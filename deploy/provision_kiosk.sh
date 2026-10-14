#!/usr/bin/env bash
# Personnalise un kiosque : identifiant, élèves (pseudonymes), appairage Syncthing avec le professeur.
#
#   sudo ./deploy/provision_kiosk.sh --id K03 --students E09,E10,E11,E12 \
#        --teacher-device XXXXXXX-XXXXXXX-... [--lan-only] [--pin 4821]
set -euo pipefail

ID="" STUDENTS="" TEACHER="" PIN="" LAN_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --id) ID="$2"; shift 2 ;;
    --students) STUDENTS="$2"; shift 2 ;;
    --teacher-device) TEACHER="$2"; shift 2 ;;
    --pin) PIN="$2"; shift 2 ;;
    --lan-only) LAN_ONLY=1; shift ;;
    *) echo "option inconnue : $1" >&2; exit 2 ;;
  esac
done
[[ $EUID -eq 0 ]] || { echo "À lancer avec sudo." >&2; exit 1; }
[[ "$ID" =~ ^[A-Za-z0-9_-]+$ ]] || { echo "--id obligatoire (ex. K03)" >&2; exit 2; }
[[ -n "$STUDENTS" ]] || { echo "--students obligatoire (ex. E09,E10,E11,E12)" >&2; exit 2; }

CONFIG=/etc/aristote/config.toml
/opt/aristote/venv/bin/python - "$CONFIG" "$ID" "$STUDENTS" "$PIN" <<'PY'
import re, sys
path, kiosk_id, students, pin = sys.argv[1:]
text = open(path, encoding="utf-8").read()
names = [s.strip() for s in students.split(",") if s.strip()]
if not 1 <= len(names) <= 4 or not all(re.fullmatch(r"[A-Za-z0-9_-]+", n) for n in names):
    sys.exit("pseudonymes invalides : 1 à 4, lettres/chiffres uniquement (jamais de vrais noms)")
text = re.sub(r'(?m)^id = ".*"$', f'id = "{kiosk_id}"', text, count=1)
text = re.sub(r'(?m)^students = \[.*\]$', "students = [" + ", ".join(f'"{n}"' for n in names) + "]", text, count=1)
if pin:
    text = re.sub(r'(?m)^pin = ".*"', f'pin = "{pin}"', text, count=1)
open(path, "w", encoding="utf-8").write(text)
PY
/opt/aristote/venv/bin/aristote --config "$CONFIG" config >/dev/null  # validation
hostnamectl set-hostname "aristote-${ID,,}"
install -d -o aristote -g aristote "/var/lib/aristote/vault/$ID"

if [[ -n "$TEACHER" ]]; then
  ARGS=(--id "$ID" --teacher-device "$TEACHER")
  [[ $LAN_ONLY -eq 1 ]] && ARGS+=(--lan-only)
  sudo -u aristote "$(dirname "$0")/syncthing/setup_kiosk.sh" "${ARGS[@]}"
fi
systemctl restart aristote-backend
echo "Kiosque $ID configuré pour : $STUDENTS"
