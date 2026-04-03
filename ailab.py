import os
import re
import sys
import time
import socket
import curses
import atexit
import signal
import subprocess
import concurrent.futures
from datetime import datetime

if os.environ.get("OPENNAX_AILAB_RUN") != "1":
    print("\033[1;31m[ERROR] Do not run this script directly. Please use ./run.sh instead to apply system optimizations.\033[0m")
    sys.exit(1)

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
    version = "v2.1.0"


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
    global ollama_process
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    if ollama_process:
        print(f"{YELLOW}[ALERT] [{timestamp}] Stopping AILab ollama process...{RESET}")
        try:
            ollama_process.terminate()
            ollama_process.wait(timeout=2)
        except Exception:
            pass

def _fetch_model_info(line):
    parts = line.split()
    if not parts:
        return None
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
        
    # Restore sanitization for clean UI (e.g. gemma3:4b -> Gemma 3)
    base_name = name.split(':')[0]
    match = re.match(r"([a-zA-Z\-]+)([0-9\.]*).*", base_name)
    if match:
        name_part = match.group(1).replace('-', ' ').strip().capitalize()
        num_part = match.group(2)
        clean_name = f"{name_part} {num_part}".strip() if num_part else name_part
    else:
        clean_name = base_name.capitalize()
        
    display_name = f"{clean_name} (Size: {size_str} | Params: {params_str})"
    return {"name": name, "display": display_name}


def wait_for_server(host="127.0.0.1", port=11434, timeout=30):
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"{YELLOW}[WAIT] [{timestamp}] Waiting for Ollama server to be ready on {host}:{port}...{RESET}")
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (socket.timeout, ConnectionRefusedError):
            time.sleep(1)
    return False

def get_installed_models():
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    # Ensure server is ready before listing
    host_port = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434").replace("http://", "").split(":")
    host = host_port[0]
    port = int(host_port[1]) if len(host_port) > 1 else 11434
    
    try:
        if not wait_for_server(host, port):
            print(f"{RED}[ERROR] [{timestamp}] Ollama server did not start in time. Check 'ollama_server.log' for details.{RESET}")
            return []
    except KeyboardInterrupt:
        return []

    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, check=True)
        lines = result.stdout.strip().split('\n')
        
        if len(lines) <= 1:
            return []
            
        models = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = executor.map(_fetch_model_info, lines[1:])
            for res in results:
                if res:
                    models.append(res)
            
        return models
        
    except subprocess.CalledProcessError:
        return []
    except FileNotFoundError:
        print(f"{RED}[ERROR] [{timestamp}] 'ollama' command not found. Ensure Ollama is installed.{RESET}")
        sys.exit(1)

# --- Intelligent Models Catalog (Curated) ---
MODELS_CATALOG = [
    # --- ULTRA LIGHT (2GB-4GB) ---
    {"id": "gemma3:4b", "ram": 4, "desc": "Current king of lightweight models. Multimodal and high quality.", "cat": "Ultra Light", "priority": 10},
    {"id": "deepseek-r1:1.5b", "ram": 2, "desc": "Incredible reasoning capabilities for its size.", "cat": "Ultra Light", "priority": 9},
    {"id": "llama3.2:3b", "ram": 3, "desc": "Very fast, efficient and excellent for direct chat.", "cat": "Ultra Light", "priority": 8},
    
    # --- SWEET POINT (8GB-12GB) ---
    {"id": "deepseek-r1:8b", "ram": 8, "desc": "Distilled from R1. Brilliant intelligence with low consumption.", "cat": "Sweet Point", "priority": 20},
    {"id": "gemma3:12b", "ram": 10, "desc": "Best all-rounder. Multimodal and competes with larger models.", "cat": "Sweet Point", "priority": 19},
    {"id": "qwen2.5:7b", "ram": 8, "desc": "Excellent multilingual support, solid in math and coding.", "cat": "Sweet Point", "priority": 18},
    
    # --- HIGH PERFORMANCE (24GB+) ---
    {"id": "gemma3:27b", "ram": 20, "desc": "Closed commercial model quality in an open format.", "cat": "High Performance", "priority": 30},
    {"id": "qwen2.5:32b", "ram": 24, "desc": "A beast for software development and complex writing.", "cat": "High Performance", "priority": 31},
    {"id": "llama3.3:70b", "ram": 40, "desc": "Most powerful open model. Requires heavy hardware.", "cat": "High Performance", "priority": 32},
    
    # --- SUPPORT TOOLS ---
    {"id": "nomic-embed-text", "ram": 1, "desc": "Text embeddings for RAG (reading PDFs/txt efficiently).", "cat": "Support Tools", "priority": 5},
    {"id": "qwen2.5-coder:1.5b", "ram": 2, "desc": "Fast code autocompletion for background tasks.", "cat": "Support Tools", "priority": 4},
]

