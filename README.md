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
- `--max-threads` : Disables Thermal/Battery thread protections. By default, AILab restricts Ollama to high-performance cores (P-Cores on macOS) or `N-1` logical threads (Linux/Android) to maintain system responsiveness. This flag forces Ollama to use 100% of available CPU threads.
- `--power-save` : Restores the legacy battery-saving behavior (Linux/Android only), limiting Ollama to 50% of available CPU cores. Useful if you want to run AILab in the background without depleting your mobile battery.
- `--elite` : Forces the **Elite Performance Mode** regardless of RAM. This enables memory-mapped files (`mmap`), Flash Attention, and high-precision FP16 KV cache. Recommended for Snapdragon 8 Gen 2 / 8 Elite or similar top-tier hardware.

### GPU Acceleration (Adreno/Vulkan):
AILab now includes an automated **Vulkan Bridge** for Android/Termux. 
- The script automatically scans for system drivers in `/vendor` and `/system`.
- It creates a symlink in `$PREFIX/lib/libvulkan.so` to bridge Android and Termux environments.
- It generates a custom **Adreno ICD** (`adreno_icd.json`) to force Vulkan tools to see your mobile GPU.

**To verify GPU status**:
1. Run `./run.sh`.
2. Load a model.
3. In another terminal, run `ollama ps`. If the processor shows `GPU`, the bridge is active.

- `--fp16-cache` : (Legacy) Disables the global 8-bit (`q8_0`) KV Cache quantization. Note: Elite Mode enables this by default

- `--no-keepalive` : Disables the infinite memory lock (`KEEP_ALIVE="-1"`). The model will be unloaded from RAM if inactive for 5 minutes, freeing up memory for other tasks.