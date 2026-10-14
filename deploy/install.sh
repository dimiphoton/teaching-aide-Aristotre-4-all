#!/usr/bin/env bash
# Installation complète d'un kiosque Aristote 4 All sur Raspberry Pi OS Bookworm 64 bits (Lite).
# Idempotent : peut être relancé après une mise à jour du dépôt.
#
#   sudo ./deploy/install.sh                 # depuis la racine du dépôt cloné
#   sudo ./deploy/install.sh --no-whisper    # sans le modèle de dictée (installation plus rapide)
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
APP_DIR=/opt/aristote
ETC_DIR=/etc/aristote
DATA_DIR=/var/lib/aristote
USER_NAME=aristote
WITH_WHISPER=1
for arg in "$@"; do
  case "$arg" in
    --no-whisper) WITH_WHISPER=0 ;;
    *) echo "option inconnue : $arg" >&2; exit 2 ;;
  esac
done

log() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
[[ $EUID -eq 0 ]] || { echo "À lancer avec sudo." >&2; exit 1; }

log "Paquets système"
apt-get update
apt-get install -y --no-install-recommends \
  python3-venv python3-dev python3-picamera2 python3-lgpio python3-gpiozero python3-libcamera \
  libportaudio2 tesseract-ocr tesseract-ocr-fra \
  cage fonts-dejavu-core \
  syncthing rsync curl git nodejs npm \
  ufw unattended-upgrades
# Le paquet s'appelle chromium-browser ou chromium selon la version de Raspberry Pi OS.
apt-get install -y --no-install-recommends chromium-browser || apt-get install -y --no-install-recommends chromium
[[ -x /usr/bin/chromium-browser ]] || ln -sf /usr/bin/chromium /usr/bin/chromium-browser

log "Utilisateur $USER_NAME"
if ! id "$USER_NAME" >/dev/null 2>&1; then
  useradd --create-home --shell /bin/bash "$USER_NAME"
fi
usermod -aG gpio,video,audio,dialout,render,input "$USER_NAME"

log "Dossiers"
install -d -o "$USER_NAME" -g "$USER_NAME" "$APP_DIR" "$DATA_DIR" "$DATA_DIR/vault" "$DATA_DIR/eval_corpus"
install -d -m 755 "$ETC_DIR"
rsync -a --delete --exclude node_modules --exclude dist --exclude .venv --exclude '__pycache__' \
  "$REPO_DIR/backend" "$REPO_DIR/frontend" "$APP_DIR/"
chown -R "$USER_NAME:$USER_NAME" "$APP_DIR"

if [[ ! -f "$ETC_DIR/config.toml" ]]; then
  install -m 644 "$REPO_DIR/backend/config.example.toml" "$ETC_DIR/config.toml"
  echo "→ $ETC_DIR/config.toml créé : lancer deploy/provision_kiosk.sh pour le personnaliser."
fi
if [[ ! -f "$ETC_DIR/secrets.env" ]]; then
  cat > "$ETC_DIR/secrets.env" <<'SECRETS'
# Clés d'API (ne jamais versionner, ne jamais copier dans le coffre Obsidian)
MISTRAL_API_KEY=
SECRETS
fi
chown root:"$USER_NAME" "$ETC_DIR/secrets.env"
chmod 640 "$ETC_DIR/secrets.env"

log "Environnement Python"
# --system-site-packages : picamera2 et lgpio viennent des paquets apt.
sudo -u "$USER_NAME" python3 -m venv --system-site-packages "$APP_DIR/venv"
EXTRAS="pi,audio,tesseract"
[[ $WITH_WHISPER -eq 1 ]] && EXTRAS="$EXTRAS,stt"
sudo -u "$USER_NAME" "$APP_DIR/venv/bin/pip" install --upgrade pip
sudo -u "$USER_NAME" "$APP_DIR/venv/bin/pip" install "$APP_DIR/backend[$EXTRAS]"
ln -sf "$APP_DIR/venv/bin/aristote" /usr/local/bin/aristote

if [[ $WITH_WHISPER -eq 1 ]]; then
  log "Modèle de dictée (téléchargé une fois, utilisé hors ligne ensuite)"
  MODEL=$("$APP_DIR/venv/bin/python" -c \
    "from aristote.config import load_config; print(load_config('$ETC_DIR/config.toml').stt.model)")
  install -d -o "$USER_NAME" -g "$USER_NAME" "/home/$USER_NAME/.cache"
  sudo -u "$USER_NAME" "$APP_DIR/venv/bin/python" -c \
    "from faster_whisper import WhisperModel; WhisperModel('${MODEL:-base}', device='cpu', compute_type='int8')"
fi

log "Interface"
(cd "$APP_DIR/frontend" && sudo -u "$USER_NAME" npm ci --no-audit --no-fund && sudo -u "$USER_NAME" npm run build)

log "Imprimante (lien /dev/aristote-printer)"
install -m 644 "$REPO_DIR/deploy/udev/99-aristote-printer.rules" /etc/udev/rules.d/
udevadm control --reload-rules && udevadm trigger --subsystem-match=tty

log "Écran 1280×800 et console"
CMDLINE=/boot/firmware/cmdline.txt
if [[ -f $CMDLINE ]] && ! grep -q "video=HDMI-A-1" "$CMDLINE"; then
  sed -i '1 s/$/ video=HDMI-A-1:1280x800@60 consoleblank=0 quiet/' "$CMDLINE"
fi

log "Services"
install -m 644 "$REPO_DIR"/deploy/systemd/aristote-*.service "$REPO_DIR"/deploy/systemd/aristote-*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl disable --now getty@tty1.service || true
systemctl enable --now aristote-backend.service
systemctl enable aristote-kiosk.service
systemctl enable --now "syncthing@$USER_NAME.service"

log "Pare-feu"
ufw allow OpenSSH
ufw allow 22000/tcp && ufw allow 22000/udp && ufw allow 21027/udp   # Syncthing
ufw --force enable

log "Terminé"
cat <<MSG
Étapes suivantes :
  1. sudo $REPO_DIR/deploy/provision_kiosk.sh --id K01 --students E01,E02,E03,E04 --teacher-device <ID-SYNCTHING-PROF>
  2. Renseigner la clé dans $ETC_DIR/secrets.env (sauf mode 100 % local), puis : sudo systemctl restart aristote-backend
  3. Tester : aristote diag printer | camera | buttons | mic
  4. sudo reboot   (l'interface démarre seule sur l'écran)
MSG
