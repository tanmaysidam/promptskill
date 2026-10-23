"""
VanaSetu Git Push Launcher
==========================
Ensures C:\\Users\\tanma\\.mingit\\cmd is in PATH and launches native git push.
"""

import os
import sys
import subprocess

def main():
    git_dir = r"C:\Users\tanma\.mingit\cmd"
    if git_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = git_dir + os.pathsep + os.environ.get("PATH", "")

    git_exe = os.path.join(git_dir, "git.exe")
    print(f"Launching Git push to origin main...")
    cmd = [git_exe, "push", "-u", "origin", "main"]
    res = subprocess.run(cmd)
    sys.exit(res.returncode)

if __name__ == "__main__":
    main()
