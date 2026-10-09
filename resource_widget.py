"""
Resource Monitor Widget (Tkinter GUI)
A compact, highly readable widget presenting CPU, Physical Memory, Virtual Memory, and Storage metrics
with numerical values, progress visualizations, color coding, and sub-second auto-refreshes.
"""

import sys
import tkinter as tk
from tkinter import ttk
from resource_collector import ResourceCollector, bytes_to_human

class MetricBar(tk.Canvas):
    """Custom progress bar canvas that supports custom colors, rounded aesthetics, and smooth rendering."""
    def __init__(self, parent, height=18, bg="#2D3748", fg="#3182CE", **kwargs):
        super().__init__(parent, height=height, bg=bg, highlightthickness=0, **kwargs)
        self.height = height
        self.bg_color = bg
        self.fg_color = fg
        self.fraction = 0.0
        self.bind("<Configure>", self._on_resize)

    def _on_resize(self, event):
        self.draw()

    def set_value(self, fraction, fg_color=None):
        self.fraction = max(0.0, min(1.0, fraction))
        if fg_color:
            self.fg_color = fg_color
        self.draw()

    def draw(self):
        self.delete("all")
        w = self.winfo_width()
        h = self.winfo_height()
        if w <= 1 or h <= 1:
            return

        # Background track
        self.create_rectangle(0, 0, w, h, fill=self.bg_color, outline="")

        # Filled portion
        fill_width = int(w * self.fraction)
        if fill_width > 0:
            self.create_rectangle(0, 0, fill_width, h, fill=self.fg_color, outline="")

        # Subtle border
        self.create_rectangle(0, 0, w - 1, h - 1, outline="#4A5568", width=1)

def get_status_color(fraction):
    """Return color based on usage thresholds (Green -> Yellow/Amber -> Red)."""
    if fraction < 0.70:
        return "#38A169" # Emerald Green
    elif fraction < 0.88:
        return "#DD6B20" # Amber / Orange
    else:
        return "#E53E3E" # Crimson Red

