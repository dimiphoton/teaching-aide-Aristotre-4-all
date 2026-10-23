# Synchronisation côté professeur (Syncthing)

Chaque kiosque envoie son dossier `vault/<K>` vers le PC du professeur. Le transfert est direct, chiffré
de bout en bout (TLS), et ne passe par aucun serveur cloud. Les fichiers restent lisibles même si un
kiosque est éteint.

## 1. Installer Syncthing sur le PC du professeur

| Système | Installation |
|---|---|
| Windows | [SyncTrayzor](https://github.com/canton7/SyncTrayzor) ou `winget install Syncthing.Syncthing` |
| macOS | `brew install syncthing` puis `brew services start syncthing` |
| Linux | `sudo apt install syncthing` puis `systemctl --user enable --now syncthing` |

Ouvrir l'interface : <http://127.0.0.1:8384>.

## 2. Donner son identifiant aux kiosques

*Actions → Afficher mon identifiant* : copier l'identifiant (`XXXXXXX-XXXXXXX-…`). Il sert d'argument
`--teacher-device` à `deploy/provision_kiosk.sh` sur chaque kiosque.

## 3. Accepter chaque kiosque

Quelques secondes après la configuration d'un kiosque, l'interface Syncthing du professeur affiche :

1. **« Nouvel appareil »** `aristote-k03` → *Ajouter l'appareil*.
2. **« Nouveau dossier partagé »** `Aristote K03` → *Ajouter*, puis :
   - **Chemin** : `<coffre Obsidian>/Aristote/Kiosques/K03`
   - **Avancé → Type de dossier : Recevoir seulement**

Répéter pour chaque kiosque (7 à 8 pour une classe de 30 élèves).

## 4. Vérifier

Après une session d'élève, le fichier `Aristote/Kiosques/K03/eleves/E09/sessions/…md` apparaît dans Obsidian
en moins d'une minute sur le réseau local.

## Règles à respecter

- **Ne jamais modifier** les fichiers de `Aristote/Kiosques/` : ce dossier est le reflet des kiosques
  (en « Recevoir seulement », vos modifications seraient signalées et annulables). Les analyses vont ailleurs.
- **Ne jamais partager** `Aristote/_Correspondance-eleves.md` (pseudonymes ↔ noms) avec un kiosque.
- Wi-Fi de l'établissement qui isole les appareils : Syncthing passe alors par un relais Internet (toujours
  chiffré). Pour l'interdire, configurer les kiosques avec `--lan-only` et prévoir un petit routeur dédié.

## Alternative sans Syncthing : rsync

Si l'établissement interdit Syncthing, chaque kiosque peut pousser ses fichiers toutes les 5 minutes par SSH
vers un partage du professeur : voir `deploy/systemd/aristote-rsync.service` et `.timer`.
