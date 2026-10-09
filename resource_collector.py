"""
Resource Collector Module
Gathers processing, memory (RAM), virtual memory (swap/cache/buffers), and storage device metrics.
"""

import os
import shutil
import subprocess
import json
import psutil

def bytes_to_human(n_bytes):
    """Convert bytes into a human-readable string (e.g. 10.2 GB)."""
    if n_bytes is None:
        return "N/A"
    n_bytes = float(n_bytes)
    for unit in ['B', 'KB', 'MB', 'GB', 'TB', 'PB']:
        if abs(n_bytes) < 1024.0:
            return f"{n_bytes:.2f} {unit}"
        n_bytes /= 1024.0
    return f"{n_bytes:.2f} EB"

class ResourceCollector:
    def __init__(self):
        # Initialize psutil cpu tracking so initial calls are accurate
        psutil.cpu_percent(interval=None)
        psutil.cpu_percent(interval=None, percpu=True)

    def get_cpu_metrics(self):
        """
        1. Processing metrics:
           - Raw measure: Logical CPU cores count, physical cores count, current clock speed/frequency,
                          per-core CPU usage list, system load averages.
           - Fraction/Percentage: Total overall CPU utilization percentage and fraction.
        """
        overall_percent = psutil.cpu_percent(interval=None)
        per_core_percent = psutil.cpu_percent(interval=None, percpu=True)
        logical_cores = psutil.cpu_count(logical=True) or 1
        physical_cores = psutil.cpu_count(logical=False) or logical_cores

        freq = getattr(psutil, 'cpu_freq', lambda: None)()
        current_freq = getattr(freq, 'current', None) if freq else None

        # Try getting load averages if available on Unix
        load_avg = getattr(os, 'getloadavg', lambda: (0.0, 0.0, 0.0))()

        return {
            "overall_percent": overall_percent,
            "overall_fraction": overall_percent / 100.0,
            "per_core_percent": per_core_percent,
            "logical_cores": logical_cores,
            "physical_cores": physical_cores,
            "current_freq_mhz": current_freq,
            "load_1m": load_avg[0],
            "load_5m": load_avg[1],
            "load_15m": load_avg[2],
            "raw_summary": f"{logical_cores} Cores ({physical_cores} Phys)" + (f" @ {current_freq:.0f} MHz" if current_freq else "")
        }

    def get_memory_metrics(self):
        """
        2. Memory metrics:
           - Basic measure of how much memory is currently in use (used_bytes, free_bytes, total_bytes).
           - Value as a fraction / percentage of total available memory.
        """
        vmem = psutil.virtual_memory()
        total = vmem.total
        used = vmem.used
        available = vmem.available
        percent = vmem.percent
        fraction = percent / 100.0 if percent else (used / total if total > 0 else 0.0)

        return {
            "total_bytes": total,
            "used_bytes": used,
            "available_bytes": available,
            "total_human": bytes_to_human(total),
            "used_human": bytes_to_human(used),
            "available_human": bytes_to_human(available),
            "percent": percent,
            "fraction": fraction,
            "cached_bytes": getattr(vmem, 'cached', 0),
            "buffers_bytes": getattr(vmem, 'buffers', 0)
        }

    def get_virtual_memory_metrics(self):
        """
        2a. Virtual memory metrics:
           - Swap memory allocations vs physical memory.
           - Highlight swap usage, total swap, fraction, and differences (cached/buffered pool).
        """
        swap = psutil.swap_memory()
        vmem = psutil.virtual_memory()

        total_swap = swap.total
        used_swap = swap.used
        free_swap = swap.free
        swap_percent = swap.percent
        swap_fraction = swap_percent / 100.0 if swap_percent else (used_swap / total_swap if total_swap > 0 else 0.0)

        # Difference analysis between physical hardware RAM and total virtual memory pool (RAM + Swap)
        total_vm_pool = vmem.total + swap.total
        used_vm_pool = vmem.used + swap.used
        vm_pool_fraction = (used_vm_pool / total_vm_pool) if total_vm_pool > 0 else 0.0

        return {
            "total_swap_bytes": total_swap,
            "used_swap_bytes": used_swap,
            "free_swap_bytes": free_swap,
            "total_swap_human": bytes_to_human(total_swap),
            "used_swap_human": bytes_to_human(used_swap),
            "free_swap_human": bytes_to_human(free_swap),
            "swap_percent": swap_percent,
            "swap_fraction": swap_fraction,
            "swap_in_bytes": getattr(swap, 'sin', 0),
            "swap_out_bytes": getattr(swap, 'sout', 0),
            "total_vm_pool_bytes": total_vm_pool,
            "used_vm_pool_bytes": used_vm_pool,
            "total_vm_pool_human": bytes_to_human(total_vm_pool),
            "used_vm_pool_human": bytes_to_human(used_vm_pool),
            "vm_pool_fraction": vm_pool_fraction,
            "vm_pool_percent": round(vm_pool_fraction * 100, 1),
            "has_swap": total_swap > 0
        }

    def get_storage_metrics(self):
        """
        3. Storage metrics for each mounted storage device:
           - device path
           - UUID
           - human-readable name
           - mountpoint(s)
           - partition info
           - amount of storage currently in use
           - storage currently in use as a fraction of total storage available
           - total amount of storage available on the device
        """
        # Map lsblk block device details if available
        lsblk_map = {}
        try:
            res = subprocess.run(
                ['lsblk', '-b', '-J', '-o', 'NAME,PATH,UUID,LABEL,FSTYPE,SIZE,MOUNTPOINTS,MODEL,TYPE'],
                capture_output=True, text=True, timeout=2
            )
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                def parse_devs(dev_list):
                    for dev in dev_list:
                        if dev.get('path'):
                            lsblk_map[dev['path']] = dev
                        if dev.get('name'):
                            lsblk_map[f"/dev/{dev['name']}"] = dev
                        if 'children' in dev:
                            parse_devs(dev['children'])
                if 'blockdevices' in data:
                    parse_devs(data['blockdevices'])
        except Exception:
            pass

        devices = []
        partitions = psutil.disk_partitions(all=False)
        seen_mounts = set()

        for p in partitions:
            if p.mountpoint in seen_mounts:
                continue
            # Skip pseudo filesystems unless relevant
            if p.fstype in ['tmpfs', 'devtmpfs', 'overlay', 'squashfs', 'cgroup2', 'proc', 'sysfs']:
                if not (p.mountpoint in ['/', '/rom', '/rom/overlay'] or p.device.startswith('/dev/')):
                    continue

            seen_mounts.add(p.mountpoint)

            try:
                usage = shutil.disk_usage(p.mountpoint)
                total = usage.total
                used = usage.used
                free = usage.free
                fraction = (used / total) if total > 0 else 0.0
            except (PermissionError, OSError):
                continue

            ls_dev = lsblk_map.get(p.device, {})
            uuid = ls_dev.get('uuid') or 'N/A'
            label = ls_dev.get('label')
            model = ls_dev.get('model')
            dev_type = ls_dev.get('type') or 'partition'

            # Human-readable name
            if label:
                name = f"{label} ({os.path.basename(p.device)})"
            elif model:
                name = f"{model.strip()} ({os.path.basename(p.device)})"
            else:
                name = os.path.basename(p.device) if p.device.startswith('/dev/') else p.mountpoint

            partition_info = f"Type: {dev_type.upper()} | FSType: {p.fstype} | Opts: {p.opts}"

            devices.append({
                "device_path": p.device,
                "uuid": uuid,
                "name": name,
                "mountpoints": [p.mountpoint],
                "mountpoints_str": ", ".join([p.mountpoint]),
                "fstype": p.fstype,
                "partition_info": partition_info,
                "used_bytes": used,
                "free_bytes": free,
                "total_bytes": total,
                "used_human": bytes_to_human(used),
                "free_human": bytes_to_human(free),
                "total_human": bytes_to_human(total),
                "fraction_used": fraction,
                "percent_used": round(fraction * 100, 1)
            })

        return devices

    def get_all_metrics(self):
        return {
            "cpu": self.get_cpu_metrics(),
            "memory": self.get_memory_metrics(),
            "virtual_memory": self.get_virtual_memory_metrics(),
            "storage": self.get_storage_metrics()
        }

if __name__ == "__main__":
    collector = ResourceCollector()
    metrics = collector.get_all_metrics()
    print(json.dumps(metrics, indent=2))
