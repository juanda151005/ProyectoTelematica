#!/usr/bin/env bash
set -euo pipefail

# Uso:
#   chmod +x scripts/deploy_ec2.sh
#   ./scripts/deploy_ec2.sh /opt/groupsapp

APP_DIR=${1:-/opt/groupsapp}
SERVICE_USER=${SERVICE_USER:-ubuntu}
SERVICE_NAME=${SERVICE_NAME:-groupsapp}
PYTHON_BIN=${PYTHON_BIN:-python3}
PORT=${PORT:-8000}

sudo apt-get update
sudo apt-get install -y nginx rsync ${PYTHON_BIN}-venv ${PYTHON_BIN}-pip

sudo mkdir -p "${APP_DIR}"
sudo chown -R "${SERVICE_USER}:${SERVICE_USER}" "${APP_DIR}"

# Copia del proyecto al directorio de despliegue.
rsync -av --exclude '.git' --exclude '.venv' ./ "${APP_DIR}/"

cd "${APP_DIR}"

${PYTHON_BIN} -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
cp -n .env.example .env || true

sudo tee /etc/systemd/system/${SERVICE_NAME}.service >/dev/null <<UNIT
[Unit]
Description=GroupsApp FastAPI Service
After=network.target

[Service]
User=${SERVICE_USER}
Group=${SERVICE_USER}
WorkingDirectory=${APP_DIR}
Environment=PYTHONUNBUFFERED=1
ExecStart=${APP_DIR}/.venv/bin/gunicorn app.main:app -k uvicorn.workers.UvicornWorker -b 127.0.0.1:${PORT} --workers 2
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
UNIT

sudo tee /etc/nginx/sites-available/${SERVICE_NAME} >/dev/null <<NGINX
server {
    listen 80;
    server_name _;

    client_max_body_size 25M;

    location / {
        proxy_pass http://127.0.0.1:${PORT};
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
NGINX

sudo ln -sf /etc/nginx/sites-available/${SERVICE_NAME} /etc/nginx/sites-enabled/${SERVICE_NAME}
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl daemon-reload
sudo systemctl enable ${SERVICE_NAME}
sudo systemctl restart ${SERVICE_NAME}
sudo systemctl restart nginx

echo "Despliegue completado. Verifica:"
echo "  sudo systemctl status ${SERVICE_NAME}"
echo "  curl http://<EC2_PUBLIC_IP>/docs"
