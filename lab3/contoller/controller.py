import socket
import requests
import time

HOST = "192.168.1.104"
PORT = 9003
API = "http://127.0.0.1:8000"

USER_ID = "1"

def send(cmd):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))
        s.sendall((cmd + "\n").encode())
        return s.recv(8192).decode()

def create_storage():
    print("Creating storage...")
    r = requests.post(f"{API}/storage/create", params={"user_id": USER_ID})
    print(r.json())

def delete_storage():
    print("Deleting storage...")
    requests.delete(f"{API}/storage/{USER_ID}")

def spawn_cube():
    print("Spawning cube...")
    send('script spawnHeldCube()')

def listen():
    print("Listening to Portal 2 console...")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((HOST, PORT))

        while True:
            data = s.recv(4096).decode(errors="ignore")

            if not data:
                continue

            print(data)

            if "Removed prop_weighted_cube(prop_weighted_cube)" in data:
                print("Deleting storage...")
                delete_storage()

def main():
    create_storage()
    spawn_cube()

    listen()

if __name__ == "__main__":
    main()