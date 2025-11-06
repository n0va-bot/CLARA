import os
import subprocess
from typing import Tuple, Optional

def is_wayland() -> bool:
    session_type = os.environ.get('XDG_SESSION_TYPE', '').lower()
    wayland_display = os.environ.get('WAYLAND_DISPLAY', '')
    
    return session_type == 'wayland' or bool(wayland_display)

def get_screen_info() -> Tuple[int, int]:
    if is_wayland():
        try:
            output = subprocess.check_output(['wlr-randr'], text=True, stderr=subprocess.DEVNULL)
            for line in output.splitlines():
                if 'current' in line.lower():
                    parts = line.split()
                    for part in parts:
                        if 'x' in part and part.replace('x', '').replace('px', '').isdigit():
                            dims = part.replace('px', '').split('x')
                            return int(dims[0]), int(dims[1])
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
            pass
        
        import json

        try:
            output = subprocess.check_output(['swaymsg', '-t', 'get_outputs'], text=True)
            outputs = json.loads(output)
            if outputs and outputs[0].get('current_mode'):
                mode = outputs[0]['current_mode']
                return mode['width'], mode['height']
        except (subprocess.CalledProcessError, FileNotFoundError, json.JSONDecodeError, KeyError, PermissionError):
            pass
        
        try:
            output = subprocess.check_output(['kscreen-doctor', '-o'], text=True)
            for line in output.splitlines():
                if 'Output:' in line:
                    continue
                if 'x' in line and '@' in line:
                    resolution = line.split('@')[0].strip().split()[-1]
                    if 'x' in resolution:
                        dims = resolution.split('x')
                        return int(dims[0]), int(dims[1])
        except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
            pass
    
    try:
        output = subprocess.check_output(['xrandr'], text=True, stderr=subprocess.DEVNULL)
        for line in output.splitlines():
            if ' connected' in line and 'primary' in line:
                parts = line.split()
                for part in parts:
                    if 'x' in part and '+' in part:
                        dims = part.split('+')[0].split('x')
                        return int(dims[0]), int(dims[1])
            elif ' connected' in line and '*' in line:
                parts = line.split()
                for i, part in enumerate(parts):
                    if 'x' in part and i > 0:
                        dims = part.split('x')
                        if dims[0].isdigit():
                            return int(dims[0]), int(dims[1].split('+')[0] if '+' in dims[1] else dims[1])
    except (subprocess.CalledProcessError, FileNotFoundError, PermissionError):
        pass
    
    # maybe somehow right sometimes
    return 1920, 1080

def set_window_bottom_right_wayland(window, width: int, height: int):
    screen_w, screen_h = get_screen_info()
    x = screen_w - width
    y = screen_h - height
    
    try:
        window.move(x, y)
    except:
        pass

def get_wayland_compositor() -> Optional[str]:
    desktop = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()
    
    if 'sway' in desktop:
        return 'sway'
    elif 'kde' in desktop or 'plasma' in desktop:
        return 'kwin'
    elif 'gnome' in desktop:
        return 'mutter'
    elif 'hypr' in desktop:
        return 'hyprland'
    
    # detect from process list
    try:
        output = subprocess.check_output(['ps', 'aux'], text=True)
        if 'sway' in output:
            return 'sway'
        elif 'kwin_wayland' in output:
            return 'kwin'
        elif 'gnome-shell' in output:
            return 'mutter'
        elif 'Hyprland' in output:
            return 'hyprland'
    except:
        pass
    
    return None