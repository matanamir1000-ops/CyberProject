__author__ = 'Matan Amir'
import socket
import time
import threading
import os
from scapy.all import *


def check_winner(scores, connected_players):
    """מסיים את המשחק אם שחקן הגיע ל-10 נקודות: מודיע לשניהם, סוגר וסוגר את השרת."""
    if scores["DEF"] >= 10:
        msg = b"DEFENDER WINS~"
    elif scores["ATK"] >= 10:
        msg = b"ATTACKER WINS~"
    else:
        return
    for s in connected_players.values():
        try: s.sendall(msg)
        except: pass
    time.sleep(1)  # מאפשר ל-OS לרוקן את באפר השליחה לפני הסגירה
    for s in connected_players.values():
        try: s.close()
        except: pass
    print(f"{msg.decode()}")
    os._exit(0)  # sniff() חוסם לעד והת'רדים לא ייסגרו לבד


def radar_sniffer(active_rules, connected_players, scores):
    """ת'רד רקע: מסנן פקטות UDP של המשחק ומריץ עליהן את לוגיקת חומת האש."""
    print("Radar is online! Scanning for packets...")

    def process_packet(packet):
        if UDP in packet and packet[UDP].dport > 1000:
            if Raw not in packet:
                return
            if not packet[Raw].load.startswith(b"GAME:"):
                return

            print("Caught a packet! Analyzing...")
            data = packet[Raw].load.decode(errors='ignore')[5:]

            if data in active_rules["words"]:
                print(f"BLOCKED! Caught forbidden word: {data}")
                if "ATK" in connected_players: connected_players["ATK"].sendall(b"MISSED~")
                if "DEF" in connected_players: connected_players["DEF"].sendall(b"SCORED~")
                scores["DEF"] += 1
                check_winner(scores, connected_players)
                return

            if len(packet) > active_rules["max_size"]:
                print(f"BLOCKED! Packet size {len(packet)} exceeded max size.")
                if "ATK" in connected_players: connected_players["ATK"].sendall(b"MISSED~")
                if "DEF" in connected_players: connected_players["DEF"].sendall(b"SCORED~")
                scores["DEF"] += 1
                check_winner(scores, connected_players)
                return

            if IP in packet:
                sender_ip = packet[IP].src
                if sender_ip in active_rules["ips"]:
                    print(f"BLOCKED! Source IP {sender_ip} is banned.")
                    if "ATK" in connected_players: connected_players["ATK"].sendall(b"MISSED~")
                    if "DEF" in connected_players: connected_players["DEF"].sendall(b"SCORED~")
                    scores["DEF"] += 1
                    check_winner(scores, connected_players)
                    return

            target_port = packet[UDP].dport
            if target_port in active_rules["ports"]:
                print(f"BLOCKED! Port {target_port} is closed.")
                if "ATK" in connected_players: connected_players["ATK"].sendall(b"MISSED~")
                if "DEF" in connected_players: connected_players["DEF"].sendall(b"SCORED~")
                scores["DEF"] += 1
                check_winner(scores, connected_players)
                return

            print("PASS! The packet successfully bypassed the firewall!")
            if "DEF" in connected_players: connected_players["DEF"].sendall(b"MISSED~")
            if "ATK" in connected_players: connected_players["ATK"].sendall(b"SCORED~")
            scores["ATK"] += 1
            check_winner(scores, connected_players)


    packets = sniff(filter="udp", prn=process_packet)

def handle_client(sock, addr , connected_players, active_rules):
    """מטפל בלקוח יחיד: הזדהות, סנכרון תחילת משחק וקליטת חוקים מהמגן."""
    expected_bytes = 3
    data = b''
    while len(data) < expected_bytes:
        packet = sock.recv(expected_bytes - len(data))
        if not packet:
            print(f"Client {addr} disconnected before identifying.")
            sock.close()
            return
        data += packet
    role = data.decode().strip().upper()
    if role not in ["DEF", "ATK"]:
        print(f"[SERVER LOG] Client {addr} sent invalid role: '{role}'. Disconnecting.")
        sock.close()
        return
    if role in connected_players:
        sock.sendall(b"Role taken~")
        print(f"[SERVER LOG] Role {role} is already taken!")
        sock.close()
        return
    print(f"Client {addr} identified as: {role}")
    connected_players[role] = sock

    while len(connected_players) < 2:
        time.sleep(0.1)

    for i in range(3, 0, -1):
        sock.sendall(f"{i}~".encode())
        time.sleep(1)
    sock.sendall(b'START~')

    # TCP עלול לשבור הודעות באמצע, לכן אוגרים בבאפר ומפצלים על התו ~ שמסמן סוף הודעה
    buffer = ""
    while True:
        try:
            data = sock.recv(1024).decode()
        except ConnectionResetError:
            print(f"[SERVER LOG] Client {role} forcefully disconnected (Connection Reset).")
            break
        if not data:
            print(f"[SERVER LOG] Client {role} gracefully disconnected.")
            break
        buffer += data
        while "~" in buffer:
            message, buffer = buffer.split("~", 1)
            print(f"Got a COMPLETE message: {message}")
            if role == "DEF":
                try:
                    code, rule = message.strip().split(" ", 1)
                    if code.upper() == "P":
                        active_rules["ports"].append(int(rule))
                    if code.upper() == "W":
                        active_rules["words"].append(rule)
                    if code.upper()  == "I":
                        active_rules["ips"].append(rule)
                    if code.upper()  == "S*S":
                        active_rules["max_size"] = int(rule)
                except ValueError:
                    print(f"Invalid rule format from DEF: {message}")




def main():
    active_rules = {
        "ports": [],
        "words": [],
        "ips": [],
        "max_size": 2**16 - 1
    }
    connected_players = {}
    scores = {"DEF": 0, "ATK": 0}

    # ת'רד נפרד: sniff() חוסם
    radar_thread = threading.Thread(target=radar_sniffer, args=(active_rules, connected_players, scores))
    radar_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # SO_REUSEADDR: עוקף את TIME_WAIT כדי לתפוס את הפורט מיד בהרצה חוזרת
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8888))
    server_socket.listen(20)
    print("Server is listening on port 8888...")
    while True:
        sock, addr = server_socket.accept()
        t = threading.Thread(target=handle_client, args=(sock, addr, connected_players, active_rules))
        t.start()

if __name__ == "__main__":
    main()
