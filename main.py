"""
Main entry point for running the VM Resource Utilization Widget.
Supports display flags for X11, Wayland, and XWayland environments.
"""

import os
import sys
import argparse
import glob

def setup_display_environment(args):
    """
    Configures environment variables based on user CLI flags for Wayland, XWayland, or standard X11 display servers.
    """
    if args.wayland:
        # Check for active Wayland display session
        wayland_disp = os.environ.get("WAYLAND_DISPLAY")
        if not wayland_disp:
            # Check standard runtime dir for wayland sockets
            user_runtime_dir = os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")
            wayland_sockets = glob.glob(os.path.join(user_runtime_dir, "wayland-*"))
            if wayland_sockets:
                wayland_disp = os.path.basename(wayland_sockets[0])
                os.environ["WAYLAND_DISPLAY"] = wayland_disp

        print(f"[Wayland Mode] WAYLAND_DISPLAY: {os.environ.get('WAYLAND_DISPLAY', 'not found (using default environment)')}")

        # Set GDK / Qt / Tk backend flags where applicable
        os.environ["GDK_BACKEND"] = "wayland,x11"
        os.environ["QT_QPA_PLATFORM"] = "wayland;xcb"
        os.environ["CLUTTER_BACKEND"] = "wayland"

    if args.xwayland or (args.wayland and not os.environ.get("DISPLAY")):
        # If running via XWayland, ensure DISPLAY is populated (typically :0 or :1)
        if not os.environ.get("DISPLAY"):
            # Scan /tmp/.X11-unix/ for active XWayland displays
            x_sockets = glob.glob("/tmp/.X11-unix/X*")
            if x_sockets:
                display_num = os.path.basename(x_sockets[0]).replace("X", "")
                os.environ["DISPLAY"] = f":{display_num}"
            else:
                os.environ["DISPLAY"] = ":0"
        print(f"[XWayland Mode] DISPLAY set to: {os.environ.get('DISPLAY')}")

    if args.display:
        os.environ["DISPLAY"] = args.display
        print(f"[Custom Display] DISPLAY explicitly set to: {args.display}")

    # Fallback default if DISPLAY is not set in GUI environments
    if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
        os.environ["DISPLAY"] = ":0"

def parse_args():
    parser = argparse.ArgumentParser(
        description="VM Resource Utilization Monitor Widget",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "-w", "--wayland", action="store_true",
        help="Force/Enable Wayland session environment configuration."
    )
    parser.add_argument(
        "-x", "--xwayland", action="store_true",
        help="Force/Enable XWayland compatibility layer mode for X11 applications on Wayland compositors."
    )
    parser.add_argument(
        "-d", "--display", type=str, default=None,
        help="Specify target X display string (e.g. ':0', ':1', ':99')."
    )
    parser.add_argument(
        "-i", "--interval", type=int, default=300,
        help="Auto-refresh interval in milliseconds (default: 300ms)."
    )
    return parser.parse_args()

def main():
    args = parse_args()
    setup_display_environment(args)

    print(f"Starting VM Resource Utilization Widget (Refresh: {args.interval}ms)...")
    from resource_widget import ResourceWidgetApp

    app = ResourceWidgetApp(update_interval_ms=args.interval)
    app.mainloop()

if __name__ == "__main__":
    main()
