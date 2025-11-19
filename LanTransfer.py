#!/usr/bin/env python3
"""
TCP File Transfer - Send and receive files across LAN
Usage:
  Server mode: python script.py server [port]
  Client mode: python script.py client <host> <port> <filepath>
"""

import socket
import os
import sys
import struct
import hashlib
from pathlib import Path

BUFFER_SIZE = 4096
DEFAULT_PORT = 5555


def calculate_md5(filepath):
    """Calculate MD5 hash of a file for integrity verification"""
    hash_md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def send_file(host, port, filepath):
    """Send a file to the server"""
    if not os.path.isfile(filepath):
        print(f"Error: File '{filepath}' not found")
        return False
    
    filepath = Path(filepath)
    filename = filepath.name
    filesize = filepath.stat().st_size
    
    print(f"Connecting to {host}:{port}...")
    
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect((host, port))
            print(f"Connected! Sending '{filename}' ({filesize} bytes)")
            
            # Calculate file hash
            file_hash = calculate_md5(filepath)
            
            # Send filename length and filename
            filename_bytes = filename.encode('utf-8')
            sock.sendall(struct.pack("!I", len(filename_bytes)))
            sock.sendall(filename_bytes)
            
            # Send filesize
            sock.sendall(struct.pack("!Q", filesize))
            
            # Send file hash
            sock.sendall(file_hash.encode('utf-8'))
            
            # Send file data
            bytes_sent = 0
            with open(filepath, 'rb') as f:
                while bytes_sent < filesize:
                    chunk = f.read(BUFFER_SIZE)
                    if not chunk:
                        break
                    sock.sendall(chunk)
                    bytes_sent += len(chunk)
                    
                    # Progress indicator
                    progress = (bytes_sent / filesize) * 100
                    print(f"\rProgress: {progress:.1f}% ({bytes_sent}/{filesize} bytes)", end='')
            
            print("\n✓ File sent successfully!")
            
            # Wait for verification from server
            verification = sock.recv(2)
            if verification == b"OK":
                print("✓ Server verified file integrity")
                return True
            else:
                print("✗ Server reported integrity check failed")
                return False
                
    except ConnectionRefusedError:
        print(f"Error: Could not connect to {host}:{port}")
        return False
    except Exception as e:
        print(f"Error sending file: {e}")
        return False


def receive_file(port, save_dir="."):
    """Start server to receive files"""
    save_dir = Path(save_dir)
    save_dir.mkdir(exist_ok=True)
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
        server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_sock.bind(('0.0.0.0', port))
        server_sock.listen(1)
        
        print(f"Server listening on port {port}")
        print(f"Files will be saved to: {save_dir.absolute()}")
        print("Waiting for connection...\n")
        
        while True:
            try:
                conn, addr = server_sock.accept()
                print(f"Connection from {addr[0]}:{addr[1]}")
                
                with conn:
                    # Receive filename length
                    filename_len_data = conn.recv(4)
                    if not filename_len_data:
                        continue
                    filename_len = struct.unpack("!I", filename_len_data)[0]
                    
                    # Receive filename
                    filename = conn.recv(filename_len).decode('utf-8')
                    
                    # Receive filesize
                    filesize_data = conn.recv(8)
                    filesize = struct.unpack("!Q", filesize_data)[0]
                    
                    # Receive file hash
                    expected_hash = conn.recv(32).decode('utf-8')
                    
                    print(f"Receiving: {filename} ({filesize} bytes)")
                    
                    # Save file
                    filepath = save_dir / filename
                    bytes_received = 0
                    
                    with open(filepath, 'wb') as f:
                        while bytes_received < filesize:
                            remaining = filesize - bytes_received
                            chunk_size = min(BUFFER_SIZE, remaining)
                            chunk = conn.recv(chunk_size)
                            
                            if not chunk:
                                break
                            
                            f.write(chunk)
                            bytes_received += len(chunk)
                            
                            # Progress indicator
                            progress = (bytes_received / filesize) * 100
                            print(f"\rProgress: {progress:.1f}% ({bytes_received}/{filesize} bytes)", end='')
                    
                    print(f"\n✓ File received: {filepath}")
                    
                    # Verify file integrity
                    received_hash = calculate_md5(filepath)
                    if received_hash == expected_hash:
                        print("✓ File integrity verified (MD5 match)")
                        conn.sendall(b"OK")
                    else:
                        print("✗ Warning: File integrity check failed!")
                        conn.sendall(b"ER")
                    
                    print("\nWaiting for next connection...\n")
                    
            except KeyboardInterrupt:
                print("\nServer shutting down...")
                break
            except Exception as e:
                print(f"Error receiving file: {e}")


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    
    mode = sys.argv[1].lower()
    
    if mode == "server":
        port = int(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_PORT
        receive_file(port)
        
    elif mode == "client":
        if len(sys.argv) < 5:
            print("Usage: python script.py client <host> <port> <filepath>")
            sys.exit(1)
        
        host = sys.argv[2]
        port = int(sys.argv[3])
        filepath = sys.argv[4]
        
        send_file(host, port, filepath)
        
    else:
        print(f"Unknown mode: {mode}")
        print(__doc__)
        sys.exit(1)


if __name__ == "__main__":
    main()