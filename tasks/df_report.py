# TASK: Disk Free Report
# SCHEDULE: on demand
# ENABLED: true
# DESCRIPTION: Reports disk usage for the root filesystem

import subprocess
from notify import send


def run():
    try:
        result = subprocess.run(
            ["df", "-h", "/"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        output = result.stdout.strip()
        send(f"Disk Usage:\n{output}")
    except Exception as e:
        send(f"Disk report failed: {e}")
