files = [
    "core/file_search.py",
    "ui/gui.py"
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