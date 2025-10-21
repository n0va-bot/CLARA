import shutil, subprocess, os

def find(pattern: str, root: str='/'):
    path = os.path.expanduser(root)
    if shutil.which('fd') is None:
        raise RuntimeError("fd not installed")
    out = subprocess.check_output(['fd', pattern, path], text=True, errors='ignore')
    return out.splitlines()