# TASK: reboot
# SCHEDULE: on demand
# ENABLED: true
# DESCRIPTION: Reboot the device

import subprocess
from notify import send


def run():
    send("Rebooting...")
    subprocess.run(["sudo", "reboot"], timeout=15)
