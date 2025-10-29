from pathlib import Path
import os
import configparser
from typing import Optional, List
import platform
import subprocess
import shlex

if platform.system() == "Windows":
    try:
        from win32com.client import Dispatch
        import win32api
        import win32con
    except ImportError:
        print("Windows specific functionality requires 'pywin32'. Please run 'pip install pywin32'.")
        Dispatch = None
        win32api = None
        win32con = None

_app_cache: Optional[list['App']] = None

class App:
    def __init__(self, name: str, exec: str, icon: str = "", hidden: bool = False, generic_name: str = "", comment: str = "", command: str = ""):
        self.name = name
        self.exec = exec
        self.icon = icon
        self.hidden = hidden
        self.generic_name = generic_name
        self.comment = comment
        self.command = command if command else os.path.basename(exec.split(' ')[0])
    
    def __str__(self):
        return f"App(name={self.name}, exec={self.exec}, command={self.command}, icon={self.icon}, hidden={self.hidden}, generic_name={self.generic_name}, comment={self.comment})"

def get_desktop_dirs_linux():
    dirs = [
        Path.home() / ".local/share/applications",
        Path.home() / ".var/lib/app/flatpak/exports/share/applications",
        Path("/usr/share/applications"),
        Path("/usr/local/share/applications"),
        Path("/var/lib/flatpak/exports/share/applications")
    ]
    
    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "").split(":")
    for xdg_dir in xdg_data_dirs:
        if xdg_dir:
            dirs.append(Path(xdg_dir) / "applications")
    
    return [d for d in dirs if d.exists()]

def get_start_menu_dirs_windows():
    appdata = os.getenv('APPDATA')
    programdata = os.getenv('PROGRAMDATA')
    dirs = []
    if appdata:
        dirs.append(Path(appdata) / "Microsoft/Windows/Start Menu/Programs")
    if programdata:
        dirs.append(Path(programdata) / "Microsoft/Windows/Start Menu/Programs")
    return [d for d in dirs if d.exists()]

def parse_desktop_file(file_path: Path) -> list[App]:
    apps = []
    config = configparser.ConfigParser(interpolation=None)
    
    try:
        config.read(file_path, encoding='utf-8')
    except Exception:
        return []

    if 'Desktop Entry' not in config:
        return []

    main_entry = config['Desktop Entry']
    main_name = main_entry.get('Name')
    
    is_hidden = main_entry.get('Hidden', 'false').lower() == 'true' or \
                main_entry.get('NoDisplay', 'false').lower() == 'true'

    if main_name and not is_hidden:
        main_exec = main_entry.get('Exec')
        if main_exec:
            apps.append(App(
                name=main_name,
                exec=main_exec,
                icon=main_entry.get('Icon', ''),
                hidden=False,
                generic_name=main_entry.get('GenericName', ''),
                comment=main_entry.get('Comment', '')
            ))

        if 'Actions' in main_entry:
            action_ids = [action for action in main_entry['Actions'].split(';') if action]
            for action_id in action_ids:
                action_section_name = f'Desktop Action {action_id}'
                if action_section_name in config:
                    action_section = config[action_section_name]
                    action_name = action_section.get('Name')
                    action_exec = action_section.get('Exec')

                    if action_name and action_exec:
                        combined_name = f"{main_name} - {action_name}"
                        apps.append(App(
                            name=combined_name,
                            exec=action_exec,
                            icon=main_entry.get('Icon', '')
                        ))
    return apps

def parse_lnk_file(file_path: Path) -> Optional[App]:
    if not Dispatch:
        return None
    try:
        shell = Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(str(file_path))
        
        target = shortcut.TargetPath
        arguments = shortcut.Arguments

        if not target or not os.path.exists(target):
            return None

        full_exec = f'"{target}"'
        if arguments:
            full_exec += f' {arguments}'

        return App(
            name=file_path.stem,
            exec=full_exec,
            comment=shortcut.Description,
            icon=shortcut.IconLocation.split(',')[0] if shortcut.IconLocation else ""
        )
    except Exception:
        return None

def is_user_dir(path: Path) -> bool:
    path_str = str(path)
    user_home = str(Path.home())
    return path_str.startswith(user_home)

def list_apps_linux() -> List[App]:
    apps_dict = {}
    for desktop_dir in get_desktop_dirs_linux():
        is_user = is_user_dir(desktop_dir)
        for file_path in desktop_dir.glob("*.desktop"):
            for app in parse_desktop_file(file_path):
                if app.hidden or not app.name or not app.exec:
                    continue
                
                if app.name in apps_dict:
                    existing_is_user = apps_dict[app.name][1]
                    if is_user and not existing_is_user:
                        apps_dict[app.name] = (app, is_user)
                else:
                    apps_dict[app.name] = (app, is_user)
    return [app for app, _ in apps_dict.values()]

def list_apps_windows() -> List[App]:
    apps_dict = {}
    for start_menu_dir in get_start_menu_dirs_windows():
        for file_path in start_menu_dir.rglob("*.lnk"):
            app = parse_lnk_file(file_path)
            if app and app.exec and app.name:
                if app.exec not in apps_dict or len(app.name) > len(apps_dict[app.exec].name):
                    apps_dict[app.exec] = app
    return list(apps_dict.values())

def list_apps(force_reload: bool = False) -> list[App]:
    global _app_cache
    
    if _app_cache is not None and not force_reload:
        return _app_cache
    
    if platform.system() == "Windows":
        _app_cache = list_apps_windows()
    else:
        _app_cache = list_apps_linux()
        
    return _app_cache

def reload_app_cache() -> list[App]:
    return list_apps(force_reload=True)

def launch(app: App):
    if platform.system() == "Windows":
        if not win32api or not win32con:
            print(f"Failed to launch '{app.name}': pywin32 components are missing.")
            return
        
        try:
            # Using ShellExecute is more robust for launching various application types on Windows,
            # as it leverages the Windows shell's own mechanisms. This is particularly helpful for
            # non-standard executables like PWAs or Microsoft Store apps.
            command_parts = shlex.split(app.exec, posix=False)
            target = command_parts[0]
            
            # Use subprocess.list2cmdline to correctly re-assemble the arguments string,
            # preserving quotes around arguments with spaces.
            arguments = subprocess.list2cmdline(command_parts[1:])

            win32api.ShellExecute(
                0,                          # Parent window handle (0 for desktop)
                "open",                     # Operation
                target,                     # File to execute or open
                arguments,                  # Parameters
                "",                       # Working directory (None for default)
                win32con.SW_SHOWNORMAL      # How to show the window
            )
        except Exception as e:
            print(f"Failed to launch '{app.name}': {e}")
    else:
        cleaned_exec = app.exec.split(' %')[0]
        try:
            subprocess.Popen(shlex.split(cleaned_exec))
        except Exception as e:
            print(f"Failed to launch '{app.name}': {e}")


if __name__ == "__main__":
    apps = list_apps()
    for app in sorted(apps, key=lambda a: a.name):
        print(app)