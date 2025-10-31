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
    html_template: Optional[str] = None
    
    def log_message(self, format, *args):
        pass
    
    @classmethod
    def load_html_template(cls):
        if cls.html_template is None:
            template_path = Path(__file__).parent / "share.html"
            try:
                with open(template_path, 'r', encoding='utf-8') as f:
                    cls.html_template = f.read()
            except FileNotFoundError:
                raise RuntimeError(f"HTML template not found at {template_path}")
        return cls.html_template
    
    def _get_base_html(self, hostname: str, url: str, total_size_info: str, 
                       no_content_display: str, initial_data_json: str) -> str:
        template = self.load_html_template()
        
        replacements = {
            '{{TITLE}}': 'CLARA Share',
            '{{HOSTNAME}}': html.escape(hostname),
            '{{URL}}': html.escape(url),
            '{{TOTAL_SIZE_INFO}}': total_size_info,
            '{{NO_CONTENT_DISPLAY}}': no_content_display,
            '{{INITIAL_DATA_JSON}}': initial_data_json
        }
        
        result = template
        for placeholder, value in replacements.items():
            result = result.replace(placeholder, value)
        
        return result
    
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
                total_size_info = format_size(total_size_bytes)

        initial_data_dict = self._get_api_data_dict()
        json_string = json.dumps(initial_data_dict)
        initial_data_json = json.dumps(json_string)
        
        url = f"http://{self._get_local_ip()}:{self.server.server_address[1]}/" #type: ignore
        no_content_display = 'none' if has_content else 'block'

        html_content = self._get_base_html(
            hostname=hostname,
            url=url,
            total_size_info=total_size_info,
            no_content_display=no_content_display,
            initial_data_json=initial_data_json
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