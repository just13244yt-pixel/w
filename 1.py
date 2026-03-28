import curses
import os
import shutil
import sys
import time
import json
import platform
from datetime import datetime, timedelta
import subprocess

# --- SYSTEM-CHECK ---
IS_WINDOWS = platform.system() == "Windows"
IS_LINUX = platform.system() == "Linux"

# --- HELPER FOR SYSTEM INFO (NO PSUTIL) ---
def get_cpu_usage():
    if not IS_LINUX: return 0
    try:
        with open('/proc/stat', 'r') as f:
            line = f.readline()
        parts = line.split()
        idle = int(parts[4])
        total = sum(int(p) for p in parts[1:])
        return (idle, total)
    except: return (0, 0)

_last_cpu = (0, 0)
def calculate_cpu():
    global _last_cpu
    idle, total = get_cpu_usage()
    if total == _last_cpu[1]: return 0
    diff_idle = idle - _last_cpu[0]
    diff_total = total - _last_cpu[1]
    _last_cpu = (idle, total)
    return round(100 * (1 - diff_idle / diff_total), 1)

def get_ram_usage():
    if not IS_LINUX: return 0
    try:
        with open('/proc/meminfo', 'r') as f:
            lines = f.readlines()
        mem_total = int(lines[0].split()[1])
        mem_free = int(lines[1].split()[1])
        return round(100 * (1 - mem_free / mem_total), 1)
    except: return 0

def get_disk_usage():
    try:
        total, used, free = shutil.disk_usage("/")
        return round(100 * (used / total), 1)
    except: return 0

