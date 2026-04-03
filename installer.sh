clear
echo "[*] OpenNAX AILab · v1.0.0"
echo "Starting download of required packages..."

echo "[+] Installing Ollama and GPU dependencies..."
apt install ollama vulkan-loader-android vulkan-tools -y > /dev/null 2>&1

echo "\n-----------------------------------------------------"
echo "Installation complete!"
echo "From now, you can now run it by using the run.sh script."
echo "-----------------------------------------------------"
