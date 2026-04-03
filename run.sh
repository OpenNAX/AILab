#!/bin/bash

clear

OOM_BYPASS=0
WEB_MODE=0
NO_GOV=0
MAX_THREADS=0
FP16_CACHE=0
NO_KEEPALIVE=0
POWER_SAVE=0


for arg in "$@"; do
    case $arg in
        --oom-bypass)
        OOM_BYPASS=1
        shift
        ;;
        --web)
        WEB_MODE=1
        shift
        ;;
        --no-gov)
        NO_GOV=1
        shift
        ;;
        --max-threads)
        MAX_THREADS=1
        shift
        ;;
        --fp16-cache)
        FP16_CACHE=1
        shift
        ;;
        --no-keepalive)
        NO_KEEPALIVE=1
        shift
        ;;
        --power-save)
        POWER_SAVE=1
        shift
        ;;
    esac

done

if [[ "$WEB_MODE" -eq 1 ]]; then
    export OLLAMA_HOST="0.0.0.0"
else
    export OLLAMA_HOST="127.0.0.1:11434"
fi

export GIN_MODE=release

if [[ "$NO_KEEPALIVE" -eq 0 ]]; then
    export OLLAMA_KEEP_ALIVE="-1"
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONUNBUFFERED=1

if [[ "$FP16_CACHE" -eq 0 ]]; then
    export OLLAMA_KV_CACHE_TYPE="q8_0"
fi

export OPENNAX_AILAB_RUN="1"

echo "[*] Optimizing system resources for Local AI (GPU/CPU)..."

ulimit -n 65535 2>/dev/null || true

ulimit -l unlimited 2>/dev/null || true

ORIG_GOV="ondemand"

restore_governor() {
    if [[ -n "$TERMUX_VERSION" ]] && command -v termux-wake-unlock >/dev/null 2>&1; then
        termux-wake-unlock >/dev/null 2>&1 || true
    fi

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

if [[ "$OSTYPE" == "linux-gnu"* ]] && [[ -z "$TERMUX_VERSION" ]] && [[ "$NO_GOV" -eq 0 ]]; then
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

if [[ -n "$TERMUX_VERSION" ]]; then
    if command -v termux-wake-lock >/dev/null 2>&1; then
        echo "[*] Android/Termux detected: Acquiring WakeLock to prevent Doze Mode throttling..."
        termux-wake-lock >/dev/null 2>&1 || true
    fi
fi

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
        export OLLAMA_FLASH_ATTENTION=0
        export OLLAMA_NOMMAP=1
        export GOGC=50
    fi
fi

if [[ "$MAX_THREADS" -eq 0 ]]; then
    if [[ "$OSTYPE" == "darwin"* ]]; then
        P_CORES=$(sysctl -n hw.perflevel0.physicalcpu 2>/dev/null)
        if [ -z "$P_CORES" ] || [ "$P_CORES" -eq 0 ]; then
            P_CORES=$(sysctl -n hw.physicalcpu 2>/dev/null)
        fi
        export OLLAMA_NUM_THREADS=${P_CORES:-4}
    else
        LOGICAL_CORES=$(nproc 2>/dev/null || echo 4)
        if [[ "$POWER_SAVE" -eq 1 ]]; then
            OPT_THREADS=$((LOGICAL_CORES / 2))
            if [ "$OPT_THREADS" -eq 0 ]; then OPT_THREADS=1; fi
            echo "[*] Power Save Mode: Limiting CPU threads to 50% (${OPT_THREADS})"
        else
            OPT_THREADS=$((LOGICAL_CORES - 1))
            if [ "$OPT_THREADS" -le 0 ]; then OPT_THREADS=1; fi
            echo "[*] Performance Mode: Using almost all logical cores (${OPT_THREADS})"
        fi
        export OLLAMA_NUM_THREADS=${OPT_THREADS}
    fi
else
    echo "[!] MAX_THREADS bypass enabled: Unrestricted CPU usage."
fi


echo ""
echo "[+] Starting OpenNAX AILab | v1.0.0"

if [[ "$OSTYPE" == "darwin"* ]]; then
    echo "[*] macOS detected: Wrapping with 'caffeinate' to prevent App Nap & sleep..."
    if [ "$(id -u)" -eq 0 ]; then
        echo "[*] Flushing inactive macOS cache (purge) to maximize free RAM..."
        purge >/dev/null 2>&1 || true
        caffeinate -i nice -n -10 python3 -O ailab.py
    else
        caffeinate -i python3 -O ailab.py
    fi
else
    if [ "$(id -u)" -eq 0 ]; then
        nice -n -10 python3 -O ailab.py
    else
        python3 -O ailab.py
    fi
fi