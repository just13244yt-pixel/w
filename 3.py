import curses
import os
import shutil
import subprocess

class FileManager:
    def __init__(self, stdscr):
        self.stdscr = stdscr
        self.current_path = os.getcwd()
        self.selected_index = 0
        self.items = []
        self.clipboard = None
        self.clipboard_action = None # 'copy' or 'move'
        
        # Curses setup
        curses.curs_set(0)
        self.stdscr.keypad(True)
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK) # Folders
        curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLACK) # Files
        curses.init_pair(3, curses.COLOR_BLACK, curses.COLOR_WHITE) # Selection
        
        self.run()

    def get_items(self):
        try:
            items = os.listdir(self.current_path)
            # Sort: Folders first, then files
            folders = sorted([f for f in items if os.path.isdir(os.path.join(self.current_path, f))])
            files = sorted([f for f in items if os.path.isfile(os.path.join(self.current_path, f))])
            
            self.items = folders + files
            if self.selected_index >= len(self.items):
                self.selected_index = max(-1, len(self.items) - 1)
        except PermissionError:
            self.items = ["[Zugriff verweigert]"]
            self.selected_index = -1

    def draw(self):
        self.stdscr.clear()
        height, width = self.stdscr.getmaxyx()
        
        # Header
        back_btn = "[ < ZURÜCK ]"
        header = f" {back_btn}  Pfad: {self.current_path} "
        self.stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(0, 0, header[:width-1])
        self.stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
        self.stdscr.addstr(1, 0, "-" * (width - 1))

        # List items
        max_display = height - 3
        start_idx = max(0, self.selected_index - max_display // 2)
        end_idx = min(len(self.items), start_idx + max_display)
        
        # Highlight back button if selected
        if self.selected_index == -1:
            self.stdscr.attron(curses.color_pair(3))
            self.stdscr.addstr(0, 1, "[ < ZURÜCK ]")
            self.stdscr.attroff(curses.color_pair(3))

        for i, idx in enumerate(range(start_idx, end_idx)):
            item = self.items[idx]
            y = i + 2
            
            if idx == self.selected_index:
                self.stdscr.attron(curses.color_pair(3))
            
            # Icon logic
            full_path = os.path.join(self.current_path, item)
            if os.path.isdir(full_path):
                icon = " 📁 " # Folder icon
                self.stdscr.attron(curses.color_pair(1))
            else:
                icon = " 📄 " # File icon (square-like)
                self.stdscr.attron(curses.color_pair(2))
                
            display_text = f"{icon}{item}"
            self.stdscr.addstr(y, 0, display_text[:width-1])
            
            if idx == self.selected_index:
                self.stdscr.attroff(curses.color_pair(3))
            self.stdscr.attroff(curses.color_pair(1))
            self.stdscr.attroff(curses.color_pair(2))

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
                if self.selected_index == -1: # Back button selected
                    self.current_path = os.path.dirname(self.current_path)
                    self.selected_index = 0
                else:
                    self.handle_enter()
            elif key == ord('q'):
                break

    def handle_enter(self):
        if not self.items: return
        selected_item = self.items[self.selected_index]
        full_path = os.path.join(self.current_path, selected_item)
        
        if os.path.isdir(full_path):
            self.show_menu(full_path, is_dir=True)
        else:
            self.show_menu(full_path, is_dir=False)

    def show_menu(self, path, is_dir):
        options = ["Öffnen", "Schließen", "Umbenennen", "Löschen", "Kopieren", "Verschieben", "USB-Stick"]
        if not is_dir:
            options.insert(1, "Mit Nano bearbeiten")
        
        if self.clipboard:
            options.append("Einfügen")

        selected_option = 0
        while True:
            self.stdscr.clear()
            height, width = self.stdscr.getmaxyx()
            self.stdscr.addstr(0, 0, f" Menü für: {os.path.basename(path)} ", curses.A_BOLD)
            
            for i, option in enumerate(options):
                if i == selected_option:
                    self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(i + 2, 2, f" {option} ")
                if i == selected_option:
                    self.stdscr.attroff(curses.color_pair(3))
            
            self.stdscr.refresh()
            key = self.stdscr.getch()
            
            if key == curses.KEY_UP:
                selected_option = max(0, selected_option - 1)
            elif key == curses.KEY_DOWN:
                selected_option = min(len(options) - 1, selected_option + 1)
            elif key == ord('\n'):
                choice = options[selected_option]
                if choice == "Öffnen":
                    if is_dir:
                        self.current_path = path
                        self.selected_index = 0
                        return
                    else:
                        self.open_terminal_command(path)
                        return
                elif choice == "Schließen":
                    return
                elif choice == "Mit Nano bearbeiten":
                    self.edit_with_nano(path)
                    return
                elif choice == "Umbenennen":
                    self.rename_item(path)
                    return
                elif choice == "Löschen":
                    self.delete_item(path)
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
                    self.paste_item(path if is_dir else os.path.dirname(path))
                    return
                elif choice == "USB-Stick":
                    self.copy_to_usb(path)
                    return
            elif key == 27: # ESC
                return

    def edit_with_nano(self, path):
        curses.endwin()
        subprocess.run(['nano', path])
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)

    def open_terminal_command(self, path):
        curses.endwin()
        print(f"Befehl für {os.path.basename(path)} eingeben (z.B. python3 {os.path.basename(path)}):")
        cmd = input("> ")
        if cmd:
            subprocess.run(cmd, shell=True)
            input("\nDrücke Enter zum Fortfahren...")
        self.stdscr = curses.initscr()
        curses.noecho()
        curses.cbreak()
        self.stdscr.keypad(True)

    def rename_item(self, path):
        curses.echo()
        self.stdscr.addstr(15, 2, "Neuer Name: ")
        new_name = self.stdscr.getstr(15, 14).decode('utf-8')
        curses.noecho()
        if new_name:
            new_path = os.path.join(os.path.dirname(path), new_name)
            os.rename(path, new_path)

    def delete_item(self, path):
        self.stdscr.addstr(15, 2, f"Wirklich löschen? (y/n): ")
        key = self.stdscr.getch()
        if key == ord('y'):
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    def paste_item(self, target_dir):
        if not self.clipboard: return
        
        dest = os.path.join(target_dir, os.path.basename(self.clipboard))
        if self.clipboard_action == 'copy':
            if os.path.isdir(self.clipboard):
                shutil.copytree(self.clipboard, dest)
            else:
                shutil.copy2(self.clipboard, dest)
        elif self.clipboard_action == 'move':
            shutil.move(self.clipboard, dest)
            self.clipboard = None
            self.clipboard_action = None

    def copy_to_usb(self, path):
        # Look for mounted drives in /media and /mnt
        usb_paths = []
        for root in ['/media', '/mnt']:
            if os.path.exists(root):
                for d in os.listdir(root):
                    full_d = os.path.join(root, d)
                    if os.path.ismount(full_d) or (root == '/media' and os.path.isdir(full_d)):
                        usb_paths.append(full_d)
        
        if not usb_paths:
            self.stdscr.addstr(15, 2, "Kein USB-Stick gefunden!")
            self.stdscr.getch()
            return

        selected_usb = 0
        while True:
            self.stdscr.clear()
            self.stdscr.addstr(0, 0, "Wähle USB-Stick:", curses.A_BOLD)
            for i, usb in enumerate(usb_paths):
                if i == selected_usb:
                    self.stdscr.attron(curses.color_pair(3))
                self.stdscr.addstr(i + 2, 2, f" {usb} ")
                if i == selected_usb:
                    self.stdscr.attroff(curses.color_pair(3))
            
            self.stdscr.refresh()
            key = self.stdscr.getch()
            if key == curses.KEY_UP:
                selected_usb = max(0, selected_usb - 1)
            elif key == curses.KEY_DOWN:
                selected_usb = min(len(usb_paths) - 1, selected_usb + 1)
            elif key == ord('\n'):
                target_usb = usb_paths[selected_usb]
                dest = os.path.join(target_usb, os.path.basename(path))
                try:
                    if os.path.isdir(path):
                        shutil.copytree(path, dest)
                    else:
                        shutil.copy2(path, dest)
                    self.stdscr.addstr(15, 2, "Erfolgreich kopiert!")
                except Exception as e:
                    self.stdscr.addstr(15, 2, f"Fehler: {str(e)[:40]}")
                self.stdscr.getch()
                return
            elif key == 27:
                return

if __name__ == "__main__":
    curses.wrapper(FileManager)
