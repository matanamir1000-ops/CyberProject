__author__ = 'Matan Amir'
from scapy.all import *
import socket
import threading
import time
import os


# רץ ברקע אחרי שהמשחק התחיל ומקשיב להודעות מהשרת.
# בלי זה לא נדע שניצחנו כי input() במנו חוסם אותנו.
def listen_for_messages(sock):
    while True:
        try:
            data = sock.recv(1024).decode()
            if not data:
                break
            print(f"\n[SERVER]: {data}")
            # הגיע סוף משחק - מודיעים ויוצאים
            if "WIN" in data:
                print("\n=== GAME OVER ===")
                os._exit(0)
        except:
            break


def main():

    print("--- Attacker Booting Up ---")

    # מתחברים לשרת ומזדהים כתוקף - בלי זה השרת לא יתחיל את המשחק
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect(('127.0.0.1', 8888))
        sock.sendall(b"ATK")
        print("Connected as ATK. Waiting for Defender and Server sync...")

        # מחכים שהשרת יסיים את הספירה לאחור וישלח START
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

    # מעבירים את ההאזנה לת'רד ברקע כי המנו חוסם עם input()
    threading.Thread(target=listen_for_messages, args=(sock,), daemon=True).start()

    print("\n--- GO! Choose your weapon ---")

    # כל הפקטות חייבות "GAME:" בהתחלה אחרת הראדאר לא רואה אותן
    while True:
        print("\n=============================")
        print(" 1 - Port Block (dport 8888)")
        print(" 2 - Word Block (GAME:HACK)")
        print(" 3 - IP Block (spoofed 8.8.8.8)")
        print(" 4 - Size Block (fat packet)")
        print(" 5 - Ninja Packet (should pass)")
        print("=============================")
        choice = input("Pick a packet (1-5): ").strip()

        if choice == "1":
            packet = IP(dst="127.0.0.1") / UDP(dport=8888) / Raw(load="GAME:TEST")
            send(packet)
        elif choice == "2":
            packet = IP(dst="127.0.0.1") / UDP(dport=10000) / Raw(load="GAME:HACK")
            send(packet)
        elif choice == "3":
            packet = IP(src="8.8.8.8", dst="127.0.0.1") / UDP(dport=10000) / Raw(load="GAME:HELLO")
            send(packet)
        elif choice == "4":
            # מטען שמן של 1500 תווים, אמור לעבור את הגודל המקסימלי
            heavy_payload = "GAME:" + "A" * 1500
            packet = IP(dst="127.0.0.1") / UDP(dport=10000) / Raw(load=heavy_payload)
            send(packet)
        elif choice == "5":
            packet = IP(dst="127.0.0.1") / UDP(dport=10000) / Raw(load="GAME:NINJA")
            send(packet)
        else:
            print("Invalid choice, try again.")

        time.sleep(0.5)

if __name__ == '__main__':
    main()
