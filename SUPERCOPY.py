import fnmatch
import os
import sys


def get_language(file_path):
    extension_map = {
        ".html": "html",
        ".htm": "html",
        ".css": "css",
        ".js": "javascript",
        ".mjs": "javascript",
        ".cjs": "javascript",
        ".py": "python",
        ".pyc": "python",
        ".pyo": "python",
        ".md": "markdown",
        ".markdown": "markdown",
        ".txt": "text",
        ".json": "json",
        ".geojson": "json",
        ".xml": "xml",
        ".php": "php",
        ".phtml": "php",
        ".sql": "sql",
        ".sh": "bash",
        ".bash": "bash",
        ".zsh": "bash",
        ".fish": "fish",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".toml": "toml",
        ".ini": "ini",
        ".cfg": "ini",
        ".conf": "ini",
        ".config": "ini",
        ".log": "text",
        ".bat": "batch",
        ".cmd": "batch",
        ".ps1": "powershell",
        ".psm1": "powershell",
        ".psd1": "powershell",
        ".rb": "ruby",
        ".gemspec": "ruby",
        ".go": "go",
        ".java": "java",
        ".class": "java",
        ".c": "c",
        ".h": "cpp",
        ".cpp": "cpp",
        ".cc": "cpp",
        ".cxx": "cpp",
        ".c++": "cpp",
        ".hpp": "cpp",
        ".hh": "cpp",
        ".hxx": "cpp",
        ".cs": "csharp",
        ".csx": "csharp",
        ".swift": "swift",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".rs": "rust",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".mts": "typescript",
        ".cts": "typescript",
        ".jsx": "javascript",
        ".vue": "vue",
        ".scss": "scss",
        ".sass": "sass",
        ".less": "less",
        ".styl": "stylus",
        ".stylus": "stylus",
        ".graphql": "graphql",
        ".gql": "graphql",
        ".dockerfile": "dockerfile",
        ".dockerignore": "dockerignore",
        ".editorconfig": "ini",
        ".gitignore": "gitignore",
        ".gitattributes": "gitattributes",
        ".gitmodules": "gitmodules",
        ".prettierrc": "json",
        ".eslintrc": "json",
        ".babelrc": "json",
        ".npmignore": "gitignore",
        ".lock": "text",
        ".env": "env",
        ".env.local": "env",
        ".env.development": "env",
        ".env.production": "env",
        ".env.test": "env",
    }

    ext = os.path.splitext(file_path)[1].lower()
    return extension_map.get(ext, "")


def should_exclude(file_path, root_dir):
    """Determine if a file should be excluded from copying."""
    abs_path = os.path.abspath(file_path)
    rel_path = os.path.relpath(abs_path, root_dir)
    rel_path_forward = rel_path.replace(os.sep, "/")
    basename = os.path.basename(file_path)

    # Exclude specific files
    exclude_files = {".pyc"}
    if rel_path_forward in exclude_files or basename in exclude_files:
        return True

    # Exclude image files
    image_extensions = {
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".bmp",
        ".ico",
        ".tiff",
        ".tif",
        ".webp",
        ".heic",
        ".heif",
        ".avif",
        ".jfif",
        ".pjpeg",
        ".pjp",
        ".tga",
        ".psd",
        ".raw",
        ".cr2",
        ".nef",
        ".orf",
        ".sr2",
        ".arw",
        ".dng",
        ".rw2",
        ".raf",
        ".3fr",
        ".kdc",
        ".mef",
        ".mrw",
        ".pef",
        ".srw",
        ".x3f",
        ".r3d",
        ".fff",
        ".iiq",
        ".erf",
        ".nrw",
    }

    ext = os.path.splitext(file_path)[1].lower()
    if ext in image_extensions:
        return True

    return False


