# TASK: restart
# SCHEDULE: on demand
# ENABLED: true
# DESCRIPTION: Restart the pincer systemd user service

import subprocess
from notify import send


def run():
    send("Restarting pincer...")
    try:
        result = subprocess.run(
            ["systemctl", "--user", "restart", "pincer"],
            capture_output=True,
            text=True,
            timeout=15,
        )
        if result.returncode != 0:
            send(f"Restart failed:\n{result.stderr.strip()}")
    except Exception as e:
        send(f"Restart failed: {e}")
