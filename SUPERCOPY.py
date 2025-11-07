import os
import sys

def get_language(file_path):
    """Detect programming language based on file extension."""
    extension_map = {
        '.html': 'html', '.htm': 'html', '.css': 'css', '.js': 'javascript',
        '.mjs': 'javascript', '.cjs': 'javascript', '.py': 'python',
        '.pyc': 'python', '.pyo': 'python', '.md': 'markdown',
        '.markdown': 'markdown', '.txt': 'text', '.json': 'json',
        '.geojson': 'json', '.xml': 'xml', '.php': 'php', '.phtml': 'php',
        '.sql': 'sql', '.sh': 'bash', '.bash': 'bash', '.zsh': 'bash',
        '.fish': 'fish', '.yml': 'yaml', '.yaml': 'yaml', '.toml': 'toml',
        '.ini': 'ini', '.cfg': 'ini', '.conf': 'ini', '.config': 'ini',
        '.log': 'text', '.bat': 'batch', '.cmd': 'batch', '.ps1': 'powershell',
        '.psm1': 'powershell', '.psd1': 'powershell', '.rb': 'ruby',
        '.gemspec': 'ruby', '.go': 'go', '.java': 'java', '.class': 'java',
        '.c': 'c', '.h': 'cpp', '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp',
        '.c++': 'cpp', '.hpp': 'cpp', '.hh': 'cpp', '.hxx': 'cpp',
        '.cs': 'csharp', '.csx': 'csharp', '.swift': 'swift', '.kt': 'kotlin',
        '.kts': 'kotlin', '.rs': 'rust', '.ts': 'typescript', '.tsx': 'typescript',
        '.mts': 'typescript', '.cts': 'typescript', '.jsx': 'javascript',
        '.vue': 'vue', '.scss': 'scss', '.sass': 'sass', '.less': 'less',
        '.styl': 'stylus', '.stylus': 'stylus', '.graphql': 'graphql',
        '.gql': 'graphql', '.dockerfile': 'dockerfile', '.dockerignore': 'dockerignore',
        '.editorconfig': 'ini', '.gitignore': 'gitignore', '.gitattributes': 'gitattributes',
        '.gitmodules': 'gitmodules', '.prettierrc': 'json', '.eslintrc': 'json',
        '.babelrc': 'json', '.npmignore': 'gitignore', '.lock': 'text',
        '.env': 'env', '.env.local': 'env', '.env.development': 'env',
        '.env.production': 'env', '.env.test': 'env',
    }
    
    ext = os.path.splitext(file_path)[1].lower()
    return extension_map.get(ext, '')

def should_exclude(file_path, root_dir):
    """Determine if a file should be excluded from copying."""
    abs_path = os.path.abspath(file_path)
    rel_path = os.path.relpath(abs_path, root_dir)
    rel_path_forward = rel_path.replace(os.sep, '/')
    basename = os.path.basename(file_path)
    
    # Exclude specific files
    exclude_files = {'prompt.md', 'v.html', 'v.py'}
    if rel_path_forward in exclude_files or basename in exclude_files:
        return True
    
    # Exclude image files
    image_extensions = {
        '.png', '.jpg', '.jpeg', '.gif', '.svg', '.bmp', '.ico',
        '.tiff', '.tif', '.webp', '.heic', '.heif', '.avif',
        '.jfif', '.pjpeg', '.pjp', '.tga', '.psd', '.raw',
        '.cr2', '.nef', '.orf', '.sr2', '.arw', '.dng', '.rw2',
        '.raf', '.3fr', '.kdc', '.mef', '.mrw', '.pef', '.srw',
        '.x3f', '.r3d', '.fff', '.iiq', '.erf', '.nrw'
    }
    
    ext = os.path.splitext(file_path)[1].lower()
    if ext in image_extensions:
        return True
    
    return False

def get_files_from_directory(directory, recursive=False, root_dir=None):
    """Get all files from a directory, optionally recursively."""
    if root_dir is None:
        root_dir = os.getcwd()
    
    files_list = []
    
    if not os.path.exists(directory):
        print(f"Warning: Directory '{directory}' not found.")
        return files_list
    
    if recursive:
        for dirpath, dirnames, filenames in os.walk(directory):
            dirnames[:] = [d for d in dirnames if not d.startswith('.')]
            
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                
                full_path = os.path.join(dirpath, filename)
                if os.path.isfile(full_path) and not should_exclude(full_path, root_dir):
                    files_list.append(full_path)
    else:
        for filename in os.listdir(directory):
            if filename.startswith('.'):
                continue
            
            full_path = os.path.join(directory, filename)
            if os.path.isfile(full_path) and not should_exclude(full_path, root_dir):
                files_list.append(full_path)
    
    return files_list

def main():
    """Main execution function."""
    root_dir = os.getcwd()
    script_path = os.path.abspath(__file__)
    output_file = "copy.md"
    codeblock = "```"
    
    def is_output_file(path):
        return os.path.abspath(path) == os.path.abspath(output_file)
    
    # Directories to process: (path, recursive)
    directories = [
        ("./", False),      # Root directory
        ("archive/", True), # Archive directory (with subdirectories)
        ("legacy/", False), # Legacy directory
        ("maybe/", False),  # Maybe directory
    ]
    
    all_files = []
    for directory, recursive in directories:
        files = get_files_from_directory(directory, recursive, root_dir)
        files = [f for f in files if not is_output_file(f) and os.path.abspath(f) != script_path]
        all_files.extend(files)
    
    all_files.sort()
    
    markdown_content = "# Main website\n\n"
    file_count = 0
    
    for file_path in all_files:
        try:
            rel_path = os.path.relpath(file_path, root_dir)
            language = get_language(file_path)
            
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            markdown_content += f"### {rel_path.replace(os.sep, '/')}\n\n"
            markdown_content += f"{codeblock}{language}\n" if language else f"{codeblock}\n"
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