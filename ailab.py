import os
import re
import sys
import time
import curses
import atexit
import signal
import subprocess
from datetime import datetime

BLACK = "\033[0;30m"
RED = "\033[0;31m"
GREEN = "\033[0;32m"
BROWN = "\033[0;33m"
BLUE = "\033[0;34m"
PURPLE = "\033[0;35m"
CYAN = "\033[0;36m"
LIGHT_GRAY = "\033[0;37m"
DARK_GRAY = "\033[1;30m"
LIGHT_RED = "\033[1;31m"
LIGHT_GREEN = "\033[1;32m"
YELLOW = "\033[1;33m"
LIGHT_BLUE = "\033[1;34m"
LIGHT_PURPLE = "\033[1;35m"
LIGHT_CYAN = "\033[1;36m"
LIGHT_WHITE = "\033[1;37m"
BOLD = "\033[1m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
CROSSED = "\033[9m"
RESET = "\033[0m"

ollama_process = None

def clear():
    os.system("clear")

def print_banner():
    clear()
    version = "v1.0.0"
    opennax = f"""{LIGHT_CYAN}
    ███████                                  ██████   █████   █████████   █████ █████
  ███░░░░░███                               ░░██████ ░░███   ███░░░░░███ ░░███ ░░███
 ███     ░░███ ████████   ██████  ████████   ░███░███ ░███  ░███    ░███  ░░███ ███
░███      ░███░░███░░███ ███░░███░░███░░███  ░███░░███░███  ░███████████   ░░█████
░███      ░███ ░███ ░███░███████  ░███ ░███  ░███ ░░██████  ░███░░░░░███    ███░███
░░███     ███  ░███ ░███░███░░░   ░███ ░███  ░███  ░░█████  ░███    ░███   ███ ░░███
 ░░░███████░   ░███████ ░░██████  ████ █████ █████  ░░█████ █████   █████ █████ █████
   ░░░░░░░     ░███░░░   ░░░░░░  ░░░░ ░░░░░ ░░░░░    ░░░░░ ░░░░░   ░░░░░ ░░░░░ ░░░░░
               ░███
               █████
              ░░░░░
    {RESET}"""
    print(opennax)
    print(f"{CYAN}Starting AILab · {version}...{RESET}\n")

def cleanup():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"{YELLOW}[ALERT] [{timestamp}] Stopping ollama processes...{RESET}")
    try:
        subprocess.run(["killall", "ollama"], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    except Exception:
        pass

def get_installed_models():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    try:
        time.sleep(1)
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        if len(lines) <= 1:
            return []
            
        models = []
        for line in lines[1:]:
            parts = line.split()
            if not parts:
                continue
            name = parts[0]
            
            size_str = "Unknown"
            if len(parts) >= 3:
                if any(x in parts[2] for x in ["GB", "MB", "KB", "B"]):
                    size_str = parts[2]
                elif len(parts) >= 4 and parts[3] in ["GB", "MB", "KB", "B"]:
                    size_str = f"{parts[2]} {parts[3]}"
            
            params_str = "Unknown"
            try:
                show_res = subprocess.run(["ollama", "show", name], capture_output=True, text=True)
                for show_line in show_res.stdout.split('\n'):
                    if "parameters" in show_line.lower():
                        params_str = show_line.split()[-1]
                        break
            except Exception:
                pass
                
            base_name = name.split(':')[0]
            match = re.match(r"([a-zA-Z\-]+)(.*)", base_name)
            if match:
                name_part = match.group(1).capitalize()
                num_part = match.group(2)
                clean_name = f"{name_part} {num_part}".strip() if num_part else name_part
            else:
                clean_name = base_name.capitalize()
                
            display_name = f"{clean_name} (Size: {size_str} | Params: {params_str})"
            models.append({"name": name, "display": display_name})
            
        return models
        
    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        print(f"{RED}[ERROR] [{timestamp}] 'ollama' command not found. Ensure Ollama is installed.{RESET}")
        sys.exit(1)

def display_interactive_menu(stdscr, models):
    curses.curs_set(0)
    
    display_items = [m["display"] for m in models]
    if not display_items:
        display_items.append("No models found")
    display_items.append("[Install new model]")
    
    current_row = 1 if not models else 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, "Select Ollama model (Up/Down: Move | Enter: Select | 'q': Quit):", curses.A_BOLD)

        for idx, item in enumerate(display_items):
            x = 2
            y = 2 + idx
            if idx == current_row:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(y, x, f"> {item}")
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(y, x, f"  {item}")

        stdscr.refresh()

        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            if not models and current_row == 1:
                pass
            else:
                current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(display_items) - 1:
            current_row += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            if not models and current_row == 0:
                pass
            elif current_row == len(display_items) - 1:
                return "[Install new model]"
            else:
                return models[current_row]["name"]
        elif key == ord('q'):
            return None

def start_ollama_server():
    global ollama_process
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    print(f"{LIGHT_GREEN}[{timestamp}] Starting ollama server in background...{RESET}")
    with open('/dev/null', 'w') as devnull:
        try:
            ollama_process = subprocess.Popen(["ollama", "serve"], stdout=devnull, stderr=devnull)
        except FileNotFoundError:
            print(f"{RED}[ERROR] [{timestamp}] Could not start ollama server. Ensure Ollama has been installed using install.sh.{RESET}")
            sys.exit(1)

def run_curses_ui(stdscr, models):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    return display_interactive_menu(stdscr, models)

def main():
    print_banner()
    
    start_ollama_server()
    atexit.register(cleanup)

    def signal_handler(sig, frame):
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)

    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"{LIGHT_GREEN}[{timestamp}] Fetching model list...{RESET}")
    
    models = get_installed_models()

    time.sleep(1.5)

    selected_model = curses.wrapper(run_curses_ui, models)

    if selected_model == "[Install new model]":
        model_name = input(f"\n{LIGHT_CYAN}Enter model name to install: {RESET}")
        if model_name.strip():
            end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"\n{LIGHT_CYAN}[{end_timestamp}] Installing and starting model: {model_name.strip()}...{RESET}\n")
            try:
                subprocess.run(["ollama", "run", model_name.strip()])
            except KeyboardInterrupt:
                pass
        else:
            end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"\n{YELLOW}[ALERT] [{end_timestamp}] Installation cancelled.{RESET}")
    elif selected_model:
        end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"\n{LIGHT_CYAN}[{end_timestamp}] Starting model: {selected_model}...{RESET}\n")
        try:
            subprocess.run(["ollama", "run", selected_model])
        except KeyboardInterrupt:
            pass
    else:
        end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
        print(f"\n{YELLOW}[ALERT] [{end_timestamp}] Selection cancelled.{RESET}")

if __name__ == "__main__":
    main()