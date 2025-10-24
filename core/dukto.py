#!/usr/bin/env python3

import socket
import struct
import threading
import os
import platform
import getpass
from pathlib import Path
from typing import List, Optional, Callable, Dict

DEFAULT_UDP_PORT = 4644
DEFAULT_TCP_PORT = 4644


class Peer:
    def __init__(self, address: str, signature: str, port: int = DEFAULT_UDP_PORT):
        self.address = address
        self.signature = signature
        self.port = port
    
    def __repr__(self):
        return f"Peer({self.address}, {self.signature}, port={self.port})"


class DuktoProtocol:    
    def __init__(self):
        self.local_udp_port = DEFAULT_UDP_PORT
        self.local_tcp_port = DEFAULT_TCP_PORT
        
        self.udp_socket: Optional[socket.socket] = None
        self.tcp_server: Optional[socket.socket] = None
        
        self.peers: Dict[str, Peer] = {}
        self.is_sending = False
        self.is_receiving = False
        self.is_awaiting_approval = False
        
        self.running = False
        
        # Confirmation for receiving
        self._transfer_decision = threading.Event()
        self._transfer_approved = False
        
        # Callbacks
        self.on_peer_added: Optional[Callable[[Peer], None]] = None
        self.on_peer_removed: Optional[Callable[[Peer], None]] = None
        self.on_receive_start: Optional[Callable[[str], None]] = None
        self.on_receive_request: Optional[Callable[[str], None]] = None
        self.on_receive_complete: Optional[Callable[[List[str], int], None]] = None
        self.on_receive_text: Optional[Callable[[str, int], None]] = None
        self.on_send_complete: Optional[Callable[[List[str]], None]] = None
        self.on_transfer_progress: Optional[Callable[[int, int], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None
        
    def set_ports(self, udp_port: int, tcp_port: int):
        self.local_udp_port = udp_port
        self.local_tcp_port = tcp_port
    
    def get_system_signature(self) -> str:
        username = getpass.getuser()
        hostname = socket.gethostname()
        system = platform.system()
        return f"{username} at {hostname} ({system})"
    
    def initialize(self):
        # UDP Socket for peer discovery
        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.udp_socket.bind(('', self.local_udp_port))
        
        # TCP Server for receiving files
        self.tcp_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.tcp_server.bind(('', self.local_tcp_port))
        self.tcp_server.listen(5)
        
        self.running = True
        
        # Start listener threads
        threading.Thread(target=self._udp_listener, daemon=True).start()
        threading.Thread(target=self._tcp_listener, daemon=True).start()
        
    def say_hello(self, dest: str = '<broadcast>', port: int = None):
        if port is None:
            port = self.local_udp_port
        
        # Prepare packet
        if port == DEFAULT_UDP_PORT and self.local_udp_port == DEFAULT_UDP_PORT:
            if dest == '<broadcast>':
                msg_type = b'\x01'  # HELLO MESSAGE (broadcast)
            else:
                msg_type = b'\x02'  # HELLO MESSAGE (unicast)
            packet = msg_type + self.get_system_signature().encode('utf-8')
        else:
            if dest == '<broadcast>':
                msg_type = b'\x04'  # HELLO MESSAGE (broadcast) with PORT
            else:
                msg_type = b'\x05'  # HELLO MESSAGE (unicast) with PORT
            packet = msg_type + struct.pack('<H', self.local_udp_port) + \
                     self.get_system_signature().encode('utf-8')
        
        # Send packet
        if dest == '<broadcast>':
            self._send_to_all_broadcast(packet, port)
            if port != DEFAULT_UDP_PORT:
                self._send_to_all_broadcast(packet, DEFAULT_UDP_PORT)
        else:
            self.udp_socket.sendto(packet, (dest, port))
    
    def say_goodbye(self):
        packet = b'\x03' + b'Bye Bye'
        
        # Collect all discovered ports
        ports = {self.local_udp_port}
        if self.local_udp_port != DEFAULT_UDP_PORT:
            ports.add(DEFAULT_UDP_PORT)
        for peer in self.peers.values():
            ports.add(peer.port)
        
        # Send to all ports
        for port in ports:
            self._send_to_all_broadcast(packet, port)
    
    def send_file(self, ip_dest: str, files: List[str], port: int = 0):
        if port == 0:
            port = DEFAULT_TCP_PORT
        
        if self.is_receiving or self.is_sending:
            if self.on_error:
                self.on_error("Already busy with another transfer")
            return
        
        self.is_sending = True
        threading.Thread(target=self._send_file_thread, 
                        args=(ip_dest, port, files), daemon=True).start()
    
    def send_text(self, ip_dest: str, text: str, port: int = 0):
        if port == 0:
            port = DEFAULT_TCP_PORT
        
        if self.is_receiving or self.is_sending:
            if self.on_error:
                self.on_error("Already busy with another transfer")
            return
        
        self.is_sending = True
        threading.Thread(target=self._send_text_thread,
                        args=(ip_dest, port, text), daemon=True).start()
    
    def approve_transfer(self):
        self._transfer_approved = True
        self._transfer_decision.set()

    def reject_transfer(self):
        self._transfer_approved = False
        self._transfer_decision.set()

    def _udp_listener(self):
        while self.running:
            try:
                data, addr = self.udp_socket.recvfrom(4096)
                self._handle_message(data, addr[0])
            except Exception as e:
                if self.running:
                    print(f"UDP listener error: {e}")
    
    def _handle_message(self, data: bytes, sender: str):
        if len(data) == 0:
            return
        
        msg_type = data[0]
        
        if msg_type in (0x01, 0x02):  # HELLO (broadcast/unicast)
            signature = data[1:].decode('utf-8', errors='ignore')
            if signature != self.get_system_signature():
                self.peers[sender] = Peer(sender, signature, DEFAULT_UDP_PORT)
                if msg_type == 0x01:  # Reply to broadcast
                    self.say_hello(sender, DEFAULT_UDP_PORT)
                if self.on_peer_added:
                    self.on_peer_added(self.peers[sender])
        
        elif msg_type == 0x03:  # GOODBYE
            if sender in self.peers:
                peer = self.peers[sender]
                if self.on_peer_removed:
                    self.on_peer_removed(peer)
                del self.peers[sender]
        
        elif msg_type in (0x04, 0x05):  # HELLO with PORT
            port = struct.unpack('<H', data[1:3])[0]
            signature = data[3:].decode('utf-8', errors='ignore')
            if signature != self.get_system_signature():
                self.peers[sender] = Peer(sender, signature, port)
                if msg_type == 0x04:  # Reply to broadcast
                    self.say_hello(sender, port)
                if self.on_peer_added:
                    self.on_peer_added(self.peers[sender])
    
    def _tcp_listener(self):
        while self.running:
            try:
                conn, addr = self.tcp_server.accept()
                if self.is_receiving or self.is_sending or self.is_awaiting_approval:
                    conn.close()
                    continue
                
                threading.Thread(target=self._handle_transfer_request, 
                               args=(conn, addr[0]), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"TCP listener error: {e}")

    def _handle_transfer_request(self, conn: socket.socket, sender_ip: str):
        try:
            self.is_awaiting_approval = True
            self._transfer_decision.clear()

            if self.on_receive_request:
                self.on_receive_request(sender_ip)
            else:
                self.reject_transfer()

            self._transfer_decision.wait()

            if self._transfer_approved:
                self._receive_files(conn, sender_ip)
            else:
                conn.close()
        finally:
            self.is_awaiting_approval = False

    def _receive_files(self, conn: socket.socket, sender_ip: str):
        self.is_receiving = True
        
        if self.on_receive_start:
            self.on_receive_start(sender_ip)
        
        try:
            conn.settimeout(10)
            
            # Read header
            header = conn.recv(16)
            if len(header) < 16:
                return
            
            elements_count = struct.unpack('<Q', header[0:8])[0]
            total_size = struct.unpack('<Q', header[8:16])[0]
            
            conn.settimeout(None)
            
            received_files = []
            total_received = 0
            root_folder_name = ""
            root_folder_renamed = ""
            receiving_text = False
            text_data = b""
            
            for _ in range(elements_count):
                # Read element name
                name_bytes = b""
                while True:
                    c = conn.recv(1)
                    if not c or c == b'\x00':
                        break
                    name_bytes += c
                
                name = name_bytes.decode('utf-8')
                
                # Read element size
                size_bytes = conn.recv(8)
                element_size = struct.unpack('<q', size_bytes)[0]
                
                if element_size == -1:  # Directory
                    root_name = name.split('/')[0]
                    
                    if root_folder_name != root_name:
                        # Find unique name
                        i = 2
                        original_name = name
                        while os.path.exists(name):
                            name = f"{original_name} ({i})"
                            i += 1
                        root_folder_name = original_name
                        root_folder_renamed = name
                        received_files.append(name)
                    elif root_folder_name != root_folder_renamed:
                        name = name.replace(root_folder_name, root_folder_renamed, 1)
                    
                    os.makedirs(name, exist_ok=True)
                
                elif name == "___DUKTO___TEXT___":  # Text transfer
                    receiving_text = True
                    received_files.append(name)
                    text_data = b""
                    
                    # Read text data
                    received = 0
                    while received < element_size:
                        chunk = conn.recv(min(8192, element_size - received))
                        if not chunk:
                            break
                        text_data += chunk
                        received += len(chunk)
                        total_received += len(chunk)
                        if self.on_transfer_progress:
                            self.on_transfer_progress(total_size, total_received)
                
                else:  # Regular file
                    if '/' in name and name.split('/')[0] == root_folder_name:
                        name = name.replace(root_folder_name, root_folder_renamed, 1)
                    
                    # Find unique filename
                    i = 2
                    original_name = name
                    base_path = Path(name)
                    while os.path.exists(name):
                        name = f"{base_path.stem} ({i}){base_path.suffix}"
                        i += 1
                    
                    received_files.append(name)
                    
                    # Receive file data
                    with open(name, 'wb') as f:
                        received = 0
                        while received < element_size:
                            chunk = conn.recv(min(8192, element_size - received))
                            if not chunk:
                                break
                            f.write(chunk)
                            received += len(chunk)
                            total_received += len(chunk)
                            if self.on_transfer_progress:
                                self.on_transfer_progress(total_size, total_received)
            
            # Transfer complete
            if receiving_text:
                text = text_data.decode('utf-8')
                if self.on_receive_text:
                    self.on_receive_text(text, total_size)
            else:
                if self.on_receive_complete:
                    self.on_receive_complete(received_files, total_size)
        
        except Exception as e:
            if self.on_error:
                self.on_error(f"Receive error: {e}")
        
        finally:
            conn.close()
            self.is_receiving = False
    
    def _send_file_thread(self, ip_dest: str, port: int, files: List[str]):
        try:
            # Expand file tree
            expanded_files = self._expand_tree(files)
            
            # Connect
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip_dest, port))
            
            # Calculate total size
            total_size = self._compute_total_size(expanded_files)
            
            # Send header
            header = struct.pack('<Q', len(expanded_files))
            header += struct.pack('<Q', total_size)
            sock.sendall(header)
            
            base_path = str(Path(files[0]).parent)
            sent_data = len(header)
            
            # Send each element
            for filepath in expanded_files:
                path = Path(filepath)
                relative_name = str(path.relative_to(base_path))
                
                # Send name
                sock.sendall(relative_name.encode('utf-8') + b'\x00')
                
                if path.is_dir():
                    # Send directory marker
                    sock.sendall(struct.pack('<q', -1))
                else:
                    # Send file size
                    file_size = path.stat().st_size
                    sock.sendall(struct.pack('<q', file_size))
                    
                    # Send file data
                    with open(filepath, 'rb') as f:
                        while True:
                            chunk = f.read(10000)
                            if not chunk:
                                break
                            sock.sendall(chunk)
                            sent_data += len(chunk)
                            if self.on_transfer_progress:
                                self.on_transfer_progress(total_size, sent_data)
            
            sock.close()
            
            if self.on_send_complete:
                self.on_send_complete(files)
        
        except Exception as e:
            if self.on_error:
                self.on_error(f"Send error: {e}")
        
        finally:
            self.is_sending = False
    
    def _send_text_thread(self, ip_dest: str, port: int, text: str):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((ip_dest, port))
            
            text_bytes = text.encode('utf-8')
            total_size = len(text_bytes)
            
            # Send header
            header = struct.pack('<Q', 1)  # 1 element
            header += struct.pack('<Q', total_size)
            sock.sendall(header)
            
            # Send text marker
            sock.sendall(b'___DUKTO___TEXT___\x00')
            sock.sendall(struct.pack('<q', total_size))
            
            # Send text data
            sock.sendall(text_bytes)
            
            sock.close()
            
            if self.on_send_complete:
                self.on_send_complete(["___DUKTO___TEXT___"])
        
        except Exception as e:
            if self.on_error:
                self.on_error(f"Send text error: {e}")
        
        finally:
            self.is_sending = False
    
    def _expand_tree(self, files: List[str]) -> List[str]:
        expanded = []
        
        for filepath in files:
            path = Path(filepath)
            if path.is_dir():
                self._add_recursive(expanded, path)
            else:
                expanded.append(str(path))
        
        return expanded
    
    def _add_recursive(self, expanded: List[str], path: Path):
        expanded.append(str(path))
        
        if path.is_dir():
            for entry in path.iterdir():
                self._add_recursive(expanded, entry)
    
    def _compute_total_size(self, files: List[str]) -> int:
        total = 0
        for filepath in files:
            path = Path(filepath)
            if path.is_file():
                total += path.stat().st_size
        return total
    
    def _send_to_all_broadcast(self, packet: bytes, port: int):
        # Try common broadcast
        try:
            self.udp_socket.sendto(packet, ('255.255.255.255', port))
        except:
            pass
    
    def shutdown(self):
        self.running = False
        self.say_goodbye()
        
        if self.udp_socket:
            self.udp_socket.close()
        if self.tcp_server:
            self.tcp_server.close()