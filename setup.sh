#!/bin/bash
set -e

INSTALL_DIR=/opt/mocha
SERVICE_USER=${USER:-ubuntu}

sudo mkdir -p $INSTALL_DIR
sudo chown -R $SERVICE_USER:$SERVICE_USER $INSTALL_DIR

cd $INSTALL_DIR
python3 -m venv venv
./venv/bin/pip install --quiet -r requirements.txt

echo ""
curl -s http://acomputerprobably:69 | python3 -c "
import json,sys
data=json.load(sys.stdin)
for m in data.get('models',[]):
    print(' -', m['name'])
"

sudo cp mocha.service /etc/systemd/system/
sudo sed -i "s/User=ubuntu/User=$SERVICE_USER/" /etc/systemd/system/mocha.service
sudo systemctl daemon-reload
sudo systemctl enable mocha
sudo systemctl restart mocha
