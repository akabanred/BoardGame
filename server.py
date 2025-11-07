import socket
import threading

HOST = '0.0.0.0'
PORT = 5555

clients = []

def handle_client(conn, addr):
    print(f"[KẾT NỐI] {addr}")
    clients.append(conn)
    try:
        while True:
            data = conn.recv(1024)
            if not data:
                break
            # Gửi cho client còn lại
            for c in clients:
                if c != conn:
                    c.sendall(data)
    except:
        pass
    finally:
        print(f"[NGẮT] {addr}")
        clients.remove(conn)
        conn.close()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(2)
    print(f"[SERVER] Đang lắng nghe tại {HOST}:{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()