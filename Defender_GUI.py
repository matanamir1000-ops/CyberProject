__author__ = 'Matan Amir'
import pygame
import sys
import socket
import threading

BG_COLOR = (10, 15, 30)
BOX_COLOR = (20, 30, 50)
TEXT_COLOR = (0, 255, 100)
INACTIVE_COLOR = (100, 100, 100)
BTN_COLOR = (200, 50, 50)
RADAR_BG = (5, 10, 20)

DEFAULT_IP = '127.0.0.1'
SERVER_PORT = 8888


# רץ ברקע ושומע מה השרת זורק עלינו. חובה ת'רד נפרד אחרת ה-GUI נתקע על recv.
# מקבל את הסוקט ואת רשימת האירועים כארגומנטים - בלי משתנים גלובליים.
def listen_to_server(sock, radar_events):
    # באפר שאוגר נתונים חלקיים עד שמגיע ~ שמסמן סוף הודעה
    buffer = ""
    while True:
        try:
            data = sock.recv(1024).decode()
            if not data:
                break
            buffer += data
            # מפצלים על ~ ושולפים כל הודעה שלמה בנפרד. חלק לא שלם נשאר בבאפר להמשך
            while "~" in buffer:
                message, buffer = buffer.split("~", 1)
                if not message:
                    continue
                # מכניסים הודעה חדשה לראש הרשימה, ואם יש יותר מ-5 מעיפים את האחרונה כדי שלא יגלוש לנו מהמסך
                radar_events.insert(0, message)
                if len(radar_events) > 5:
                    radar_events.pop()
        except:
            break


# פונקציית עזר: בונה את ההודעה לפי הפרוטוקול ושולחת. תמיד מוסיף ~ בסוף!
# מקבל את הסוקט כארגומנט במקום להסתמך על משתנה גלובלי.
def send_rule(sock, code, value):
    msg = f"{code} {value}~"
    sock.sendall(msg.encode())