# --- BOOT ANIMATION ---
def boot_animation(stdscr):
    try:
        h, w = stdscr.getmaxyx()
        boot_msg = "BOOTING JUST-OS ULTIMATE..."
        x = max(0, (w - len(boot_msg))//2)
        y = max(0, h//2)
        stdscr.addstr(y, x, boot_msg, curses.color_pair(1) | curses.A_BOLD)
        stdscr.refresh()
        time.sleep(1.5)
    except: pass

# --- CONFIG & PERSISTENCE ---
DATA_FILE = "just_os_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
                if "cfg" not in data: data["cfg"] = {}
                if "padding" not in data["cfg"]: data["cfg"]["padding"] = 6
                if "sidebar_width" not in data["cfg"]: data["cfg"]["sidebar_width"] = 30
                if "notes" not in data: data["notes"] = []
                if "games_v3" not in data: data["games_v3"] = []
                if "hack_tools_v3" not in data: data["hack_tools_v3"] = []
                if "username" not in data["cfg"]: data["cfg"]["username"] = "User"
                if "theme" not in data["cfg"]: data["cfg"]["theme"] = "default"
                keys = ["border", "text", "logo", "bg", "sel_bg", "sel_txt", "taskbar_bg", "taskbar_txt"]
                defaults = [curses.COLOR_BLUE, curses.COLOR_CYAN, curses.COLOR_BLUE,
                            curses.COLOR_BLACK, curses.COLOR_CYAN, curses.COLOR_BLACK,
                            curses.COLOR_BLACK, curses.COLOR_WHITE]
                for k, d in zip(keys, defaults):
                    if k not in data["cfg"]: data["cfg"][k] = d
                return data
        except: pass
    return {
        "notes": [], 
        "games_v3": [],
        "hack_tools_v3": [],
        "cfg": {
            "border": curses.COLOR_BLUE, "text": curses.COLOR_CYAN, "logo": curses.COLOR_BLUE,
            "bg": curses.COLOR_BLACK, "sel_bg": curses.COLOR_CYAN, "sel_txt": curses.COLOR_BLACK,
            "taskbar_bg": curses.COLOR_BLACK, "taskbar_txt": curses.COLOR_WHITE,
            "padding": 6, "sidebar_width": 30, "username": "User", "theme": "default"
        }
    }

user_data = load_data()
cfg = user_data["cfg"]

def save_data():
    user_data["cfg"] = cfg
    with open(DATA_FILE, 'w') as f:
        json.dump(user_data, f, indent=4)

# --- THEMES ---
themes = {
    "default": {"border": curses.COLOR_BLUE, "text": curses.COLOR_CYAN, "logo": curses.COLOR_BLUE, "bg": curses.COLOR_BLACK, "sel_bg": curses.COLOR_CYAN, "sel_txt": curses.COLOR_BLACK, "taskbar_bg": curses.COLOR_BLACK, "taskbar_txt": curses.COLOR_WHITE},
    "dark_green": {"border": curses.COLOR_GREEN, "text": curses.COLOR_WHITE, "logo": curses.COLOR_GREEN, "bg": curses.COLOR_BLACK, "sel_bg": curses.COLOR_GREEN, "sel_txt": curses.COLOR_BLACK, "taskbar_bg": curses.COLOR_BLACK, "taskbar_txt": curses.COLOR_GREEN},
    "light_blue": {"border": curses.COLOR_CYAN, "text": curses.COLOR_BLACK, "logo": curses.COLOR_BLUE, "bg": curses.COLOR_WHITE, "sel_bg": curses.COLOR_BLUE, "sel_txt": curses.COLOR_WHITE, "taskbar_bg": curses.COLOR_BLUE, "taskbar_txt": curses.COLOR_WHITE}
}

def apply_theme(theme_name):
    if theme_name in themes:
        for key, value in themes[theme_name].items(): cfg[key] = value
    apply_colors()

# --- UI LOGIK & FARBEN ---
def apply_colors():
    curses.start_color()
    curses.init_pair(1, cfg["logo"], cfg["bg"])
    curses.init_pair(2, cfg["border"], cfg["bg"])
    curses.init_pair(3, cfg["text"], cfg["bg"])
    curses.init_pair(4, curses.COLOR_GREEN, cfg["bg"])
    curses.init_pair(5, curses.COLOR_RED, cfg["bg"])
    curses.init_pair(6, curses.COLOR_YELLOW, cfg["bg"])
    curses.init_pair(7, cfg["sel_txt"], cfg["sel_bg"])
    curses.init_pair(8, cfg["taskbar_txt"], cfg["taskbar_bg"])

def draw_frame(stdscr, title, sidebar_width=0, taskbar_height=0):
    try:
        h, w = stdscr.getmaxyx()
        if h < 3 or w < 10: return
        stdscr.attron(curses.color_pair(2) | curses.A_BOLD)
        stdscr.border(0, 0, 0, 0, 0, 0, 0, 0)
        if sidebar_width > 0 and sidebar_width < w - 5:
            stdscr.vline(0, sidebar_width, curses.ACS_VLINE, h - taskbar_height)
            stdscr.addch(0, sidebar_width, curses.ACS_TTEE)
            if h - taskbar_height - 1 > 0: stdscr.addch(h - taskbar_height - 1, sidebar_width, curses.ACS_BTEE)
        if taskbar_height > 0 and h - taskbar_height - 1 > 0:
            stdscr.hline(h - taskbar_height - 1, 0, curses.ACS_HLINE, w)
            stdscr.addch(h - taskbar_height - 1, 0, curses.ACS_LTEE)
            stdscr.addch(h - taskbar_height - 1, w - 1, curses.ACS_RTEE)
            if sidebar_width > 0: stdscr.addch(h - taskbar_height - 1, sidebar_width, curses.ACS_PLUS)
        title_str = f" [ {title.upper()} ] "
        x_pos = max(sidebar_width + 1, (w + sidebar_width)//2 - len(title_str)//2)
        if x_pos < w - len(title_str): stdscr.addstr(0, x_pos, title_str)
        stdscr.attroff(curses.color_pair(2) | curses.A_BOLD)
    except: pass

def get_network_info():
    info = {"ssid": "N/A", "ip": "N/A"}
    if IS_LINUX:
        try:
            res = subprocess.run("hostname -I", shell=True, capture_output=True, text=True)
            info["ip"] = res.stdout.split()[0] if res.stdout.split() else "N/A"
            res = subprocess.run("iwgetid -r", shell=True, capture_output=True, text=True)
            info["ssid"] = res.stdout.strip() if res.stdout.strip() else "N/A"
        except: pass
    return info

def draw_sidebar(stdscr, width, taskbar_height):
    try:
        h, w = stdscr.getmaxyx()
        if width <= 0 or width >= w: return
        stdscr.addstr(2, 2, "SYSTEM INFO", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(4, 2, f"USER: {cfg['username']}", curses.color_pair(3))
        stdscr.addstr(5, 2, f"OS: JUST-OS V21", curses.color_pair(3))
        cpu = calculate_cpu()
        ram = get_ram_usage()
        stdscr.addstr(7, 2, f"CPU: {cpu}%", curses.color_pair(4 if cpu < 80 else 5))
        stdscr.addstr(8, 2, f"RAM: {ram}%", curses.color_pair(4 if ram < 80 else 5))
        net = get_network_info()
        stdscr.addstr(10, 2, "NETWORK:", curses.color_pair(1) | curses.A_BOLD)
        stdscr.addstr(11, 2, f"SSID: {net['ssid'][:width-8]}", curses.color_pair(3))
        stdscr.addstr(12, 2, f"IP: {net['ip']}", curses.color_pair(3))
        now = datetime.now().strftime("%H:%M:%S")
        stdscr.addstr(h - taskbar_height - 3, 2, f"TIME: {now}", curses.color_pair(6))
    except: pass

def draw_taskbar(stdscr, height, sidebar_width):
    try:
        h, w = stdscr.getmaxyx()
        if height <= 0: return
        stdscr.attron(curses.color_pair(8))
        for i in range(height): stdscr.addstr(h - 1 - i, 0, " " * w)
        stdscr.addstr(h - 1, 2, " [W/S] Navigieren | [ENTER] Auswählen | [Q] Zurück ")
        stdscr.attroff(curses.color_pair(8))
    except: pass

# --- UNIVERSAL LIST MENU (FOR GAMES & TOOLS) ---
def universal_list_menu(stdscr, title, data_key):
    sel = 0
    while True:
        try:
            sidebar_width = cfg.get("sidebar_width", 30)
            taskbar_height = 1
            stdscr.clear()
            draw_frame(stdscr, title, sidebar_width, taskbar_height)
            draw_sidebar(stdscr, sidebar_width, taskbar_height)
            draw_taskbar(stdscr, taskbar_height, sidebar_width)
            h, w = stdscr.getmaxyx()
            pad = cfg["padding"]
            content_start_x = sidebar_width + pad
            items = user_data.get(data_key, [])
            stdscr.addstr(2, content_start_x, f"{title}:", curses.color_pair(1) | curses.A_BOLD)
            for i, item in enumerate(items):
                attr = curses.color_pair(7) if i == sel else curses.color_pair(3)
                if 4 + i < h - 8: stdscr.addstr(4 + i, content_start_x, f" {i+1}. {item['name']} ", attr)
            menu_y = h - 7
            menu_items = ["[A] HINZUFÜGEN", "[D] LÖSCHEN", "[R] UMBENENNEN", "[Q] ZURÜCK"]
            for i, m_item in enumerate(menu_items):
                attr = curses.color_pair(7) if (len(items) + i) == sel else curses.color_pair(6)
                stdscr.addstr(menu_y + i, content_start_x, f" {m_item} ", attr)
            k = stdscr.getch()
            total_items = len(items) + len(menu_items)
            if k in [ord('w'), curses.KEY_UP] and sel > 0: sel -= 1
            elif k in [ord('s'), curses.KEY_DOWN] and sel < total_items - 1: sel += 1
            elif k == ord('a'):
                curses.echo(); stdscr.addstr(h-3, content_start_x, "Name: "); name = stdscr.getstr().decode().strip()
                stdscr.addstr(h-2, content_start_x, "Befehl: "); cmd = stdscr.getstr().decode().strip()
                if name and cmd: user_data[data_key].append({"name": name, "cmd": cmd}); save_data()
                curses.noecho()
            elif k == ord('d') and sel < len(items): user_data[data_key].pop(sel); save_data(); sel = max(0, sel - 1)
            elif k == ord('r') and sel < len(items):
                curses.echo(); stdscr.addstr(h-3, content_start_x, "Neuer Name: "); new_name = stdscr.getstr().decode().strip()
                if new_name: user_data[data_key][sel]['name'] = new_name; save_data()
                curses.noecho()
            elif k in [10, 13]:
                if sel < len(items):
                    cmd = items[sel]["cmd"]
                    curses.endwin(); print(f"\nStarte: {items[sel]['name']}..."); os.system(cmd)
                    print("\nBeendet. Beliebige Taste..."); input(); stdscr.clear(); apply_colors(); curses.curs_set(0)
                elif sel == len(items) + 3: break
            elif k == ord('q'): break
        except: break

# --- USB TRANSFER ---
def usb_transfer_menu(stdscr):
    sel = 0
    while True:
        try:
            sidebar_width = cfg.get("sidebar_width", 30)
            taskbar_height = 1
            stdscr.clear()
            draw_frame(stdscr, "USB-TRANSFER", sidebar_width, taskbar_height)
            draw_sidebar(stdscr, sidebar_width, taskbar_height)
            draw_taskbar(stdscr, taskbar_height, sidebar_width)
            h, w = stdscr.getmaxyx()
            content_start_x = sidebar_width + cfg["padding"]
            usb_path = "/media/pi" if os.path.exists("/media/pi") else "/mnt"
            stdscr.addstr(2, content_start_x, f"USB-PFAD: {usb_path}", curses.color_pair(1))
            try: usb_items = os.listdir(usb_path)
            except: usb_items = []
            if not usb_items: stdscr.addstr(4, content_start_x, "Kein USB-Stick gefunden!", curses.color_pair(5))
            else:
                for i, item in enumerate(usb_items[:h-10]):
                    attr = curses.color_pair(7) if i == sel else curses.color_pair(3)
                    stdscr.addstr(4 + i, content_start_x, f" > {item}", attr)
            stdscr.addstr(h-2, content_start_x, "[ENTER] Kopieren nach /home/pi/ | [Q] Zurück", curses.color_pair(6))
            k = stdscr.getch()
            if k in [ord('w'), curses.KEY_UP] and sel > 0: sel -= 1
            elif k in [ord('s'), curses.KEY_DOWN] and sel < len(usb_items)-1: sel += 1
            elif k in [10, 13] and usb_items:
                src = os.path.join(usb_path, usb_items[sel])
                dst = "/home/pi/"
                try:
                    if os.path.isdir(src): shutil.copytree(src, os.path.join(dst, usb_items[sel]))
                    else: shutil.copy2(src, dst)
                    stdscr.addstr(h-3, content_start_x, "ERFOLGREICH KOPIERT!", curses.color_pair(4)); stdscr.refresh(); time.sleep(1)
                except Exception as e:
                    stdscr.addstr(h-3, content_start_x, f"FEHLER: {str(e)[:20]}", curses.color_pair(5)); stdscr.refresh(); time.sleep(1)
            elif k == ord('q'): break
        except: break

# --- TERMINAL ---
def terminal_menu(stdscr):
    curses.echo(); curses.curs_set(1)
    while True:
        try:
            sidebar_width = cfg.get("sidebar_width", 30)
            taskbar_height = 1
            stdscr.clear()
            draw_frame(stdscr, "TERMINAL", sidebar_width, taskbar_height)
            draw_sidebar(stdscr, sidebar_width, taskbar_height)
            draw_taskbar(stdscr, taskbar_height, sidebar_width)
            h, w = stdscr.getmaxyx()
            content_start_x = sidebar_width + cfg["padding"]
            stdscr.addstr(2, content_start_x, "JUST-OS TERMINAL ('exit' zum Neustart, 'back' für Menü)", curses.color_pair(6))
            stdscr.addstr(4, content_start_x, f"{os.getcwd()} > ", curses.color_pair(4))
            cmd = stdscr.getstr().decode().strip()
            if cmd.lower() == "back": break
            if cmd.lower() == "exit":
                curses.endwin(); print("\n[!] Neustart von JUST-OS..."); os.execv(sys.executable, [sys.executable] + sys.argv)
            curses.endwin(); print(f"\n--- Output: {cmd} ---")
            if cmd.startswith("cd "):
                try: os.chdir(cmd[3:])
                except: print("Pfad nicht gefunden.")
            else: os.system(cmd)
            print("\nBeliebige Taste..."); input(); stdscr.clear(); apply_colors(); curses.curs_set(1)
        except: break
    curses.noecho(); curses.curs_set(0)

# --- SETTINGS ---
def settings_menu(stdscr):
    sel = 0
    colors = [curses.COLOR_BLUE, curses.COLOR_CYAN, curses.COLOR_GREEN, curses.COLOR_RED, curses.COLOR_YELLOW, curses.COLOR_WHITE]
    names = ["BLAU", "CYAN", "GRÜN", "ROT", "GELB", "WEISS"]
    while True:
        try:
            sidebar_width = cfg.get("sidebar_width", 30)
            taskbar_height = 1
            stdscr.clear()
            draw_frame(stdscr, "EINSTELLUNGEN", sidebar_width, taskbar_height)
            draw_sidebar(stdscr, sidebar_width, taskbar_height)
            draw_taskbar(stdscr, taskbar_height, sidebar_width)
            h, w = stdscr.getmaxyx()
            content_start_x = sidebar_width + cfg["padding"]
            opts = [f"RAHMEN-FARBE: {names[colors.index(cfg['border'])]}", f"TEXT-FARBE  : {names[colors.index(cfg['text'])]}", f"RAND-ABSTAND: {cfg['padding']}px", f"SIDEBAR-BREITE: {cfg['sidebar_width']}px", f"BENUTZERNAME: {cfg['username']}", "KONFIGURATION SPEICHERN", "ZURÜCK"]
            for i, o in enumerate(opts):
                attr = curses.color_pair(7) if i == sel else curses.color_pair(3)
                stdscr.addstr(4 + i * 2, content_start_x, f" {o} ", attr)
            k = stdscr.getch()
            if k in [ord('w'), curses.KEY_UP] and sel > 0: sel -= 1
            elif k in [ord('s'), curses.KEY_DOWN] and sel < len(opts)-1: sel += 1
            elif k in [10, 13]:
                if sel == 0: cfg['border'] = colors[(colors.index(cfg['border'])+1)%len(colors)]
                elif sel == 1: cfg['text'] = colors[(colors.index(cfg['text'])+1)%len(colors)]
                elif sel == 2: cfg['padding'] = 2 if cfg['padding'] >= 20 else cfg['padding']+2
                elif sel == 3: cfg['sidebar_width'] = 10 if cfg['sidebar_width'] >= 50 else cfg['sidebar_width']+5
                elif sel == 4:
                    curses.echo(); stdscr.addstr(h-3, content_start_x, "Neuer Name: "); new_name = stdscr.getstr().decode()
                    if new_name: cfg['username'] = new_name; curses.noecho()
                elif sel == 5: save_data()
                elif sel == 6: break
                apply_colors()
            elif k == ord('q'): break
        except: break

# --- MAIN ---
def main(stdscr):
    apply_colors(); boot_animation(stdscr)
    menu = [
        {"n": "EXPLORER", "f": lambda s: os.system("ls -la")}, # Placeholder for full explorer
        {"n": "TERMINAL", "f": terminal_menu},
        {"n": "HACK-TOOLS", "f": lambda s: universal_list_menu(s, "HACK-TOOLS", "hack_tools_v3")},
        {"n": "GAMES", "f": lambda s: universal_list_menu(s, "GAMES", "games_v3")},
        {"n": "USB-STICK", "f": usb_transfer_menu},
        {"n": "DASHBOARD", "f": lambda s: None},
        {"n": "SETTINGS", "f": settings_menu},
        {"n": "EXIT", "f": "exit"}
    ]
    sel = 0
    while True:
        try:
            sidebar_width = cfg.get("sidebar_width", 30)
            taskbar_height = 1
            stdscr.clear()
            draw_frame(stdscr, "JUST-OS ULTIMATE", sidebar_width, taskbar_height)
            draw_sidebar(stdscr, sidebar_width, taskbar_height)
            draw_taskbar(stdscr, taskbar_height, sidebar_width)
            h, w = stdscr.getmaxyx()
            content_start_x = sidebar_width + cfg["padding"]
            logo = ["  ██╗██╗   ██╗███████╗████████╗", "  ██║██║   ██║██╔════╝╚══██╔══╝", "  ██║██║   ██║███████╗   ██║   ", "  ██║██║   ██║╚════██║   ██║   ", "  ██║╚██████╔╝███████║   ██║   ", "  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   "]
            for i, line in enumerate(logo):
                if 2 + i < h - 10: stdscr.addstr(2 + i, content_start_x + 5, line, curses.color_pair(1))
            for i, item in enumerate(menu):
                attr = curses.color_pair(7) if i == sel else curses.color_pair(3)
                if 10 + i*2 < h - 2: stdscr.addstr(10 + i*2, content_start_x + 5, f" [ {item['n']:<12} ] ", attr)
            k = stdscr.getch()
            if k in [ord('w'), curses.KEY_UP] and sel > 0: sel -= 1
            elif k in [ord('s'), curses.KEY_DOWN] and sel < len(menu)-1: sel += 1
            elif k in [10, 13]:
                if menu[sel]["f"] == "exit": break
                menu[sel]["f"](stdscr)
            elif k == ord('q'): break
        except: continue

if __name__ == "__main__":
    try: curses.wrapper(main)
    except KeyboardInterrupt: pass
    finally: save_data(); print("\n[!] JUST-OS beendet.")
