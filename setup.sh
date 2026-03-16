#!/bin/bash
set -e

echo "==> Setting up Mocha Cat Terminal..."

# --- Config ---
INSTALL_DIR=/opt/mocha
SERVICE_USER=${USER:-ubuntu}

# 1. Copy files
sudo mkdir -p $INSTALL_DIR
sudo chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

# 2. Python venv
cd $INSTALL_DIR
python3 -m venv venv
./venv/bin/pip install --quiet -r requirements.txt

# 3. Check your exact model name in Ollama
echo ""
echo "==> Your available Ollama models:"
curl -s http://localhost:11434/api/tags | python3 -c "
import json,sys
data=json.load(sys.stdin)
for m in data.get('models',[]):
    print(' -', m['name'])
"

echo ""
echo "==> Edit OLLAMA_MODEL in mocha.service to match one of the above, then:"
echo ""

# 4. Install systemd service
sudo cp mocha.service /etc/systemd/system/
sudo sed -i "s/User=ubuntu/User=$SERVICE_USER/" /etc/systemd/system/mocha.service
sudo systemctl daemon-reload
sudo systemctl enable mocha
sudo systemctl restart mocha

echo "==> Done! Mocha is running at http://$(hostname -I | awk '{print $1}'):8400"
echo ""
echo "Useful commands:"
echo "  sudo systemctl status mocha   # check status"
echo "  sudo journalctl -u mocha -f   # tail logs"
echo "  sudo systemctl restart mocha  # restart"
