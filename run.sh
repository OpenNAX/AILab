#!/bin/bash

clear

OOM_BYPASS=0

for arg in "$@"; do
    case $arg in
        --oom-bypass)
        OOM_BYPASS=1
        shift
        ;;
    esac
done

echo "[*] Optimizing system resources for Local AI (GPU/CPU)..."

ulimit -n 65535 2>/dev/null || true

ulimit -l unlimited 2>/dev/null || true

ORIG_GOV="ondemand"

restore_governor() {
    if [[ "$OSTYPE" == "linux-gnu"* ]] && [[ -z "$TERMUX_VERSION" ]]; then
        if [ "$ORIG_GOV" != "performance" ] && command -v cpupower >/dev/null 2>&1; then
            if [ "$(id -u)" -ne 0 ]; then
                sudo -n cpupower frequency-set -g "$ORIG_GOV" >/dev/null 2>&1 || true
            else
                cpupower frequency-set -g "$ORIG_GOV" >/dev/null 2>&1 || true
            fi
        fi
    fi
}

if [[ "$OSTYPE" == "linux-gnu"* ]] && [[ -z "$TERMUX_VERSION" ]]; then
    if [ -f /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor ]; then
        ORIG_GOV=$(cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor)
    fi
    
    if [ "$ORIG_GOV" != "performance" ] && command -v cpupower >/dev/null 2>&1; then
        if [ "$(id -u)" -ne 0 ]; then
            if ! sudo -n true 2>/dev/null; then
                echo ""
                echo "[!] Sudo privileges requested to set CPU governor to 'performance'."
                echo "    This will significantly improve AI inference speed."
                echo "    (If you prefer not to, press Enter to skip or type your password)"
                sudo -v 2>/dev/null || true
            fi
            sudo cpupower frequency-set -g performance >/dev/null 2>&1 || true
        else
            cpupower frequency-set -g performance >/dev/null 2>&1 || true
        fi
    fi
fi

trap restore_governor EXIT

if [[ "$OOM_BYPASS" -eq 0 ]]; then
    TOTAL_RAM=0
    if [[ "$OSTYPE" == "darwin"* ]]; then
        TOTAL_RAM=$(($(sysctl -n hw.memsize 2>/dev/null) / 1048576))
    elif command -v free >/dev/null 2>&1; then
        TOTAL_RAM=$(free -m | awk '/^Mem:/{print $2}')
    fi

    if [[ -n "$TOTAL_RAM" ]] && [[ "$TOTAL_RAM" -gt 0 ]]; then
        SAFE_RAM=$((TOTAL_RAM * 75 / 100))
        export GOMEMLIMIT="${SAFE_RAM}MiB"
        echo "[*] Dynamic Memory Protection: GOMEMLIMIT set to ${GOMEMLIMIT} (Total RAM: ${TOTAL_RAM}MiB)"
    fi
fi

if [[ -n "$TERMUX_VERSION" ]]; then
    if [[ "$OOM_BYPASS" -eq 1 ]]; then
        echo ""
        echo "[!] Termux detected, but --oom-bypass is enabled."
        echo "    WARNING: Memory protections are DISABLED. Device may freeze or reboot!"
    else
        echo ""
        echo "[!] Termux detected. Applying memory protections (Anti-OOM)..."

        export OLLAMA_NUM_PARALLEL=1
        export OLLAMA_MAX_QUEUE=1
        export OLLAMA_KV_CACHE_TYPE="q8_0"
        export OLLAMA_FLASH_ATTENTION=0
    fi
fi

echo ""
echo "[+] Starting OpenNAX AILab | v2.0.0"

if [ "$(id -u)" -eq 0 ]; then
    nice -n -10 python3 ailab.py
else
    python3 ailab.py
fi