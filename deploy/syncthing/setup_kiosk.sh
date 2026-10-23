#!/usr/bin/env bash
# Partage le dossier du kiosque avec le PC du professeur, en « Envoyer seulement ».
# À lancer en tant qu'utilisateur aristote (provision_kiosk.sh s'en charge).
set -euo pipefail

ID="" TEACHER="" LAN_ONLY=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --id) ID="$2"; shift 2 ;;
    --teacher-device) TEACHER="$2"; shift 2 ;;
    --lan-only) LAN_ONLY=1; shift ;;
    *) echo "option inconnue : $1" >&2; exit 2 ;;
  esac
done
FOLDER_ID="aristote-${ID,,}"
FOLDER_PATH="/var/lib/aristote/vault/$ID"
st() { syncthing cli "$@"; }

for _ in $(seq 1 30); do st show system >/dev/null 2>&1 && break; sleep 1; done
MY_ID=$(st show system | sed -n 's/.*"myID": *"\([^"]*\)".*/\1/p')

st config devices list | grep -q "$TEACHER" || st config devices add --device-id "$TEACHER" --name "professeur"
if ! st config folders list | grep -qx "$FOLDER_ID"; then
  st config folders add --id "$FOLDER_ID" --label "Aristote $ID" --path "$FOLDER_PATH" --type sendonly
fi
st config folders "$FOLDER_ID" devices list | grep -q "$TEACHER" || \
  st config folders "$FOLDER_ID" devices add --device-id "$TEACHER"
# Rien d'autre ne doit être synchronisé : on retire le dossier par défaut s'il existe.
st config folders list | grep -qx default && st config folders default delete || true

if [[ $LAN_ONLY -eq 1 ]]; then
  st config options relays-enabled set false
  st config options global-ann-enabled set false
fi

cat <<MSG
Kiosque prêt à synchroniser.
  Identifiant Syncthing du kiosque : $MY_ID
  Dossier partagé : $FOLDER_ID  ($FOLDER_PATH)
Sur le PC du professeur : accepter l'appareil, puis accepter le dossier en « Recevoir seulement »
dans  <coffre Obsidian>/Aristote/Kiosques/$ID   (voir deploy/syncthing/setup_teacher.md).
MSG
