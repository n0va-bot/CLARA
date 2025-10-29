#!/usr/bin/env python3

import socket
import threading
import mimetypes
from pathlib import Path
from typing import List, Optional, Callable
from http.server import HTTPServer, BaseHTTPRequestHandler
import html
import json

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
    
    def _get_base_html(self, title: str, body_content: str, initial_data_script: str = "") -> str:
        return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
    <title>{html.escape(title)}</title>
    <style type="text/css">
        html, body {{ margin:0; padding:0; }}
        body {{
            font-family: Arial, Helvetica, sans-serif;
            background: #f3f4f6;
            color: #222;
            padding: 20px;
            line-height: 1.4;
            font-size: 14px;
        }}
        .container {{
            width: 760px;
            max-width: 98%;
            margin: 0 auto;
            background: #ffffff;
            border: 1px solid #cfcfcf;
            padding: 16px;
        }}
        .header {{
            padding-bottom: 12px;
            border-bottom: 2px solid #e6e6e6;
            overflow: hidden;
        }}
        .brand {{
            float: left;
            font-weight: bold;
            font-size: 20px;
            color: #2b65a3;
        }}
        .subtitle {{
            float: right;
            color: #666;
            font-size: 12px;
            margin-top: 4px;
            text-align: right;
        }}
        .main {{
            margin-top: 16px;
            overflow: hidden;
        }}
        .left-col {{
            float: left;
            width: 60%;
            min-width: 300px;
        }}
        .right-col {{
            float: left;
            width: 36%;
            min-width: 160px;
            margin-left: 12px;
        }}
        .section {{ margin-bottom: 18px; }}
        h2 {{
            font-size: 16px;
            margin: 6px 0 10px 0;
            color: #333;
        }}
        p {{ margin: 8px 0; color: #444; }}
        table.file-list {{
            width: 100%;
            border-collapse: collapse;
            border-spacing: 0;
        }}
        table.file-list th, table.file-list td {{
            padding: 8px 6px;
            border-bottom: 1px solid #eaeaea;
            text-align: left;
            vertical-align: middle;
        }}
        table.file-list th {{
            background: #f7f7f7;
            font-size: 13px;
            color: #333;
        }}
        a.button {{
            display: inline-block;
            padding: 6px 10px;
            text-decoration: none;
            border: 1px solid #9fb3d6;
            background: #e9f0fb;
            color: #1a4f86;
            cursor: pointer;
            font-size: 13px;
        }}
        a.button:hover {{ text-decoration: underline; }}
        textarea.share-text {{
            width: 98%;
            height: 220px;
            font-family: "Courier New", Courier, monospace;
            font-size: 12px;
            padding: 6px;
            border: 1px solid #ccc;
            background: #fafafa;
        }}
        .clearfix {{ display: block; }}
        .footer {{
            margin-top: 16px;
            padding-top: 12px;
            border-top: 1px solid #eaeaea;
            text-align: center;
            font-size: 11px;
            color: #888;
        }}
        .footer a {{
            color: #555;
            text-decoration: none;
        }}
        .footer a:hover {{ text-decoration: underline; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">CLARA Share</div>
            <div class="subtitle">Simple file &amp; text sharing — local network</div>
        </div>
        {body_content}
        <div class="footer">
            <p>Powered by <a href="https://github.com/n0va-bot/CLARA" target="_blank">CLARA</a>, your friendly desktop assistant.</p>
        </div>
    </div>
    {initial_data_script}
    <script type="text/javascript">
        (function() {{
            var lastData = '';

            function updateContent(data) {{
                var textContainer = document.getElementById('shared-text-container');
                var filesContainer = document.getElementById('shared-files-container');
                var noContent = document.getElementById('no-content-message');

                var hasText = data.text && data.text.length > 0;
                var hasFiles = data.files && data.files.length > 0;

                if (textContainer) {{
                    var textHtml = '';
                    if (hasText) {{
                        textHtml = '<h2>Shared Text</h2>' +
                                   '<p>Select the text below and copy it to your clipboard.</p>' +
                                   '<textarea class="share-text" readonly="readonly">' + data.text + '</textarea>';
                    }}
                    textContainer.innerHTML = textHtml;
                }}

                if (filesContainer) {{
                    var filesHtml = '';
                    if (hasFiles) {{
                        var rows = '';
                        for (var i = 0; i < data.files.length; i++) {{
                            var file = data.files[i];
                            rows += '<tr>' +
                                      '<td>' + file.name + '</td>' +
                                      '<td>' + file.size + '</td>' +
                                      '<td><a class="button" href="' + file.url + '">Download</a></td>' +
                                    '</tr>';
                        }}
                        filesHtml = '<h2>Shared Files</h2>' +
                                    '<p>Click a button to download the corresponding file.</p>' +
                                    '<table class="file-list" cellpadding="0" cellspacing="0">' +
                                    '<tr><th>Filename</th><th>Size</th><th>Action</th></tr>' + rows + '</table>';
                    }}
                    filesContainer.innerHTML = filesHtml;
                }}
                
                if (noContent) {{
                    noContent.style.display = (hasText || hasFiles) ? 'none' : 'block';
                }}
            }}

            function fetchData() {{
                var xhr = new (window.XMLHttpRequest || ActiveXObject)('MSXML2.XMLHTTP.3.0');
                xhr.open('GET', '/api/data', true);
                xhr.onreadystatechange = function () {{
                    if (xhr.readyState === 4 && xhr.status === 200) {{
                        if (xhr.responseText !== lastData) {{
                            lastData = xhr.responseText;
                            try {{
                                var data = JSON.parse(xhr.responseText);
                                updateContent(data);
                            }} catch (e) {{}}
                        }}
                    }}
                }};
                xhr.send(null);
            }}

            if (typeof initialDataJSON !== 'undefined' && initialDataJSON) {{
                lastData = initialDataJSON;
                try {{
                    var initialData = JSON.parse(initialDataJSON);
                    updateContent(initialData);
                }} catch (e) {{}}
            }}

            setInterval(fetchData, 5000);
        }})();
    </script>
</body>
</html>"""

    def do_GET(self):
        if self.path == '/':
            self.send_combined_index_page()
        elif self.path.startswith('/download/'):
            self.handle_download()
        elif self.path == '/api/data':
            self.send_api_data()
        else:
            self.send_error(404, "Not Found")

    def _get_api_data_dict(self):
        files_data = []
        for i, filepath in enumerate(self.shared_files):
            try:
                path = Path(filepath)
                if path.exists() and path.is_file():
                    files_data.append({
                        "name": html.escape(path.name),
                        "size": format_size(path.stat().st_size),
                        "url": f"/download/{i}"
                    })
            except Exception:
                continue
        
        return {
            "text": html.escape(self.shared_text or ""),
            "files": files_data
        }

    def send_combined_index_page(self):
        has_content = bool(self.shared_text or self.shared_files)
        
        hostname = socket.gethostname()
        total_size_info = ""
        if self.shared_files:
            total_size_bytes = 0
            for filepath in self.shared_files:
                try:
                    p = Path(filepath)
                    if p.is_file():
                        total_size_bytes += p.stat().st_size
                except (FileNotFoundError, OSError):
                    pass
            if total_size_bytes > 0:
                total_size_info = f'<p><strong>Total Size:</strong><br/><span>{format_size(total_size_bytes)}</span></p>'

        main_content = f"""<div class="main clearfix">
    <div class="left-col">
        <div class="section" id="shared-text-container"></div>
        <div class="section" id="shared-files-container"></div>
    </div>
    <div class="right-col">
        <div class="section">
            <h2>Quick Info</h2>
            <p><strong>Host:</strong><br/><span>{html.escape(hostname)}</span></p>
            <p><strong>URL:</strong><br/><span>{html.escape(f"http://{self._get_local_ip()}:%s/")}</span></p>
            {total_size_info}
            <p><strong>Status:</strong><br/><span>Server running</span></p>
        </div>
    </div>
    <div id="no-content-message" style="display: {'none' if has_content else 'block'};">
        <p>No content is currently being shared.</p>
    </div>
</div>""" % self.server.server_address[1] #type: ignore

        initial_data_dict = self._get_api_data_dict()
        json_string = json.dumps(initial_data_dict)
        initial_data_script = f'<script type="text/javascript">var initialDataJSON = {json.dumps(json_string)};</script>'

        html_content = self._get_base_html(
            "CLARA Share", 
            main_content, 
            initial_data_script=initial_data_script
        ).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.send_header('Content-Length', str(len(html_content)))
        self.end_headers()
        self.wfile.write(html_content)

    def send_api_data(self):
        data = self._get_api_data_dict()
        json_response = json.dumps(data).encode('utf-8')
        
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(json_response)))
        self.end_headers()
        self.wfile.write(json_response)
    
    def _get_local_ip(self) -> str:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"
    
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