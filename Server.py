__author__ = 'Matan Amir'
import socket
import time
import threading
import os
from scapy.all import *


# בודק אם מישהו הגיע ל-10 נקודות. אם כן - מודיע לשניים, סוגר הכל ומכבה את השרת.
def check_winner(scores, connected_players):
    if scores["DEF"] >= 10:
        msg = b"DEFENDER WINS~"
    elif scores["ATK"] >= 10:
        msg = b"ATTACKER WINS~"
    else:
        return
    for s in connected_players.values():
        try: s.sendall(msg)
        except: pass
        try: s.close()
        except: pass
    print(f"[GAME OVER] {msg.decode()}")
    # os._exit כי יש לנו ת'רדים שלא ייסגרו לבד (sniff חוסם לעד)
    os._exit(0)


# הראדאר - רץ ברקע ומסנן את כל הפקטות שמגיעות. פה הכל קורה.
def radar_sniffer(active_rules, connected_players, scores):
    print("Radar is online! Scanning for packets...")

    def process_packet(packet):
        # מתעניינים רק ב-UDP על פורטים גבוהים (מתחת ל-1000 זה רעש של המערכת)
        if UDP in packet and packet[UDP].dport > 1000:
            if Raw not in packet:
                return
            # החתימה הסודית שלנו. בלי "GAME:" בהתחלה הפקטה לא רלוונטית למשחק
            if not packet[Raw].load.startswith(b"GAME:"):
                return

            print("Caught a packet! Analyzing...")
            # מורידים את ה-"GAME:" ומשאירים רק את התוכן האמיתי
            data = packet[Raw].load.decode(errors='ignore')[5:]

            if data in active_rules["words"]:
                print(f"BLOCKED! Caught forbidden word: {data}")
                if "ATK" in connected_players: connected_players["ATK"].sendall(b"MISSED~")
                if "DEF" in connected_players: connected_players["DEF"].sendall(b"SCORED~")
                # נקודה למגן - הוא תפס את הפקטה
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

            # עברה את כל הפילטרים - התוקף הצליח לעקוף את החומה!
            print("PASS! The packet successfully bypassed the firewall!")
            if "DEF" in connected_players: connected_players["DEF"].sendall(b"MISSED~")
            if "ATK" in connected_players: connected_players["ATK"].sendall(b"SCORED~")
            # נקודה לתוקף כי הוא הצליח לעקוף אותנו
            scores["ATK"] += 1
            check_winner(scores, connected_players)

    # מאזין על ה-loopback כי שני הצדדים רצים על אותו מחשב
    packets = sniff(filter="udp", prn=process_packet, iface=conf.loopback_name)

def handle_client(sock, addr , connected_players, active_rules):
    # שלב ההזדהות - מצפים בדיוק ל-3 בייטים (DEF או ATK)
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
    # מונעים מצב ששני שחקנים יתפסו את אותו תפקיד
    if role in connected_players:
        sock.sendall(b"Role taken~")
        print(f"[SERVER LOG] Role {role} is already taken!")
        sock.close()
        return
    print(f"Client {addr} identified as: {role}")
    connected_players[role] = sock

    # מחכים שגם השחקן השני יתחבר, אחרת אין משחק
    while len(connected_players) < 2:
        time.sleep(0.1)

    # ספירה לאחור 3-2-1 ואז GO
    for i in range(3, 0, -1):
        sock.sendall(f"{i}~".encode())
        time.sleep(1)
    sock.sendall(b'START~')

    # פה הקטע החשוב - TCP יכול לשבור הודעות באמצע, אז אנחנו אוגרים בבאפר
    # ומחפשים את התו ~ שמסמן סוף הודעה. בלי זה היינו מקבלים בלאגן.
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
            # רק המגן יכול לעדכן חוקים, התוקף לא רלוונטי פה
            if role == "DEF":
                try:
                    code, rule = message.strip().split(" ", 1)
                    # P=פורט, W=מילה, I=איי-פי, S*S=גודל מקסימלי
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
    # מילון החוקים המשותף - גם הראדאר וגם ה-handler נוגעים בו
    active_rules = {
        "ports": [],
        "words": [],
        "ips": [],
        "max_size": 2**16 - 1
    }
    connected_players = {}
    # ניקוד משותף. הראשון שמגיע ל-10 מנצח.
    scores = {"DEF": 0, "ATK": 0}

    # הראדאר חייב לרוץ בתהליכון נפרד אחרת sniff() חוסם הכל
    radar_thread = threading.Thread(target=radar_sniffer, args=(active_rules, connected_players, scores))
    radar_thread.start()

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # בלי זה צריך לחכות דקה אחרי כל ריצה עד שהפורט משתחרר
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('0.0.0.0', 8888))
    server_socket.listen(20)
    print("Server is listening on port 8888...")
    while True:
        sock, addr = server_socket.accept()
        # תהליכון לכל לקוח כדי שלא יחסמו אחד את השני
        t = threading.Thread(target=handle_client, args=(sock, addr, connected_players, active_rules))
        t.start()

if __name__ == "__main__":
    main()
