## OpenNAX (by NAX Entertainment) | ![Version](https://img.shields.io/badge/dynamic/yaml?url=https%3A%2F%2Fraw.githubusercontent.com%2FOpenNAX%2FAPI%2Fmain%2FOpenNAX-AILab.txt&query=%24.version&label=version&color=blue) AILab is a utility for simplifying running and installing Ollama.

*Unix only*

Run the following commands to continue

### One time (if you dont use Debian-based, install git by using your package manager):
```bash
apt update && apt install git -y
git clone https://github.com/OpenNAX/AILab.git
cd AILab
```

### One time:
```bash
chmod +x installer.sh
chmod +x run.sh
./installer.sh
```

### Normal run:
```bash
./run.sh
```

### Advanced Run Options (Bypass Flags):
AILab includes extreme, hardware-level optimizations out of the box (Dynamic RAM Allocation, Termux WakeLocks, CPU Affinity pinning, KV Cache Quantization, App Nap prevention, etc). 

If you are running AILab on a specific hardware configuration and want to disable certain protections, you can pass the following bypass flags to `run.sh`:

- `--web` : Binds the Ollama host to `0.0.0.0` instead of the optimized local `127.0.0.1` loopback. Useful if you want to connect to AILab from another device on your network.
- `--oom-bypass` : Disables all aggressive Termux/Android memory protections (OOM Killer avoidance, `mmap` disables, strict parallelism limits). *Warning: May cause your mobile device to freeze or restart if RAM runs out.*
- `--no-gov` : Prevents the script from automatically switching your Linux CPU governor to `performance`. Useful if you manage your CPU frequencies with other daemons like `TLP` or `auto-cpufreq`.
- `--max-threads` : Disables Thermal/Battery thread protections. By default, AILab restricts Ollama to high-performance cores (P-Cores on macOS) or half the logical threads (Linux/Android) to prevent thermal throttling and save battery. This flag forces Ollama to use 100% of available CPU threads.
- `--fp16-cache` : Disables the global 8-bit (`q8_0`) KV Cache quantization. The model will remember context in full FP16 precision. *Warning: This doubles the RAM usage for long contexts and may force macOS/Linux into using disk Swap, severely impacting inference speed.*
- `--no-keepalive` : Disables the infinite memory lock (`KEEP_ALIVE="-1"`). The model will be unloaded from RAM if inactive for 5 minutes, freeing up memory for other tasks.