# Installation logicielle

## Kiosque (Raspberry Pi 5)

### 1. Système

1. Avec **Raspberry Pi Imager**, écrire **Raspberry Pi OS Lite (64 bits, Bookworm)** directement sur le SSD
   (adaptateur USB-NVMe), ou sur une carte microSD pour la variante économique.
2. Dans les réglages d'Imager : nom d'hôte provisoire, utilisateur administrateur, **clé SSH**, Wi-Fi de
   l'établissement, fuseau horaire `Europe/Paris` (ou `Europe/Brussels`), clavier.
3. Démarrer le Pi. Avec un SSD, si le Pi ne démarre pas dessus :
   `sudo rpi-eeprom-config --edit` → `BOOT_ORDER=0xf416`.

### 2. Aristote

```bash
sudo apt update && sudo apt install -y git
git clone https://github.com/dimiphoton/teaching-aide-Aristotre-4-all.git
cd teaching-aide-Aristotre-4-all
sudo ./deploy/install.sh
```

Le script installe les paquets, crée l'utilisateur `aristote`, l'environnement Python, le modèle de dictée,
compile l'interface, installe les services et le pare-feu. Il peut être relancé après une mise à jour
(`git pull && sudo ./deploy/install.sh`).

### 3. Personnaliser le kiosque

```bash
sudo ./deploy/provision_kiosk.sh --id K03 --students E09,E10,E11,E12 \
     --teacher-device <ID-SYNCTHING-DU-PROFESSEUR> --pin 4821
```

- `--students` : 4 pseudonymes, dans l'ordre des boutons 1 à 4. **Jamais de vrais noms.**
- `--teacher-device` : identifiant Syncthing du PC du professeur (voir le guide professeur).
- `--lan-only` : interdit les relais Syncthing par Internet.

### 4. Choisir le mode IA

Éditer `/etc/aristote/config.toml` :

- **Mode UE (par défaut)** : mettre la clé dans `/etc/aristote/secrets.env` (`MISTRAL_API_KEY=…`).
- **Mode 100 % local** : installer le hub de classe ([`deploy/hub/README.md`](../deploy/hub/README.md)), puis
  renseigner `base_url = "http://hub.local:11434/v1"` dans `[llm]` et `[ocr]` (`engine = "vlm"`).
- **Démonstration sans réseau** : `[tutor] offline_demo = true` (correction déterministe uniquement).

Choisir le cours : `[tutor] curriculum = "/etc/aristote/cours/mon-cours.yaml"` (format :
[`DATA_FORMAT.md`](DATA_FORMAT.md)). Sans cours, le cours de démonstration multi-matières est utilisé.

```bash
sudo systemctl restart aristote-backend
aristote diag printer && aristote diag camera
sudo reboot     # l'interface démarre en plein écran
```

### 5. Exploitation

| Besoin | Commande |
|---|---|
| Journaux du serveur | `journalctl -u aristote-backend -f` |
| Redémarrer l'interface | `sudo systemctl restart aristote-kiosk` |
| Configuration effective | `aristote config` |
| Diagnostic à l'écran | appui long (3 s) sur le titre « Aristote » de l'écran d'accueil, puis code PIN |
| Mise à jour | `cd teaching-aide-Aristotre-4-all && git pull && sudo ./deploy/install.sh` |

## Poste de développement (sans matériel)

```bash
make venv          # environnement Python + dépendances de test
make frontend      # compile l'interface (Node 18+)
make test          # tests du backend et du harnais d'évaluation
make dev           # kiosque simulé : http://127.0.0.1:8000
```

En mode simulé (`ARISTOTE_MOCK=1`), la caméra renvoie une page de test, l'imprimante affiche ses tickets dans les
journaux, les boutons sont remplacés par les touches F13 à F17 ou par un clic sur les badges, et le tuteur
utilise le LLM de démonstration. Pour l'interface en rechargement à chaud : `cd frontend && npm run dev`.
