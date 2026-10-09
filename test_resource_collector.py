"""
Unit and Integration Tests for VM Resource Monitor Widget
"""

import os
import unittest
import argparse
from resource_collector import ResourceCollector, bytes_to_human
from main import setup_display_environment, parse_args

class TestResourceCollector(unittest.TestCase):
    def setUp(self):
        self.collector = ResourceCollector()

    def test_bytes_to_human(self):
        self.assertEqual(bytes_to_human(0), "0.00 B")
        self.assertEqual(bytes_to_human(1024), "1.00 KB")
        self.assertEqual(bytes_to_human(1048576), "1.00 MB")
        self.assertEqual(bytes_to_human(1073741824), "1.00 GB")
        self.assertEqual(bytes_to_human(None), "N/A")

    def test_cpu_metrics(self):
        cpu = self.collector.get_cpu_metrics()
        self.assertIn("overall_percent", cpu)
        self.assertIn("overall_fraction", cpu)
        self.assertIn("per_core_percent", cpu)
        self.assertIn("logical_cores", cpu)
        self.assertIn("physical_cores", cpu)
        self.assertGreaterEqual(cpu["overall_percent"], 0.0)
        self.assertLessEqual(cpu["overall_percent"], 100.0)
        self.assertGreaterEqual(cpu["overall_fraction"], 0.0)
        self.assertLessEqual(cpu["overall_fraction"], 1.0)
        self.assertGreater(cpu["logical_cores"], 0)

    def test_memory_metrics(self):
        mem = self.collector.get_memory_metrics()
        self.assertIn("total_bytes", mem)
        self.assertIn("used_bytes", mem)
        self.assertIn("available_bytes", mem)
        self.assertIn("fraction", mem)
        self.assertGreater(mem["total_bytes"], 0)
        self.assertGreaterEqual(mem["fraction"], 0.0)
        self.assertLessEqual(mem["fraction"], 1.0)

    def test_virtual_memory_metrics(self):
        vmem = self.collector.get_virtual_memory_metrics()
        self.assertIn("total_swap_bytes", vmem)
        self.assertIn("used_swap_bytes", vmem)
        self.assertIn("swap_fraction", vmem)
        self.assertIn("vm_pool_fraction", vmem)
        self.assertGreaterEqual(vmem["swap_fraction"], 0.0)
        self.assertLessEqual(vmem["swap_fraction"], 1.0)

    def test_storage_metrics(self):
        storage = self.collector.get_storage_metrics()
        self.assertIsInstance(storage, list)
        self.assertGreater(len(storage), 0)
        for dev in storage:
            self.assertIn("device_path", dev)
            self.assertIn("uuid", dev)
            self.assertIn("name", dev)
            self.assertIn("mountpoints", dev)
            self.assertIn("partition_info", dev)
            self.assertIn("used_bytes", dev)
            self.assertIn("total_bytes", dev)
            self.assertIn("fraction_used", dev)
            self.assertGreaterEqual(dev["fraction_used"], 0.0)
            self.assertLessEqual(dev["fraction_used"], 1.0)

class TestCLIAndEnvironment(unittest.TestCase):
    def test_wayland_flag_configuration(self):
        args = argparse.Namespace(wayland=True, xwayland=False, display=None, interval=300)
        setup_display_environment(args)
        self.assertEqual(os.environ.get("GDK_BACKEND"), "wayland,x11")
        self.assertEqual(os.environ.get("QT_QPA_PLATFORM"), "wayland;xcb")

    def test_custom_display_flag(self):
        args = argparse.Namespace(wayland=False, xwayland=False, display=":42", interval=250)
        setup_display_environment(args)
        self.assertEqual(os.environ.get("DISPLAY"), ":42")

    def test_xwayland_flag_configuration(self):
        args = argparse.Namespace(wayland=False, xwayland=True, display=None, interval=300)
        setup_display_environment(args)
        self.assertIsNotNone(os.environ.get("DISPLAY"))

if __name__ == "__main__":
    unittest.main()
