from pathlib import Path
import os
import configparser

class App:
    def __init__(self, name: str, exec: str, icon: str = "", hidden: bool = False):
        self.name = name
        self.exec = exec
        self.icon = icon
        self.hidden = hidden
    
    def __str__(self):
        return f"App(name={self.name}, exec={self.exec}, icon={self.icon}, hidden={self.hidden})"

def get_desktop_dirs():
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
                hidden=False
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
                            icon=main_entry.get('Icon', ''),
                            hidden=False
                        ))
    return apps


def is_user_dir(path: Path) -> bool:
    path_str = str(path)
    user_home = str(Path.home())
    return path_str.startswith(user_home)

def list_apps() -> list[App]:
    apps_dict = {}
    
    for desktop_dir in get_desktop_dirs():
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

def launch(app: App):
    import subprocess
    import shlex
    
    cleaned_exec = app.exec.split(' %')[0]
    
    try:
        subprocess.Popen(shlex.split(cleaned_exec))
    except Exception as e:
        print(f"Failed to launch '{app.name}': {e}")


if __name__ == "__main__":
    apps = list_apps()
    for app in sorted(apps, key=lambda a: a.name):
        print(app)