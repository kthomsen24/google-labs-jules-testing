"""
Main entry point for running the VM Resource Utilization Widget.
"""

import os
import sys
from resource_widget import ResourceWidgetApp

def main():
    print("Starting VM Resource Utilization Widget...")
    # Check if DISPLAY is available
    if not os.environ.get("DISPLAY"):
        print("Warning: DISPLAY environment variable not set. Using default :0")
        os.environ["DISPLAY"] = ":0"

    app = ResourceWidgetApp(update_interval_ms=300)
    app.mainloop()

if __name__ == "__main__":
    main()