def get_system_memory_gb():
    """Detects total physical RAM in GB with a fallback for andriod/linux."""
    try:
        if os.path.exists('/proc/meminfo'):
            with open('/proc/meminfo', 'r') as f:
                for line in f:
                    if "MemTotal" in line:
                        mem_kb = int(line.split()[1])
                        return round(mem_kb / (1024 * 1024), 2)
        # Fallback using sysconf (POSIX systems)
        pages = os.sysconf('SC_PHYS_PAGES')
        page_size = os.sysconf('SC_PAGE_SIZE')
        return round((pages * page_size) / (1024**3), 2)
    except Exception:
        return 8.0 # Default if anything fails

def display_recommendation_menu(stdscr, ai_budget_gb):
    curses.curs_set(0)
    current_row = 0
    
    # Smart sorting logic:
    # 1. Models within budget first
    # 2. Sort by categorical priority (Sweet Point > Ultra Light > Tools > Heavy)
    def sort_score(m):
        within_budget = 1 if m["ram"] <= ai_budget_gb else 0
        # If within budget, we prioritize Sweet Point (priority ~20), then Ultra Light (priority ~10)
        # If not within budget, they go to the bottom.
        return (within_budget, m["priority"])
    
    sorted_catalog = sorted(MODELS_CATALOG, key=sort_score, reverse=True)
    
    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Recommended Models (AI Budget: {ai_budget_gb}GB | 50% OS Rule):", curses.A_BOLD)
        
        for idx, model in enumerate(sorted_catalog):
            x = 2
            y = 2 + (idx * 2) 
            
            status = "[RECOMMENDED]" if model["ram"] <= ai_budget_gb else "[! HEAVY]"
            color_pair = 1 if idx == current_row else 0
            
            if color_pair == 1:
                stdscr.attron(curses.color_pair(1))
            
            label = f"{status} {model['id']} ({model['cat']})"
            stdscr.addstr(y, x, label)
            stdscr.addstr(y + 1, x + 4, f"Info: {model['desc']}", curses.A_ITALIC)
            
            stdscr.attroff(curses.color_pair(1))
        
        stdscr.refresh()
        key = stdscr.getch()
        
        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(sorted_catalog) - 1:
            current_row += 1
        elif key in [curses.KEY_ENTER, 10, 13]:
            return sorted_catalog[current_row]["id"]
        elif key == ord('q'):
            return None

def display_interactive_menu(stdscr, models):
    curses.curs_set(0)
    
    display_items = [m["display"] for m in models]
    if not display_items:
        display_items.append("No models found")
    display_items.append("[Install new model]")
    display_items.append("[Delete model]")
    
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
            elif display_items[current_row] == "[Install new model]":
                return "[Install new model]"
            elif display_items[current_row] == "[Delete model]":
                return "[Delete model]"
            else:
                return models[current_row]["name"]
        elif key == ord('q'):
            return None

def start_ollama_server():
    global ollama_process
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    
    print(f"{LIGHT_GREEN}[{timestamp}] Starting ollama server in background...{RESET}")
    
    cmd = []
    
    if sys.platform.startswith("linux") and os.environ.get("OLLAMA_PIN_CORES") == "1":

        if subprocess.call("command -v taskset >/dev/null 2>&1", shell=True) == 0:
            try:
                cpu_count = os.cpu_count() or 4
                num_threads = int(os.environ.get("OLLAMA_NUM_THREADS", cpu_count))
                start_core = max(0, cpu_count - num_threads)
                end_core = cpu_count - 1
                cmd.extend(["taskset", "-c", f"{start_core}-{end_core}"])
            except Exception:
                pass
                
    if sys.platform.startswith("linux"):
        if subprocess.call("command -v ionice >/dev/null 2>&1", shell=True) == 0:
            cmd.extend(["ionice", "-c", "2", "-n", "0"])
            
    if subprocess.call("command -v nice >/dev/null 2>&1", shell=True) == 0:
        if hasattr(os, 'geteuid') and os.geteuid() == 0:
            cmd.extend(["nice", "-n", "-5"])
        
    cmd.extend(["ollama", "serve"])
    
    log_file = open('ollama_server.log', 'w')
    try:
        ollama_process = subprocess.Popen(cmd, stdout=log_file, stderr=log_file)
    except FileNotFoundError:
        print(f"{RED}[ERROR] [{timestamp}] Could not start ollama server. Ensure Ollama has been installed.{RESET}")
        sys.exit(1)


