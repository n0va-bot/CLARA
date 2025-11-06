files = [
    "core/app_launcher.py",
    "core/config.py",
    "core/discord_presence.py",
    "core/dukto.py",
    "core/file_search.py",
    "core/headers.py",
    "core/http_share.py",
    "core/updater.py",
    "core/wayland_utils.py",
    "core/web_search.py",
    "strings/en.json",
    "strings/personality_en.json",
    "windows/app_launcher.py",
    "windows/calculator.py",
    "windows/file_search.py",
    "windows/main_window.py",
    "windows/text_viewer.py",
    "windows/web_results.py",
    "main.py",
    "README.md",
    "requirements.txt"
]

codeblock = "```"

copy = ""

for file in files:
    with open(file, "r", encoding="utf-8") as f:
        lines = f.readlines()
        copy += f"### {file}\n\n"
        copy += f"{codeblock}python\n"
        copy += "".join(lines)
        copy += f"\n{codeblock}\n\n"

with open("copy.md", "w", encoding="utf-8") as f:
    f.write(copy)