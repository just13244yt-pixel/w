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
        
        # Curses setup
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.use_default_colors()
        
        # Color pairs: (ID, Foreground, Background)
        curses.init_pair(1, curses.COLOR_CYAN, -1)    # Folders
        curses.init_pair(2, curses.COLOR_WHITE, -1)   # Files
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_YELLOW) # Selection (High contrast)
        curses.init_pair(4, curses.COLOR_GREEN, -1)   # Success messages
        curses.init_pair(5, curses.COLOR_RED, -1)     # Error messages
        
        self.run()

    def get_items(self):
        try:
            items = os.listdir(self.current_path)
            folders = sorted([f for f in items if os.path.isdir(os.path.join(self.current_path, f))])
            files = sorted([f for f in items if os.path.isfile(os.path.join(self.current_path, f))])
            self.items = folders + files
        except Exception as e:
            self.items = [f"[Fehler: {str(e)}]"]
        
        # Keep index in bounds
        if not self.items:
            self.selected_index = -1 # Only Back button possible
        elif self.selected_index >= len(self.items):
            self.selected_index = len(self.items) - 1

    def draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Header with Back Button
        back_text = " [ < ZURÜCK ] "
        if self.selected_index == -1:
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(0, 0, back_text)
            self.stdscr.attroff(curses.color_pair(3))
        else:
            self.stdscr.addstr(0, 0, back_text, curses.A_BOLD)
            
        path_display = f"  Pfad: {self.current_path} "
        self.stdscr.addstr(0, len(back_text), path_display[:width-len(back_text)-1], curses.color_pair(1))
        self.stdscr.addstr(1, 0, "═" * (width - 1))

        # List items
        max_display = height - 3
        start_idx = max(0, self.selected_index - max_display // 2) if self.selected_index != -1 else 0
        end_idx = min(len(self.items), start_idx + max_display)
        
        for i, idx in enumerate(range(start_idx, end_idx)):
            item = self.items[idx]
            y = i + 2
            full_path = os.path.join(self.current_path, item)
            is_dir = os.path.isdir(full_path)
            
            if idx == self.selected_index:
                self.stdscr.attron(curses.color_pair(3))
            
            icon = " 📁 " if is_dir else " 📄 "
            color = curses.color_pair(1) if is_dir else curses.color_pair(2)
            
            if idx != self.selected_index:
                self.stdscr.attron(color)
                
            display_line = f"{icon} {item}"
            self.stdscr.addstr(y, 0, display_line[:width-1])
            
            if idx == self.selected_index:
                self.stdscr.attroff(curses.color_pair(3))
            else:
                self.stdscr.attroff(color)

        # Footer info
        if self.clipboard:
            status = f" Zwischenablage: {os.path.basename(self.clipboard)} ({self.clipboard_action}) "
            self.stdscr.addstr(height-1, 0, status[:width-1], curses.A_REVERSE)

        self.stdscr.refresh()

    def run(self):
        while True:
            self.get_items()
            self.draw()
            key = self.stdscr.getch()
            
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
            elif key == ord('q'):
                break

    def handle_item_action(self):
        if not self.items: return
        item = self.items[self.selected_index]
        path = os.path.join(self.current_path, item)
        is_dir = os.path.isdir(path)
        
        options = ["Öffnen", "Schließen", "Umbenennen", "Löschen", "Kopieren", "Verschieben", "USB-Stick"]
        if not is_dir:
            options.insert(1, "Mit Nano bearbeiten")
        if self.clipboard:
            options.append("Einfügen")

        sel = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, f" AKTION: {item} ", curses.A_BOLD | curses.color_pair(3))
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
            elif k == ord('\n'):
                choice = options[sel]
                if choice == "Öffnen":
                    if is_dir:
                        self.current_path = path
                        self.selected_index = 0
                        return
                    else:
                        self.run_terminal_cmd(path)
                        return
                elif choice == "Schließen": return
                elif choice == "Mit Nano bearbeiten":
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
                    return
                elif choice == "Verschieben":
                    self.clipboard = path
                    self.clipboard_action = 'move'
                    return
                elif choice == "Einfügen":
                    self.paste(path if is_dir else self.current_path)
                    return
                elif choice == "USB-Stick":
                    self.usb_copy(path)
                    return
            elif k == 27: break # ESC

    def run_nano(self, path):
        curses.endwin()
        subprocess.run(['nano', path])
        self.stdscr.clear()
        curses.doupdate()

    def run_terminal_cmd(self, path):
        curses.endwin()
        print(f"\nDatei: {os.path.basename(path)}")
        print("Gib den Befehl ein (z.B. python3 1.py) oder drücke Enter für Standard:")
        cmd = input("> ")
        if cmd:
            subprocess.run(cmd, shell=True)
            input("\nFertig. Drücke Enter...")
        self.stdscr.clear()
        curses.doupdate()

    def rename(self, path):
        curses.echo()
        self.stdscr.addstr(15, 2, "Neuer Name: ")
        new_name = self.stdscr.getstr(15, 14).decode('utf-8')
        curses.noecho()
        if new_name:
            try:
                os.rename(path, os.path.join(os.path.dirname(path), new_name))
            except Exception as e:
                self.msg(f"Fehler: {e}", True)

    def delete(self, path):
        self.stdscr.addstr(15, 2, "Wirklich löschen? (j/n): ", curses.color_pair(5))
        if self.stdscr.getch() == ord('j'):
            try:
                if os.path.isdir(path): shutil.rmtree(path)
                else: os.remove(path)
            except Exception as e:
                self.msg(f"Fehler: {e}", True)

    def paste(self, target):
        if not self.clipboard: return
        dest = os.path.join(target, os.path.basename(self.clipboard))
        try:
            if self.clipboard_action == 'copy':
                if os.path.isdir(self.clipboard): shutil.copytree(self.clipboard, dest)
                else: shutil.copy2(self.clipboard, dest)
            else:
                shutil.move(self.clipboard, dest)
                self.clipboard = None
            self.msg("Eingefügt!")
        except Exception as e:
            self.msg(f"Fehler: {e}", True)

    def usb_copy(self, path):
        # Find USB drives via lsblk
        try:
            output = subprocess.check_output(['lsblk', '-nr', '-o', 'MOUNTPOINT']).decode()
            mounts = [line.strip() for line in output.split('\n') if line.strip() and line.startswith(('/media', '/mnt'))]
        except:
            mounts = []
            
        if not mounts:
            self.msg("Kein USB-Stick gefunden!", True)
            return

        sel = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, " WÄHLE USB-STICK: ", curses.color_pair(3))
            for i, m in enumerate(mounts):
                if i == sel: self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(i+2, 2, f" {m} ")
                if i == sel: self.stdscr.attroff(curses.color_pair(3))
            self.stdscr.refresh()
            k = self.stdscr.getch()
            if k == curses.KEY_UP: sel = max(0, sel - 1)
            elif k == curses.KEY_DOWN: sel = min(len(mounts)-1, sel + 1)
            elif k == ord('\n'):
                dest = os.path.join(mounts[sel], os.path.basename(path))
                try:
                    if os.path.isdir(path): shutil.copytree(path, dest)
                    else: shutil.copy2(path, dest)
                    self.msg("Auf USB kopiert!")
                except Exception as e:
                    self.msg(f"Fehler: {e}", True)
                return
            elif k == 27: break

    def msg(self, text, error=False):
        color = curses.color_pair(5) if error else curses.color_pair(4)
        self.stdscr.addstr(18, 2, f" {text} ", color | curses.A_BOLD)
        self.stdscr.refresh()
        time.sleep(1.5)

if __name__ == "__main__":
    curses.wrapper(PiFileManager)
