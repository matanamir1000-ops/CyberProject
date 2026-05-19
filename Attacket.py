__author__ = 'Matan Amir'
from scapy.all import *
import socket
import threading
import time
import os
import sys

DEFAULT_IP = '127.0.0.1'
SERVER_PORT = 8888


# רץ ברקע אחרי שהמשחק התחיל ומקשיב להודעות מהשרת.
# בלי זה לא נדע שניצחנו כי input() במנו חוסם אותנו.
def listen_for_messages(sock):
    while True:
        try:
            data = sock.recv(1024).decode()
            if not data:
                break
            print(f"\n[SERVER]: {data}")
            if "WIN" in data:
                print("\n=== GAME OVER ===")
                os._exit(0)
        except:
            break


def main():

    print("--- Attacker Booting Up ---")

    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
    else:
        server_ip = DEFAULT_IP

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server_ip, SERVER_PORT))
        sock.sendall(b"ATK")
        print(f"Connected to {server_ip}:{SERVER_PORT} as ATK. Waiting for Defender and Server sync...")

        while True:
            data = sock.recv(1024).decode()
            if not data:
                break
            print(f"[SERVER]: {data}")
            if "START" in data:
                break
    except ConnectionRefusedError:
        print("Server is offline! Run Server.py first.")
        return

    threading.Thread(target=listen_for_messages, args=(sock,), daemon=True).start()

    print("\n--- GO! Choose your weapon ---")

# כל הפקטות חייבות "GAME:" בהתחלה אחרת הראדאר לא רואה אותן
    while True:
        print("\n=============================")
        print(" 1 - Port Block (dport 8888)")
        print(" 2 - Word Block (GAME:HACK, dport 11111)")
        print(" 3 - IP Block (spoofed 8.8.8.8, dport 10000)")
        print(" 4 - Size Block (fat packet, dport 10000)")
        print(" 5 - Ninja Packet (GAME:NINJA, should pass)")
        print(" 6 - Hacker IP Block (spoofed 13.37.13.37, dport 10000)")
        print(" 7 - New Port Block (dport 6767)")
        print(" 8 - Edge Case (Empty payload 'GAME:', dport 10000)")
        print(" 9 - Word Block 2 (GAME:VIRUS, dport 10000)")
        print(" 10 - Ghost Packet (GAME:GHOST, should pass)")
        print("=============================")
        choice = input("Pick a packet (1-10): ").strip()

        if choice == "1":
            packet = IP(dst=server_ip) / UDP(dport=8888) / Raw(load="GAME:TEST")
            send(packet)
        elif choice == "2":
            packet = IP(dst=server_ip) / UDP(dport=11111) / Raw(load="GAME:HACK")
            send(packet)
        elif choice == "3":
            packet = IP(src="8.8.8.8", dst=server_ip) / UDP(dport=10000) / Raw(load="GAME:HELLO")
            send(packet)
        elif choice == "4":
            heavy_payload = "GAME:" + "A" * 1500
            packet = IP(dst=server_ip) / UDP(dport=10000) / Raw(load=heavy_payload)
            send(packet)
        elif choice == "5":
            packet = IP(dst=server_ip) / UDP(dport=10000) / Raw(load="GAME:NINJA")
            send(packet)
        elif choice == "6":
            packet = IP(src="13.37.13.37", dst=server_ip) / UDP(dport=10000) / Raw(load="GAME:PING")
            send(packet)
        elif choice == "7":
            packet = IP(dst=server_ip) / UDP(dport=6767) / Raw(load="GAME:PROBE")
            send(packet)
        elif choice == "8":
            packet = IP(dst=server_ip) / UDP(dport=10000) / Raw(load="GAME:")
            send(packet)
        elif choice == "9":
            packet = IP(dst=server_ip) / UDP(dport=10000) / Raw(load="GAME:VIRUS")
            send(packet)
        elif choice == "10":
            packet = IP(dst=server_ip) / UDP(dport=10000) / Raw(load="GAME:GHOST")
            send(packet)
        else:
            print("Invalid choice, try again.")

        time.sleep(0.5)

if __name__ == '__main__':
    main()