def run_curses_ui(stdscr, models):
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
    return display_interactive_menu(stdscr, models)

def main():
    print_banner()
    
    start_ollama_server()
    atexit.register(cleanup)

    while True:
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
            print(f"{LIGHT_GREEN}[{timestamp}] Fetching model list...{RESET}")
            
            models = get_installed_models()
            selected_model = curses.wrapper(run_curses_ui, models)

            if selected_model is None: # Pressed 'q'
                break

            if selected_model == "[Install new model]":
                # New sub-menu for installation type
                install_menu_items = ["[View Recommended Models]", "[Custom Installation (Manual Name)]", "[Go back]"]
                
                def run_install_menu(scr):
                    curses.start_color()
                    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_WHITE)
                    current_row = 0
                    while True:
                        scr.clear()
                        scr.addstr(0, 0, "Select installation method:", curses.A_BOLD)
                        for idx, item in enumerate(install_menu_items):
                            if idx == current_row:
                                scr.attron(curses.color_pair(1)); scr.addstr(2+idx, 2, f"> {item}"); scr.attroff(curses.color_pair(1))
                            else:
                                scr.addstr(2+idx, 2, f"  {item}")
                        scr.refresh()
                        k = scr.getch()
                        if k == curses.KEY_UP and current_row > 0: current_row -= 1
                        elif k == curses.KEY_DOWN and current_row < len(install_menu_items)-1: current_row += 1
                        elif k in [10, 13]: return install_menu_items[current_row]
                        elif k == ord('q'): return "[Go back]"
                
                install_choice = curses.wrapper(run_install_menu)
                
                model_to_install = None
                if install_choice == "[View Recommended Models]":
                    total_ram = get_system_memory_gb()
                    ai_budget = round(total_ram * 0.5, 2)
                    model_to_install = curses.wrapper(display_recommendation_menu, ai_budget)
                elif install_choice == "[Custom Installation (Manual Name)]":
                    try:
                        model_to_install = input(f"\n{LIGHT_CYAN}Enter manual model name to install (e.g. llama3): {RESET}")
                    except (KeyboardInterrupt, EOFError):
                        pass
                
                if model_to_install and model_to_install.strip():
                    model_name = model_to_install.strip()
                    end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    print(f"\n{LIGHT_CYAN}[{end_timestamp}] Starting session for: {model_name}...{RESET}\n")
                    subprocess.run(["ollama", "run", model_name])
                else:
                    print(f"\n{YELLOW}[INFO] Installation cancelled.{RESET}")
            
            elif selected_model == "[Delete model]":
                try:
                    model_name = input(f"\n{LIGHT_CYAN}Enter model name to delete: {RESET}")
                    if model_name.strip():
                        end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                        print(f"\n{LIGHT_CYAN}[{end_timestamp}] Deleting model: {model_name.strip()}...{RESET}\n")
                        subprocess.run(["ollama", "rm", model_name.strip()])
                except (KeyboardInterrupt, EOFError):
                    print(f"\n{YELLOW}[INFO] Deletion cancelled.{RESET}")
            
            elif selected_model:
                try:
                    end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
                    print(f"\n{LIGHT_CYAN}[{end_timestamp}] Starting model: {selected_model}...{RESET}\n")
                    subprocess.run(["ollama", "run", selected_model])
                except (KeyboardInterrupt, EOFError):
                    print(f"\n{YELLOW}[INFO] Model execution interrupted.{RESET}")
            
        except (KeyboardInterrupt, EOFError):
            continue
        except Exception as e:
            if not isinstance(e, SystemExit):
                print(f"\n{RED}[ERROR] Unhandled error: {e}{RESET}")
                time.sleep(2)
        
    end_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]
    print(f"\n{YELLOW}[EXIT] [{end_timestamp}] Exiting AILab...{RESET}")

if __name__ == "__main__":
    main()