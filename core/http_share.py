#!/usr/bin/env python3

import socket
import threading
import mimetypes
from pathlib import Path
from typing import List, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import html

def format_size(bytes_val: int) -> str:
    if bytes_val is None: return ""
    if bytes_val < 1024:
        return f"{bytes_val} Bytes"
    elif bytes_val < 1024**2:
        return f"{bytes_val/1024:.2f} KB"
    elif bytes_val < 1024**3:
        return f"{bytes_val/1024**2:.2f} MB"
    else:
        return f"{bytes_val/1024**3:.2f} GB"


class FileShareHandler(BaseHTTPRequestHandler):
    shared_files: List[str] = []
    shared_text: Optional[str] = None
    on_download: Optional[Callable[[str, str], None]] = None
    
    def log_message(self, format, *args):
        pass
    
    def _get_base_html(self, title: str, body_content: str) -> str:
        return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>{html.escape(title)}</title>
    <style type="text/css">
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            background-color: #f4f4f9;
            color: #333;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
            border: 1px solid #dcdcdc;
            border-radius: 8px;
            padding: 20px 30px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        h1, h2 {{
            color: #4a4a4a;
            border-bottom: 2px solid #eaeaea;
            padding-bottom: 10px;
        }}
        p {{
            line-height: 1.6;
            color: #555;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        th, td {{
            text-align: left;
            padding: 12px;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background-color: #f8f8f8;
        }}
        tr:hover {{
            background-color: #f1f1f1;
        }}
        a {{
            color: #007bff;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        textarea {{
            width: 98%;
            padding: 10px;
            font-family: "Courier New", Courier, monospace;
            border: 1px solid #ccc;
            border-radius: 4px;
            background-color: #fafafa;
        }}
        .section {{
            margin-bottom: 30px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {body_content}
    </div>
</body>
</html>"""

    def do_GET(self):
        if self.path == '/':
            self.send_combined_index_page()
        elif self.path.startswith('/download/'):
            self.handle_download()
        else:
            self.send_error(404, "Not Found")

    def send_combined_index_page(self):
        body_parts = ["<h1>CLARA Share</h1>"]
        has_content = False

        # Text section
        if self.shared_text:
            has_content = True
            escaped_text = html.escape(self.shared_text)
            body_parts.append(f"""<div class="section">
<h2>Shared Text</h2>
<p>Select the text below and copy it.</p>
<textarea readonly="readonly" rows="15">{escaped_text}</textarea>
</div>""")

        # Files section
        if self.shared_files:
            has_content = True
            file_rows = []
            for i, filepath in enumerate(self.shared_files):
                try:
                    path = Path(filepath)
                    if path.exists() and path.is_file():
                        file_rows.append(
                            f'<tr>'
                            f'<td>{html.escape(path.name)}</td>'
                            f'<td>{format_size(path.stat().st_size)}</td>'
                            f'<td><a href="/download/{i}">Download</a></td>'
                            f'</tr>'
                        )
                except Exception:
                    continue
            
            if not file_rows:
                file_table = '<p>No valid files are currently being shared.</p>'
            else:
                file_table = f"""<table>
    <tr><th>Filename</th><th>Size</th><th>Link</th></tr>
    {''.join(file_rows)}
</table>"""

            body_parts.append(f"""<div class="section">
<h2>Shared Files</h2>
{file_table}
</div>""")

        if not has_content:
            body_parts.append("<p>No content is currently being shared.</p>")

        html_content = self._get_base_html("CLARA Share", "".join(body_parts)).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content)
    
    def handle_download(self):
        try:
            index = int(self.path.split('/')[-1])
            
            if 0 <= index < len(self.shared_files):
                filepath = self.shared_files[index]
                path = Path(filepath)
                
                if not path.exists() or not path.is_file():
                    self.send_error(404, "File not found")
                    return
                
                client_ip = self.client_address[0]
                
                if FileShareHandler.on_download:
                    FileShareHandler.on_download(path.name, client_ip)
                
                mime_type, _ = mimetypes.guess_type(str(path))
                if mime_type is None:
                    mime_type = 'application/octet-stream'
                
                file_size = path.stat().st_size
                
                self.send_response(200)
                self.send_header('Content-Type', mime_type)
                self.send_header('Content-Length', str(file_size))
                self.send_header('Content-Disposition', f'attachment; filename="{path.name}"')
                self.end_headers()
                
                with open(path, 'rb') as f:
                    self.wfile.write(f.read())

            else:
                self.send_error(404, "File not found")
                
        except Exception as e:
            print(f"Error handling download: {e}")
            if not self.wfile.closed:
                self.send_error(500, "Internal Server Error")


class FileShareServer:    
    def __init__(self, port: int = 8080):
        self.port = port
        self.server: Optional[HTTPServer] = None
        self.thread: Optional[threading.Thread] = None
        self.running = False
        self.shared_files: List[str] = []
        self.shared_text: Optional[str] = None
        
        self.on_download: Optional[Callable[[str, str], None]] = None
    
    def get_local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _start_server_if_needed(self) -> str:
        if self.running and self.server:
            local_ip = self.get_local_ip()
            return f"http://{local_ip}:{self.port}"

        FileShareHandler.on_download = self.on_download
        
        port = self.port
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                self.server = HTTPServer(('0.0.0.0', port), FileShareHandler)
                break
            except OSError:
                port += 1
                if attempt == max_attempts - 1:
                    raise RuntimeError(f"Could not find available port after {max_attempts} attempts")
        
        self.port = port
        self.running = True
        
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()
        
        local_ip = self.get_local_ip()
        return f"http://{local_ip}:{self.port}"

    def share_files(self, files: List[str]) -> str:
        self.shared_files = files
        FileShareHandler.shared_files = self.shared_files
        return self._start_server_if_needed()

    def add_files(self, files: List[str]):
        if not self.running:
            return

        current_files = set(self.shared_files)
        for f in files:
            if f not in current_files:
                self.shared_files.append(f)

    def share_text(self, text: str) -> str:
        self.shared_text = text
        FileShareHandler.shared_text = self.shared_text
        return self._start_server_if_needed()
    
    def _run_server(self):
        if self.server:
            try:
                self.server.serve_forever()
            except Exception:
                pass
        self.running = False
    
    def stop(self):
        if self.server:
            self.running = False
            self.server.shutdown()
            self.server.server_close()
            self.server = None
        
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2)
            self.thread = None
        
        self.shared_files = []
        self.shared_text = None
        FileShareHandler.shared_files = []
        FileShareHandler.shared_text = None
    
    def is_running(self) -> bool:
        return self.running
    
    def get_url(self) -> Optional[str]:
        if self.running:
            local_ip = self.get_local_ip()
            return f"http://{local_ip}:{self.port}"
        return None