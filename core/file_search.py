import shutil
import subprocess
import os
import platform
import fnmatch

def _find_native(pattern: str, root: str):
    """Native Python implementation of file search using os.walk."""
    results = []
    for dirpath, _, filenames in os.walk(root):
        for filename in fnmatch.filter(filenames, pattern):
            results.append(os.path.join(dirpath, filename))
    return results

def find(pattern: str, root: str='/'):
    path = os.path.expanduser(root)
    
    if shutil.which('fd') is None:
        return _find_native(f"*{pattern}*", path)
    else:
        try:
            out = subprocess.check_output(['fd', pattern, path], text=True, errors='ignore')
            return out.splitlines()
        except subprocess.CalledProcessError:
            return []