def load_gitignore_patterns(root_dir):
    patterns = []
    gitignore_path = os.path.join(root_dir, ".gitignore")

    if os.path.isfile(gitignore_path):
        try:
            with open(gitignore_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    # Skip empty lines and comments
                    if line and not line.startswith("#"):
                        # Remove trailing backslash for escaped #
                        if line.startswith(r"\#"):
                            line = line[1:]
                        patterns.append(line)
        except Exception as e:
            print(f"Warning: Could not read .gitignore: {e}")

    return patterns


def is_ignored(path, patterns, root_dir):
    if not patterns:
        return False

    # Get relative path with forward slashes
    rel_path = os.path.relpath(path, root_dir).replace(os.sep, "/")

    # For directories, also check with trailing slash
    if os.path.isdir(path):
        rel_path_with_slash = rel_path + "/"
    else:
        rel_path_with_slash = rel_path

    for pattern in patterns:
        # Skip negation patterns (too complex for this script)
        if pattern.startswith("!"):
            continue

        # Directory pattern (ending with /)
        if pattern.endswith("/"):
            if not os.path.isdir(path):
                continue
            pattern = pattern.rstrip("/")
            # Match directory name or anything inside it
            if fnmatch.fnmatch(rel_path, pattern) or fnmatch.fnmatch(
                rel_path_with_slash, pattern + "/*"
            ):
                return True
            continue

        # Absolute pattern (starting with /) - match from root only
        if pattern.startswith("/"):
            pattern = pattern.lstrip("/")
            if fnmatch.fnmatch(rel_path, pattern):
                return True
            continue

        # Pattern without slash - matches at any level
        if "/" not in pattern:
            # Check basename
            basename = os.path.basename(rel_path)
            if fnmatch.fnmatch(basename, pattern):
                return True
        else:
            # Pattern with slash - relative path match
            if fnmatch.fnmatch(rel_path, pattern):
                return True

    return False


def get_files_from_directory(
    directory, recursive=False, root_dir=None, gitignore_patterns=None
):
    if root_dir is None:
        root_dir = os.getcwd()

    if gitignore_patterns is None:
        gitignore_patterns = []

    files_list = []
    abs_directory = os.path.abspath(directory)

    if not os.path.exists(abs_directory):
        print(f"Warning: Directory '{directory}' not found.")
        return files_list

    # Skip if directory itself is ignored
    if is_ignored(abs_directory, gitignore_patterns, root_dir):
        return files_list

    if recursive:
        for dirpath, dirnames, filenames in os.walk(abs_directory):
            # Filter directories: exclude hidden and gitignored
            dirnames[:] = [
                d
                for d in dirnames
                if not d.startswith(".")
                and not is_ignored(
                    os.path.join(dirpath, d), gitignore_patterns, root_dir
                )
            ]

            # Filter files
            for filename in filenames:
                if filename.startswith("."):
                    continue

                full_path = os.path.join(dirpath, filename)
                if (
                    os.path.isfile(full_path)
                    and not should_exclude(full_path, root_dir)
                    and not is_ignored(full_path, gitignore_patterns, root_dir)
                ):
                    files_list.append(full_path)
    else:
        for filename in os.listdir(abs_directory):
            if filename.startswith("."):
                continue

            full_path = os.path.join(abs_directory, filename)

            # Skip directories in non-recursive mode
            if os.path.isdir(full_path):
                continue

            if (
                os.path.isfile(full_path)
                and not should_exclude(full_path, root_dir)
                and not is_ignored(full_path, gitignore_patterns, root_dir)
            ):
                files_list.append(full_path)

    return files_list


def main():
    root_dir = os.getcwd()
    script_path = os.path.abspath(__file__)
    output_file = "copy.md"
    codeblock = "```"

    # Load .gitignore patterns
    gitignore_patterns = load_gitignore_patterns(root_dir)
    if gitignore_patterns:
        print(f"Loaded {len(gitignore_patterns)} patterns from .gitignore")

    def is_output_file(path):
        return os.path.abspath(path) == os.path.abspath(output_file)

    # Directories to process: (path, recursive)
    directories = [
        ("./", False),  # Root directory
        ("assets/", True),  # Archive directory (with subdirectories)
        ("core/", True),  # Legacy directory
        ("strings/", True),  # Maybe directory
        ("windows/", True),
    ]

    all_files = []
    for directory, recursive in directories:
        files = get_files_from_directory(
            directory, recursive, root_dir, gitignore_patterns
        )
        files = [
            f
            for f in files
            if not is_output_file(f) and os.path.abspath(f) != script_path
        ]
        all_files.extend(files)

    # Remove duplicates and sort
    all_files = sorted(set(all_files))

    markdown_content = ""
    file_count = 0

    for file_path in all_files:
        try:
            rel_path = os.path.relpath(file_path, root_dir)
            language = get_language(file_path)

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            markdown_content += f"### {rel_path.replace(os.sep, '/')}\n\n"
            markdown_content += (
                f"{codeblock}{language}\n" if language else f"{codeblock}\n"
            )
            markdown_content += content
            markdown_content += f"\n{codeblock}\n\n"

            file_count += 1

        except UnicodeDecodeError:
            print(f"Warning: Could not read {file_path} as text. Skipping.")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    markdown_content += f"<!-- Processed {file_count} files -->\n"

    try:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)
        print(f"Successfully created {output_file} with {file_count} files.")
    except Exception as e:
        print(f"Error writing to {output_file}: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
