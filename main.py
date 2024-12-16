import os
import time
from bluetooth import BluetoothSocket, BluetoothError, RFCOMM
import threading
import shutil

def get_files_with_timestamps(folder):
    files = {}
    for root, _, filenames in os.walk(folder):
        for filename in filenames:
            full_path = os.path.join(root, filename)
            relative_path = os.path.relpath(full_path, folder)
            files[relative_path] = os.path.getmtime(full_path)  # Last modified time
    return files

def send_file(sock, file_path, base_folder):
    try:
        relative_path = os.path.relpath(file_path, base_folder)
        file_size = os.path.getsize(file_path)

        sock.send(f"{relative_path}|{file_size}\n")

        ack = sock.recv(1024).decode().strip()
        if ack != "OK":
            print("Error: No acknowledgment from receiver.")
            return False

        with open(file_path, "rb") as file:
            sock.sendfile(file)
        print(f"File sent: {relative_path}")
        return True
    except Exception as e:
        print(f"Error sending file {file_path}: {e}")
        return False

def receive_file(sock, destination_folder):
    try:
        metadata = sock.recv(1024).decode().strip()
        relative_path, file_size = metadata.split("|")
        file_size = int(file_size)

        sock.send("OK".encode())

        destination_path = os.path.join(destination_folder, relative_path)
        os.makedirs(os.path.dirname(destination_path), exist_ok=True)

        with open(destination_path, "wb") as file:
            remaining = file_size
            while remaining > 0:
                chunk = sock.recv(min(4096, remaining))
                file.write(chunk)
                remaining -= len(chunk)
        print(f"File received: {relative_path}")
    except Exception as e:
        print(f"Error receiving file: {e}")

def synchronize_folders(local_folder, remote_files, sock, mode="send"):
    local_files = get_files_with_timestamps(local_folder)

    if mode == "send":
        for relative_path, local_mtime in local_files.items():
            if relative_path not in remote_files or local_mtime > remote_files[relative_path]:
                full_path = os.path.join(local_folder, relative_path)
                send_file(sock, full_path, local_folder)
    elif mode == "receive":
        while True:
            receive_file(sock, local_folder)

def bluetooth_server(local_folder):
    server_socket = BluetoothSocket(RFCOMM)
    try:
        server_socket.bind(("", 1))
        server_socket.listen(1)
        print("Bluetooth server listening for connections...")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connection established with {client_address}")

            remote_files = {}
            synchronize_folders(local_folder, remote_files, client_socket, mode="receive")

            client_socket.close()
    except BluetoothError as e:
        print(f"Bluetooth server error: {e}")
    finally:
        server_socket.close()

def bluetooth_client(remote_mac, local_folder):
    try:
        print(f"Attempting to connect to {remote_mac} via Bluetooth...")
        client_socket = BluetoothSocket(RFCOMM)
        client_socket.connect((remote_mac, 1))
        print(f"Connected to {remote_mac}")

        remote_files = {}
        synchronize_folders(local_folder, remote_files, client_socket, mode="send")

        client_socket.close()
    except BluetoothError as e:
        print(f"Bluetooth client error: {e}")

def main(local_mac, remote_mac, local_folder):
    server_thread = threading.Thread(target=bluetooth_server, args=(local_folder,), daemon=True)
    server_thread.start()

    bluetooth_client(remote_mac, local_folder)

if __name__ == "__main__":
    local_mac_address = "XX:XX:XX:XX:XX:XX"
    remote_mac_address = "YY:YY:YY:YY:YY:YY"
    local_sync_folder = "/path/to/local/folder/"

    main(local_mac_address, remote_mac_address, local_sync_folder)