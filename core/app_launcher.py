from pathlib import Path
import os

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

def parse_desktop_file(file_path: Path) -> App:
    app_data = {}
    with file_path.open() as f:
        for line in f:
            if line.startswith("["):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                app_data[key] = value.strip().strip('"')
    
    if "Name" in app_data:
        app_data["Name"] = app_data["Name"].strip().strip('"')
    if "Icon" in app_data:
        app_data["Icon"] = app_data["Icon"].strip().strip('"')
    if "Hidden" in app_data:
        app_data["Hidden"] = app_data["Hidden"].strip().strip('"')
    if "NoDisplay" in app_data:
        app_data["Hidden"] = app_data["NoDisplay"].strip().strip('"')

    app = App(
        name=app_data.get("Name", ""),
        exec=app_data.get("Exec", ""),
        icon=app_data.get("Icon", ""),
        hidden=app_data.get("Hidden", "").lower() == "true"
    )

    return app

def list_apps() -> list[App]:
    all_apps = []
    for desktop_dir in get_desktop_dirs():
        for file_path in desktop_dir.glob("*.desktop"):
            app = parse_desktop_file(file_path)
            if not app.hidden:
                all_apps.append(app)
    
    return all_apps

def launch(app: App):
    os.system(f"{app.exec}")

if __name__ == "__main__":
    apps = list_apps()
    for app in apps:
        print(app)