class ResourceWidgetApp(tk.Tk):
    def __init__(self, update_interval_ms=300):
        super().__init__()
        self.update_interval_ms = update_interval_ms
        self.collector = ResourceCollector()

        self.title("VM Resource Monitor Widget")
        self.geometry("540x720")
        self.minsize(480, 580)
        self.configure(bg="#1A202C") # Dark theme slate background

        # Header
        self._build_header()

        # Container for main content
        self.main_container = tk.Frame(self, bg="#1A202C")
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=12, pady=5)

        # Build Sections
        self._build_cpu_section(self.main_container)
        self._build_memory_section(self.main_container)
        self._build_vmemory_section(self.main_container)
        self._build_storage_section(self.main_container)

        # Footer / Refresh Indicator
        self._build_footer()

        # Start auto-update timer (e.g. every 300ms = ~3.3 refreshes per second)
        self.after(50, self.refresh_metrics)

    def _build_header(self):
        header_frame = tk.Frame(self, bg="#2D3748", pady=10, padx=15)
        header_frame.pack(fill=tk.X, side=tk.TOP)

        title_lbl = tk.Label(
            header_frame, text="⚡ VM Resource Utilization",
            font=("Helvetica", 14, "bold"), fg="#EDF2F7", bg="#2D3748"
        )
        title_lbl.pack(side=tk.LEFT)

        self.refresh_lbl = tk.Label(
            header_frame, text="● Live (3.3 Hz)",
            font=("Helvetica", 9, "bold"), fg="#48BB78", bg="#2D3748"
        )
        self.refresh_lbl.pack(side=tk.RIGHT)

    def _build_card(self, parent, title):
        card = tk.LabelFrame(
            parent, text=f"  {title}  ", font=("Helvetica", 11, "bold"),
            fg="#63B3ED", bg="#2D3748", bd=1, relief=tk.SOLID, padx=12, pady=10
        )
        card.pack(fill=tk.X, expand=False, pady=6)
        return card

    def _build_cpu_section(self, parent):
        card = self._build_card(parent, "1. Processing Power (CPU)")

        # Main stats row
        top_row = tk.Frame(card, bg="#2D3748")
        top_row.pack(fill=tk.X, pady=(0, 4))

        self.cpu_pct_lbl = tk.Label(
            top_row, text="0.0%", font=("Helvetica", 16, "bold"), fg="#EDF2F7", bg="#2D3748"
        )
        self.cpu_pct_lbl.pack(side=tk.LEFT)

        self.cpu_raw_lbl = tk.Label(
            top_row, text="Cores: - | Load: -", font=("Helvetica", 9), fg="#A0AEC0", bg="#2D3748"
        )
        self.cpu_raw_lbl.pack(side=tk.RIGHT)

        # Main CPU utilization bar
        self.cpu_bar = MetricBar(card, height=16, bg="#1A202C")
        self.cpu_bar.pack(fill=tk.X, pady=(2, 6))

        # Per-core indicators container
        self.cores_frame = tk.Frame(card, bg="#2D3748")
        self.cores_frame.pack(fill=tk.X, pady=(2, 0))
        self.core_bars = []
        self.core_labels = []

    def _build_memory_section(self, parent):
        card = self._build_card(parent, "2. Physical Memory (RAM)")

        top_row = tk.Frame(card, bg="#2D3748")
        top_row.pack(fill=tk.X, pady=(0, 4))

        self.mem_pct_lbl = tk.Label(
            top_row, text="0.0%", font=("Helvetica", 16, "bold"), fg="#EDF2F7", bg="#2D3748"
        )
        self.mem_pct_lbl.pack(side=tk.LEFT)

        self.mem_raw_lbl = tk.Label(
            top_row, text="Used: - / Total: -", font=("Helvetica", 10, "bold"), fg="#A0AEC0", bg="#2D3748"
        )
        self.mem_raw_lbl.pack(side=tk.RIGHT)

        self.mem_bar = MetricBar(card, height=16, bg="#1A202C")
        self.mem_bar.pack(fill=tk.X, pady=(2, 4))

        self.mem_sub_lbl = tk.Label(
            card, text="Available: - | Cached/Buffers: -", font=("Helvetica", 8), fg="#CBD5E0", bg="#2D3748", anchor="w"
        )
        self.mem_sub_lbl.pack(fill=tk.X)

    def _build_vmemory_section(self, parent):
        card = self._build_card(parent, "2a. Virtual Memory & Swap")

        top_row = tk.Frame(card, bg="#2D3748")
        top_row.pack(fill=tk.X, pady=(0, 4))

        self.vmem_pct_lbl = tk.Label(
            top_row, text="Swap: 0.0%", font=("Helvetica", 12, "bold"), fg="#EDF2F7", bg="#2D3748"
        )
        self.vmem_pct_lbl.pack(side=tk.LEFT)

        self.vmem_raw_lbl = tk.Label(
            top_row, text="Swap Used: - / -", font=("Helvetica", 9), fg="#A0AEC0", bg="#2D3748"
        )
        self.vmem_raw_lbl.pack(side=tk.RIGHT)

        self.vmem_bar = MetricBar(card, height=14, bg="#1A202C")
        self.vmem_bar.pack(fill=tk.X, pady=(2, 4))

        self.vmem_diff_lbl = tk.Label(
            card, text="Total Pool (RAM + Swap): -", font=("Helvetica", 8), fg="#CBD5E0", bg="#2D3748", anchor="w"
        )
        self.vmem_diff_lbl.pack(fill=tk.X)

    def _build_storage_section(self, parent):
        self.storage_card = self._build_card(parent, "3. Mounted Storage Devices")
        self.storage_devices_frame = tk.Frame(self.storage_card, bg="#2D3748")
        self.storage_devices_frame.pack(fill=tk.X, expand=True)
        self.storage_widgets = {}

    def _build_footer(self):
        footer = tk.Frame(self, bg="#1A202C", pady=8, padx=12)
        footer.pack(fill=tk.X, side=tk.BOTTOM)

        lbl = tk.Label(
            footer, text="Auto-refresh: 3.3 Hz (Every 300ms) | Status: Running",
            font=("Helvetica", 8), fg="#718096", bg="#1A202C"
        )
        lbl.pack(side=tk.LEFT)

    def refresh_metrics(self):
        try:
            metrics = self.collector.get_all_metrics()
            self._update_cpu(metrics["cpu"])
            self._update_memory(metrics["memory"])
            self._update_vmemory(metrics["virtual_memory"])
            self._update_storage(metrics["storage"])
        except Exception as e:
            print("Error refreshing metrics:", e)
        finally:
            self.after(self.update_interval_ms, self.refresh_metrics)

    def _update_cpu(self, cpu_data):
        pct = cpu_data["overall_percent"]
        frac = cpu_data["overall_fraction"]
        color = get_status_color(frac)

        self.cpu_pct_lbl.config(text=f"{pct:.1f}%", fg=color)
        self.cpu_bar.set_value(frac, fg_color=color)

        summary = f"{cpu_data['raw_summary']} | Load: {cpu_data['load_1m']:.2f}"
        self.cpu_raw_lbl.config(text=summary)

        # Update per-core bars
        per_core = cpu_data["per_core_percent"]
        num_cores = len(per_core)

        # Re-create per-core widgets if count changed
        if len(self.core_bars) != num_cores:
            for w in self.cores_frame.winfo_children():
                w.destroy()
            self.core_bars = []
            self.core_labels = []

            for i in range(num_cores):
                sub_f = tk.Frame(self.cores_frame, bg="#2D3748")
                sub_f.pack(fill=tk.X, pady=1)

                lbl = tk.Label(sub_f, text=f"Core {i}: 0.0%", font=("Helvetica", 8), fg="#A0AEC0", bg="#2D3748", width=12, anchor="w")
                lbl.pack(side=tk.LEFT)

                bar = MetricBar(sub_f, height=10, bg="#1A202C")
                bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=4)

                self.core_labels.append(lbl)
                self.core_bars.append(bar)

        for i, val in enumerate(per_core):
            c_frac = val / 100.0
            c_color = get_status_color(c_frac)
            self.core_labels[i].config(text=f"Core {i}: {val:.1f}%")
            self.core_bars[i].set_value(c_frac, fg_color=c_color)

    def _update_memory(self, mem_data):
        frac = mem_data["fraction"]
        color = get_status_color(frac)

        self.mem_pct_lbl.config(text=f"{mem_data['percent']:.1f}%", fg=color)
        self.mem_raw_lbl.config(text=f"{mem_data['used_human']} / {mem_data['total_human']}")
        self.mem_bar.set_value(frac, fg_color=color)

        cached_str = bytes_to_human(mem_data['cached_bytes'] + mem_data['buffers_bytes'])
        self.mem_sub_lbl.config(text=f"Available: {mem_data['available_human']}  |  Cached/Buffers: {cached_str}")

    def _update_vmemory(self, vmem_data):
        frac = vmem_data["swap_fraction"]
        color = get_status_color(frac)

        if not vmem_data["has_swap"]:
            self.vmem_pct_lbl.config(text="Swap: 0.0% (Disabled/None)", fg="#A0AEC0")
            self.vmem_raw_lbl.config(text="0 B / 0 B")
            self.vmem_bar.set_value(0.0, fg_color="#4A5568")
        else:
            self.vmem_pct_lbl.config(text=f"Swap: {vmem_data['swap_percent']:.1f}%", fg=color)
            self.vmem_raw_lbl.config(text=f"{vmem_data['used_swap_human']} / {vmem_data['total_swap_human']}")
            self.vmem_bar.set_value(frac, fg_color=color)

        pool_txt = (f"Combined Pool (RAM + Swap): {vmem_data['used_vm_pool_human']} used of "
                    f"{vmem_data['total_vm_pool_human']} ({vmem_data['vm_pool_percent']:.1f}%)")
        self.vmem_diff_lbl.config(text=pool_txt)

    def _update_storage(self, storage_data):
        current_dev_paths = {d["device_path"] for d in storage_data}

        # Remove devices that are no longer mounted
        for dev_path in list(self.storage_widgets.keys()):
            if dev_path not in current_dev_paths:
                self.storage_widgets[dev_path]["frame"].destroy()
                del self.storage_widgets[dev_path]

        # Add or update devices
        for dev in storage_data:
            dev_path = dev["device_path"]
            frac = dev["fraction_used"]
            color = get_status_color(frac)

            if dev_path not in self.storage_widgets:
                dev_f = tk.Frame(self.storage_devices_frame, bg="#2D3748", pady=4)
                dev_f.pack(fill=tk.X, expand=True, pady=2)

                # Row 1: Device Name, Mountpoint, & Utilization %
                r1 = tk.Frame(dev_f, bg="#2D3748")
                r1.pack(fill=tk.X)

                title_txt = f"💾 {dev['name']} [{dev['mountpoints_str']}]"
                name_lbl = tk.Label(r1, text=title_txt, font=("Helvetica", 9, "bold"), fg="#E2E8F0", bg="#2D3748", anchor="w")
                name_lbl.pack(side=tk.LEFT)

                pct_lbl = tk.Label(r1, text=f"{dev['percent_used']:.1f}%", font=("Helvetica", 9, "bold"), fg=color, bg="#2D3748")
                pct_lbl.pack(side=tk.RIGHT)

                # Row 2: Visual Progress Bar
                bar = MetricBar(dev_f, height=12, bg="#1A202C")
                bar.pack(fill=tk.X, pady=(2, 2))

                # Row 3: Raw Usage & Partition Info (UUID, fstype)
                r3 = tk.Frame(dev_f, bg="#2D3748")
                r3.pack(fill=tk.X)

                raw_txt = f"Used: {dev['used_human']} of {dev['total_human']} (Free: {dev['free_human']})"
                raw_lbl = tk.Label(r3, text=raw_txt, font=("Helvetica", 8), fg="#A0AEC0", bg="#2D3748", anchor="w")
                raw_lbl.pack(side=tk.LEFT)

                info_txt = f"UUID: {dev['uuid'][:13]}..." if len(dev['uuid']) > 13 else f"UUID: {dev['uuid']}"
                info_lbl = tk.Label(r3, text=info_txt, font=("Helvetica", 8), fg="#718096", bg="#2D3748", anchor="e")
                info_lbl.pack(side=tk.RIGHT)

                self.storage_widgets[dev_path] = {
                    "frame": dev_f,
                    "name_lbl": name_lbl,
                    "pct_lbl": pct_lbl,
                    "bar": bar,
                    "raw_lbl": raw_lbl,
                    "info_lbl": info_lbl
                }

            # Update existing
            w = self.storage_widgets[dev_path]
            w["pct_lbl"].config(text=f"{dev['percent_used']:.1f}%", fg=color)
            w["bar"].set_value(frac, fg_color=color)
            w["raw_lbl"].config(text=f"Used: {dev['used_human']} of {dev['total_human']} (Free: {dev['free_human']})")

def main():
    app = ResourceWidgetApp(update_interval_ms=300)
    app.mainloop()

if __name__ == "__main__":
    main()