def main():
    if len(sys.argv) > 1:
        server_ip = sys.argv[1]
    else:
        server_ip = DEFAULT_IP

    pygame.init()
    pygame.font.init()

    WIDTH, HEIGHT = 800, 600
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Firewall Command Center - DEFENDER")

    font = pygame.font.SysFont("consolas", 20)
    title_font = pygame.font.SysFont("consolas", 30, bold=True)

    port_box = pygame.Rect(50, 100, 200, 40)
    port_btn = pygame.Rect(260, 100, 100, 40)

    ip_box = pygame.Rect(50, 180, 200, 40)
    ip_btn = pygame.Rect(260, 180, 100, 40)

    word_box = pygame.Rect(50, 260, 200, 40)
    word_btn = pygame.Rect(260, 260, 100, 40)

    radar_box = pygame.Rect(400, 50, 350, 500)

    active_box = None
    port_text = ""
    ip_text = ""
    word_text = ""

    # רשימת האירועים האחרונים מהשרת. הת'רד דוחף הודעות חדשות לראש, ה-GUI מצייר.
    radar_events = []

    # מתחברים לשרת ומזדהים כמגן. ה-~ בסוף זה הדלימיטר שהשרת מצפה לו.
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((server_ip, SERVER_PORT))
        sock.sendall(b"DEF")
        print(f"Connected to server at {server_ip}:{SERVER_PORT} as DEF.")
    except ConnectionRefusedError:
        print("Server is offline! Run Server.py first.")
        pygame.quit()
        return

    # מעבירים לת'רד את הסוקט ואת הרשימה כארגומנטים - אין יותר משתנים גלובליים
    threading.Thread(target=listen_to_server, args=(sock, radar_events), daemon=True).start()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type == pygame.MOUSEBUTTONDOWN:
                # קודם בודקים פוקוס על תיבות הקלט
                if port_box.collidepoint(event.pos):
                    active_box = 'port'
                elif ip_box.collidepoint(event.pos):
                    active_box = 'ip'
                elif word_box.collidepoint(event.pos):
                    active_box = 'word'
                else:
                    active_box = None

                # לחיצה על כפתור BLOCK - שולחים את החוק לשרת ומנקים את התיבה
                if port_btn.collidepoint(event.pos):
                    # רק מספרים בפורט, אחרת השרת יקרוס על int()
                    if port_text and port_text.isdigit():
                        send_rule(sock, "P", port_text)
                        port_text = ""
                elif ip_btn.collidepoint(event.pos):
                    if ip_text:
                        send_rule(sock, "I", ip_text)
                        ip_text = ""
                elif word_btn.collidepoint(event.pos):
                    if word_text:
                        send_rule(sock, "W", word_text)
                        word_text = ""

            if event.type == pygame.KEYDOWN:
                if active_box:
                    if event.key == pygame.K_BACKSPACE:
                        if active_box == 'port': port_text = port_text[:-1]
                        elif active_box == 'ip': ip_text = ip_text[:-1]
                        elif active_box == 'word': word_text = word_text[:-1]
                    else:
                        if active_box == 'port': port_text += event.unicode
                        elif active_box == 'ip': ip_text += event.unicode
                        elif active_box == 'word': word_text += event.unicode

        screen.fill(BG_COLOR)

        title_surf = title_font.render("DEFENSE CONTROL", True, TEXT_COLOR)
        screen.blit(title_surf, (50, 30))
        radar_title = title_font.render("LIVE RADAR", True, TEXT_COLOR)
        screen.blit(radar_title, (400, 10))

        port_label = font.render("Target Port:", True, (200, 220, 255))
        screen.blit(port_label, (port_box.x, port_box.y - 25))
        ip_label = font.render("Banned IP:", True, (200, 220, 255))
        screen.blit(ip_label, (ip_box.x, ip_box.y - 25))
        word_label = font.render("Forbidden Word:", True, (200, 220, 255))
        screen.blit(word_label, (word_box.x, word_box.y - 25))

        # מסגרת ירוקה אם בפוקוס, אפורה אחרת
        p_color = TEXT_COLOR if active_box == 'port' else INACTIVE_COLOR
        i_color = TEXT_COLOR if active_box == 'ip' else INACTIVE_COLOR
        w_color = TEXT_COLOR if active_box == 'word' else INACTIVE_COLOR

        pygame.draw.rect(screen, BOX_COLOR, port_box)
        pygame.draw.rect(screen, p_color, port_box, 2)
        screen.blit(font.render(port_text, True, (255, 255, 255)), (port_box.x + 5, port_box.y + 10))

        pygame.draw.rect(screen, BOX_COLOR, ip_box)
        pygame.draw.rect(screen, i_color, ip_box, 2)
        screen.blit(font.render(ip_text, True, (255, 255, 255)), (ip_box.x + 5, ip_box.y + 10))

        pygame.draw.rect(screen, BOX_COLOR, word_box)
        pygame.draw.rect(screen, w_color, word_box, 2)
        screen.blit(font.render(word_text, True, (255, 255, 255)), (word_box.x + 5, word_box.y + 10))

        pygame.draw.rect(screen, BTN_COLOR, port_btn, border_radius=5)
        pygame.draw.rect(screen, BTN_COLOR, ip_btn, border_radius=5)
        pygame.draw.rect(screen, BTN_COLOR, word_btn, border_radius=5)

        btn_text = font.render("BLOCK!", True, (255, 255, 255))
        screen.blit(btn_text, (port_btn.x + 15, port_btn.y + 10))
        screen.blit(btn_text, (ip_btn.x + 15, ip_btn.y + 10))
        screen.blit(btn_text, (word_btn.x + 15, word_btn.y + 10))

        pygame.draw.rect(screen, RADAR_BG, radar_box)
        pygame.draw.rect(screen, TEXT_COLOR, radar_box, 2)

        # מציירים את כל האירועים מהראש - האחרון נכנס למעלה, הישנים יורדים
        for i, msg in enumerate(radar_events):
            event_surf = font.render(msg, True, TEXT_COLOR)
            screen.blit(event_surf, (radar_box.x + 20, radar_box.y + 30 + i * 30))

        pygame.display.flip()

    sock.close()
    pygame.quit()
    sys.exit()


if __name__ == '__main__':
    main()
