#!/bin/bash

clear

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

echo ""
echo "[+] Starting OpenNAX AILab | v2.0.0"

if [ "$(id -u)" -eq 0 ]; then
    nice -n -10 python3 ailab.py
else
    python3 ailab.py
fi