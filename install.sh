#!/bin/bash
# Instala/reinstala as notificacoes RaspController de presenca no quarto.
# Uso: ./install.sh   (rodar de dentro da pasta clonada do repositorio)

set -e

REPO_URL="https://github.com/rtavares-g/raspc-notificacao.git"
INSTALL_DIR="$HOME/raspc-notificacao"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$SCRIPT_DIR" != "$INSTALL_DIR" ]; then
    if [ ! -d "$INSTALL_DIR" ]; then
        git clone "$REPO_URL" "$INSTALL_DIR"
    fi
    cd "$INSTALL_DIR"
else
    cd "$SCRIPT_DIR"
fi

sudo apt update
sudo apt install -y python3-venv python3-pip openssl

if [ ! -f .env ]; then
    cp .env.example .env
    chmod 600 .env

    echo
    echo "==> Configuracao do RaspController (deixe em branco para pular e editar depois)"
    read -rsp "API Key: " RASPC_APIKEY
    echo

    if [ -n "$RASPC_APIKEY" ]; then
        sed -i "s|^RASPC_APIKEY=.*|RASPC_APIKEY=$RASPC_APIKEY|" .env
    else
        echo "==> API Key ficou em branco - edite depois com: nano $(pwd)/.env"
    fi
fi

if [ ! -d venv ]; then
    python3 -m venv venv
fi
./venv/bin/pip install -r requirements.txt

if [ ! -f "$HOME/presenca-quarto/estado.json" ]; then
    echo "==> Aviso: $HOME/presenca-quarto/estado.json nao existe ainda - instale/inicie o presenca-quarto"
fi

sudo cp raspc-notificacao.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now raspc-notificacao
sudo systemctl restart raspc-notificacao
systemctl status raspc-notificacao --no-pager

echo
read -rp "Enviar uma notificacao de teste agora? [s/N]: " ENVIAR_TESTE
if [[ "$ENVIAR_TESTE" =~ ^[sS] ]]; then
    ./venv/bin/python - <<'PYEOF'
import notificar_presenca as m
from raspc_notif import notif

r = notif.Sender(m.carregar_apikey()).send_notification(
    notif.Notification("Teste", "Notificação de teste do raspc-notificacao"))
print(f"==> Resultado: {r.status} {r.message}")
PYEOF
fi
