import curses
import os
import shutil
import subprocess
import time

class PiFileManager:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_path = os.path.abspath(os.getcwd())
        self.selected_index = 0
        self.items = []
        self.clipboard = None
        self.clipboard_action = None # 'copy' or 'move'
        self.status_msg = ""
        self.status_is_error = False
        
        # Curses setup
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.use_default_colors()
        
        # Color pairs: (ID, Foreground, Background)
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Folders
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Files
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW) # Selection
        curses.init_pair(4, curses.COLOR_GREEN, -1)   # Success
        curses.init_pair(5, curses.COLOR_RED, -1)     # Error
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_CYAN)   # Buttons/Header
        
        self.run()

    def get_items(self):
        try:
            items = os.listdir(self.current_path)
            folders = sorted([f for f in items if os.path.isdir(os.path.join(self.current_path, f))])
            files = sorted([f for f in items if os.path.isfile(os.path.join(self.current_path, f))])
            self.items = folders + files
        except Exception as e:
            self.items = []
            self.status_msg = f"Fehler: {str(e)}"
            self.status_is_error = True
        
        if not self.items:
            self.selected_index = -1 
        elif self.selected_index >= len(self.items):
            self.selected_index = len(self.items) - 1

    def draw_button(self, y, x, text, active=False):
        if active:
            self.stdscr.attron(curses.color_pair(3))
        else:
            self.stdscr.attron(curses.color_pair(6))
        self.stdscr.addstr(y, x, f" {text} ")
        self.stdscr.attroff(curses.color_pair(3) if active else curses.color_pair(6))

    def draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # --- HEADER ---
        header_bg = curses.color_pair(6)
        self.stdscr.attron(header_bg)
        self.stdscr.addstr(0, 0, " " * (width - 1))
        self.stdscr.addstr(0, 1, "PI FILE MANAGER v2.0", curses.A_BOLD)
        self.stdscr.attroff(header_bg)

        # --- NAVIGATION BAR ---
        nav_y = 1
        back_btn = "[ < ZURÜCK ]"
        usb_btn = "[ USB IMPORT ]"
        home_btn = "[ HOME ]"
        
        if self.selected_index == -1:
            self.draw_button(nav_y, 0, back_btn, True)
        else:
            self.draw_button(nav_y, 0, back_btn, False)
            
        self.draw_button(nav_y, 14, usb_btn, False)
        self.draw_button(nav_y, 30, home_btn, False)
        
        path_display = f" Pfad: {self.current_path} "
        self.stdscr.addstr(nav_y, 40, path_display[:width-41], curses.color_pair(1))
        self.stdscr.addstr(nav_y + 1, 0, "─" * (width - 1))

        # --- FILE LIST ---
        max_display = height - 6
        start_idx = max(0, self.selected_index - max_display // 2) if self.selected_index != -1 else 0
        end_idx = min(len(self.items), start_idx + max_display)
        
        for i, idx in enumerate(range(start_idx, end_idx)):
            item = self.items[idx]
            y = i + 3
            full_path = os.path.join(self.current_path, item)
            is_dir = os.path.isdir(full_path)
            
            if idx == self.selected_index:
                self.stdscr.attron(curses.color_pair(3))
            
            icon = "📁" if is_dir else "📄"
            color = curses.color_pair(1) if is_dir else curses.color_pair(2)
            
            if idx != self.selected_index:
                self.stdscr.attron(color)
                
            display_line = f" {icon} {item}"
            self.stdscr.addstr(y, 0, display_line[:width-1])
            
            if idx == self.selected_index:
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.attroff(color)

        # --- FOOTER / BUTTONS ---
        footer_y = height - 2
        self.stdscr.addstr(footer_y - 1, 0, "─" * (width - 1))
        
        help_text = " [Enter] Aktion | [U] USB-Import | [H] Home | [Q] Beenden "
        self.stdscr.addstr(footer_y, 0, help_text[:width-1], curses.A_DIM)

        if self.clipboard:
            clip_info = f" Clip: {os.path.basename(self.clipboard)} ({self.clipboard_action}) "
            self.stdscr.addstr(footer_y, width - len(clip_info) - 1, clip_info, curses.A_REVERSE)

        # Status Message
        if self.status_msg:
            color = curses.color_pair(5) if self.status_is_error else curses.color_pair(4)
            self.stdscr.addstr(height-1, 0, f" {self.status_msg} "[:width-1], color | curses.A_BOLD)

        self.stdscr.refresh()

    def run(self):
        while True:
            self.get_items()
            self.draw()
            key = self.stdscr.getch()
            
            self.status_msg = "" # Reset status on next key
            
            if key == curses.KEY_UP:
                self.selected_index = max(-1, self.selected_index - 1)
            elif key == curses.KEY_DOWN:
                self.selected_index = min(len(self.items) - 1, self.selected_index + 1)
            elif key == ord('\n'): # Enter
                if self.selected_index == -1:
                    self.current_path = os.path.dirname(self.current_path)
                    self.selected_index = 0
                else:
                    self.handle_item_action()
            elif key in [ord('u'), ord('U')]:
                self.usb_browser()
            elif key in [ord('h'), ord('H')]:
                self.current_path = os.path.expanduser("~")
                self.selected_index = 0
            elif key == ord('q'):
                break

    def handle_item_action(self):
        if not self.items: return
        item = self.items[self.selected_index]
        path = os.path.join(self.current_path, item)
        is_dir = os.path.isdir(path)
        
        options = ["Öffnen", "Umbenennen", "Löschen", "Kopieren", "Verschieben", "Export zu USB", "Abbrechen"]
        if not is_dir:
            options.insert(1, "Edit (Nano)")
        if self.clipboard:
            options.insert(len(options)-1, "Einfügen")

        sel = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, f" AKTION: {item} ", curses.color_pair(6) | curses.A_BOLD)
            for i, opt in enumerate(options):
                if i == sel:
                    self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(i + 2, 2, f" {opt} ")
                if i == sel:
                    self.stdscr.attroff(curses.color_pair(3))
            
            self.stdscr.refresh()
            k = self.stdscr.getch()
            if k == curses.KEY_UP: sel = max(0, sel - 1)
            elif k == curses.KEY_DOWN: sel = min(len(options)-1, sel + 1)
            elif k in [ord('\n'), curses.KEY_RIGHT]:
                choice = options[sel]
                if choice == "Öffnen":
                    if is_dir:
                        self.current_path = path
                        self.selected_index = 0
                    else:
                        self.run_terminal_cmd(path)
                    return
                elif choice == "Abbrechen": return
                elif choice == "Edit (Nano)":
                    self.run_nano(path)
                    return
                elif choice == "Umbenennen":
                    self.rename(path)
                    return
                elif choice == "Löschen":
                    self.delete(path)
                    return
                elif choice == "Kopieren":
                    self.clipboard = path
                    self.clipboard_action = 'copy'
                    self.msg("In Zwischenablage kopiert")
                    return
                elif choice == "Verschieben":
                    self.clipboard = path
                    self.clipboard_action = 'move'
                    self.msg("Zum Verschieben markiert")
                    return
                elif choice == "Einfügen":
                    self.paste(path if is_dir else self.current_path)
                    return
                elif choice == "Export zu USB":
                    self.usb_transfer(path, direction="to_usb")
                    return
            elif k in [27, curses.KEY_LEFT]: break

    def usb_browser(self):
        """Browse USB and import to current path."""
        self.usb_transfer(self.current_path, direction="from_usb")

    def usb_transfer(self, local_path, direction="from_usb"):
        """Handles both directions: from_usb (import) and to_usb (export)."""
        try:
            output = subprocess.check_output(['lsblk', '-nr', '-o', 'NAME,SIZE,MOUNTPOINT,TRAN']).decode()
            devices = []
            for line in output.split('\n'):
                parts = line.split()
                if len(parts) >= 2 and 'usb' in line.lower():
                    name = parts[0]
                    size = parts[1]
                    mount = parts[2] if len(parts) > 2 and parts[2].startswith('/') else None
                    devices.append({'dev': f"/dev/{name}", 'size': size, 'mount': mount})
        except:
            devices = []
            
        if not devices:
            self.msg("Kein USB-Gerät gefunden!", True)
            return

        sel = 0
        while True:
            self.stdscr.clear()
            title = " WÄHLE USB-QUELLE (IMPORT): " if direction == "from_usb" else " WÄHLE USB-ZIEL (EXPORT): "
            self.stdscr.addstr(0, 0, title, curses.color_pair(6) | curses.A_BOLD)
            for i, d in enumerate(devices):
                status = f"[{d['mount']}]" if d['mount'] else "[Nicht eingebunden]"
                if i == sel: self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(i+2, 2, f" {d['dev']} ({d['size']}) {status} ")
                if i == sel: self.stdscr.attroff(curses.color_pair(3))
            self.stdscr.refresh()
            k = self.stdscr.getch()
            if k == curses.KEY_UP: sel = max(0, sel - 1)
            elif k == curses.KEY_DOWN: sel = min(len(devices)-1, sel + 1)
            elif k == ord('\n'):
                target_dev = devices[sel]
                mount_path = target_dev['mount']
                
                if not mount_path:
                    mount_path = f"/mnt/usb_{os.path.basename(target_dev['dev'])}"
                    try:
                        subprocess.run(['sudo', 'mkdir', '-p', mount_path])
                        res = subprocess.run(['sudo', 'mount', target_dev['dev'], mount_path], capture_output=True)
                        if res.returncode != 0:
                            res = subprocess.run(['sudo', 'mount', f"{target_dev['dev']}1", mount_path], capture_output=True)
                            if res.returncode != 0: raise Exception("Mount fehlgeschlagen")
                    except Exception as e:
                        self.msg(f"Mount-Fehler: {e}", True)
                        return

                if direction == "from_usb":
                    self.browse_and_import(mount_path, local_path)
                else:
                    self.perform_copy(local_path, mount_path)
                return
            elif k == 27: break

    def browse_and_import(self, usb_path, dest_path):
        """Browser specifically for selecting files ON the USB stick to import."""
        usb_current = usb_path
        usb_sel = 0
        
        while True:
            try:
                items = os.listdir(usb_current)
                folders = sorted([f for f in items if os.path.isdir(os.path.join(usb_current, f))])
                files = sorted([f for f in items if os.path.isfile(os.path.join(usb_current, f))])
                usb_items = folders + files
            except: usb_items = []

            self.stdscr.clear()
            self.stdscr.addstr(0, 0, f" IMPORT VON USB: {usb_current} ", curses.color_pair(6) | curses.A_BOLD)
            self.stdscr.addstr(1, 0, f" Ziel: {dest_path}", curses.color_pair(4))
            
            # Back option
            if usb_sel == -1: self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(3, 2, " [ < ZURÜCK / ORDNER HOCH ] ")
            self.stdscr.attroff(curses.color_pair(3))

            for i, item in enumerate(usb_items):
                if i == usb_sel: self.stdscr.attron(curses.color_pair(3))
                icon = "📁" if os.path.isdir(os.path.join(usb_current, item)) else "📄"
                self.stdscr.addstr(i + 4, 2, f" {icon} {item} ")
                if i == usb_sel: self.stdscr.attroff(curses.color_pair(3))
            
            self.stdscr.addstr(self.stdscr.getmaxyx()[0]-1, 0, " [Enter] Importieren/Öffnen | [ESC] Abbrechen ", curses.A_DIM)
            self.stdscr.refresh()
            
            k = self.stdscr.getch()
            if k == curses.KEY_UP: usb_sel = max(-1, usb_sel - 1)
            elif k == curses.KEY_DOWN: usb_sel = min(len(usb_items)-1, usb_sel + 1)
            elif k == ord('\n'):
                if usb_sel == -1:
                    if usb_current == usb_path: break # Already at USB root
                    usb_current = os.path.dirname(usb_current)
                    usb_sel = 0
                else:
                    target = os.path.join(usb_current, usb_items[usb_sel])
                    if os.path.isdir(target):
                        usb_current = target
                        usb_sel = 0
                    else:
                        self.perform_copy(target, dest_path)
                        break
            elif k == 27: break

    def perform_copy(self, src, dest_dir):
        dest = os.path.join(dest_dir, os.path.basename(src))
        try:
            self.msg("Kopiere... bitte warten.")
            if os.path.isdir(src): shutil.copytree(src, dest)
            else: shutil.copy2(src, dest)
            self.msg("Erfolgreich!")
        except Exception as e:
            self.msg(f"Fehler: {e}", True)

    def run_nano(self, path):
        curses.endwin()
        subprocess.run(['nano', path])
        self.stdscr.clear()
        curses.doupdate()

    def run_terminal_cmd(self, path):
        curses.endwin()
        print(f"\nDatei: {os.path.basename(path)}")
        print("Befehl (z.B. python3) oder Enter für Shell:")
        cmd = input("> ")
        if cmd:
            subprocess.run(f"{cmd} {path}", shell=True)
            input("\nFertig. Enter...")
        self.stdscr.clear()
        curses.doupdate()

    def rename(self, path):
        curses.echo()
        self.stdscr.addstr(15, 2, "Neuer Name: ", curses.color_pair(6))
        new_name = self.stdscr.getstr(15, 14).decode('utf-8')
        curses.noecho()
        if new_name:
            try:
                os.rename(path, os.path.join(os.path.dirname(path), new_name))
                self.msg("Umbenannt")
            except Exception as e: self.msg(f"Fehler: {e}", True)

    def delete(self, path):
        self.stdscr.addstr(15, 2, "Löschen? (j/n): ", curses.color_pair(5) | curses.A_BOLD)
        if self.stdscr.getch() == ord('j'):
            try:
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
                self.msg("Gelöscht")
            except Exception as e: self.msg(f"Fehler: {e}", True)

    def paste(self, target):
        if not self.clipboard: return
        self.perform_copy(self.clipboard, target)
        if self.clipboard_action == 'move':
            try:
                if os.path.isdir(self.clipboard): shutil.rmtree(self.clipboard)
                else: os.remove(self.clipboard)
                self.clipboard = None
            except: pass

    def msg(self, text, error=False):
        self.status_msg = text
        self.status_is_error = error
        self.draw()
        time.sleep(1.2)

if __name__ == "__main__":
    curses.wrapper(PiFileManager)
