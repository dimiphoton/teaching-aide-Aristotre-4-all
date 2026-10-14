# Architecture — Aristote 4 All

> Kiosque éducatif de bureau : tuteur IA socratique partagé par 4 élèves, avec scan de copies manuscrites,
> impression d'exercices sur ticket thermique et remontée automatique des données vers l'Obsidian du professeur.

## 1. Vue d'ensemble

```
                         SALLE DE CLASSE (réseau local / Wi-Fi école)
 ┌──────────────────────── KIOSQUE ×7-8 (1 par groupe de 4 élèves) ────────────────────────┐
 │                                                                                          │
 │  [4 boutons élèves + 1 bouton SCAN] ──GPIO──┐                                            │
 │  [Caméra Module 3 (CSI)] ───────────────────┤                                            │
 │  [Micro USB] ───────────────────────────────┤      Raspberry Pi 5 (8 Go) + SSD NVMe      │
 │  [Écran tactile 10,1" HDMI + USB] ──────────┤   ┌────────────────────────────────────┐   │
 │  [Imprimante CSN-A2] ──USB-TTL──────────────┘   │ Chromium (mode kiosque, Wayland)   │   │
 │                                                 │   └─ Frontend Vue 3 (statique)     │   │
 │                                                 │        ▲ HTTP + WebSocket          │   │
 │                                                 │ Backend FastAPI (Python 3.11)      │   │
 │                                                 │   ├─ hardware/ (GPIO, caméra,      │   │
 │                                                 │   │   imprimante, micro)           │   │
 │                                                 │   ├─ ocr/   (moteurs enfichables)  │   │
 │                                                 │   ├─ stt/   (faster-whisper local) │   │
 │                                                 │   ├─ tutor/ (agent socratique)     │   │
 │                                                 │   └─ storage/ (Markdown + YAML)    │   │
 │                                                 │            │                       │   │
 │                                                 │   /var/lib/aristote/vault/  ◄──────┼───┼── Syncthing (envoi seul)
 │                                                 └────────────────────────────────────┘   │
 └──────────────────────────────────────────────────────────────────────────────────────────┘
           │ API compatible OpenAI (HTTPS)                                 │ Syncthing (chiffré TLS, LAN)
           ▼                                                               ▼
 ┌───────────────────────────────┐                     ┌─────────────────────────────────────────┐
 │ Fournisseur LLM / OCR, au choix│                    │ PC du professeur                        │
 │  A. Mistral (API UE)           │                    │  Obsidian vault/                        │
 │  B. Ollama sur un « hub »      │                    │   └─ Aristote/Kiosques/<kiosk-id>/...   │
 │     de classe (LAN, 100 % local)│                   │  Plugins : Dataview, Text Generator,    │
 └───────────────────────────────┘                     │  Smart Connections + prompts fournis   │
                                                       └─────────────────────────────────────────┘
```

### Principes directeurs

1. **Le kiosque fonctionne hors ligne** pour tout ce qui est matériel et stockage ; seul l'appel au LLM nécessite le réseau
   (Internet pour Mistral, ou seulement le LAN pour Ollama).
2. **La logique pédagogique critique est déterministe** : le compteur d'erreurs, le verrou « pas de réponse après 3 erreurs »
   et la journalisation sont gérés en Python, jamais confiés au LLM. Le LLM ne fait que *produire* du texte et une
   *évaluation structurée* (JSON) que le code valide.
3. **Le Markdown est la base de données.** Pas de SGBD : des fichiers `.md` avec en-tête YAML, lisibles par un humain,
   interrogeables par Dataview, synchronisables par Syncthing.
4. **Pseudonymisation par défaut (RGPD, élèves mineurs).** Les kiosques ne connaissent que des pseudonymes (`E07`).
   La table de correspondance pseudonyme ↔ nom reste uniquement dans le coffre Obsidian du professeur.
5. **Matériel abstrait derrière des interfaces** : chaque périphérique a une implémentation réelle et une implémentation
   factice (`mock`) → le logiciel se développe et se teste sur n'importe quel PC.

## 2. Choix techniques et justification

| Sujet | Choix | Pourquoi | Alternative documentée |
|---|---|---|---|
| Calcul | **Raspberry Pi 5 – 8 Go** + SSD NVMe | GPIO natifs (boutons/LED), port caméra CSI (meilleure qualité/prix pour scanner une page), écosystème éducatif, ~85 €, très facile à sourcer, 7 W | Mini-PC Intel N100 16 Go : plus puissant (OCR manuscrit local possible), mais sans GPIO ni CSI → boutons via RP2040 en clavier USB, webcam USB |
| Système | Raspberry Pi OS Bookworm 64 bits (Lite) + `cage` (compositeur Wayland kiosque) + Chromium | Démarrage direct sur l'appli, pas de bureau à administrer | — |
| Backend | Python 3.11, **FastAPI** + Uvicorn, WebSocket | Bibliothèques matérielles Python (gpiozero, picamera2, pyserial), asynchrone | — |
| Frontend | **Vue 3 + Vite**, compilé en statique et servi par FastAPI | Léger, simple à maintenir par un enseignant/dev | — |
| Boutons | `gpiozero` (backend `lgpio`, compatible Pi 5) | Anti-rebond intégré, simple | Clavier HID (touches F13-F17) pour N100 |
| Caméra | `picamera2` (libcamera), capture 12 MP + correction de perspective OpenCV | Autofocus du Camera Module 3, net sur une page A4 | OpenCV `VideoCapture` (webcam USB) |
| Imprimante | Pilote Python maison pour CSN-A2 (sous-ensemble ESC/POS) via `pyserial` sur adaptateur USB-TTL | Pas de dépendance fragile ; contrôle de la vitesse/chauffe ; même câblage sur Pi ou N100 | UART GPIO14/15 du Pi |
| Voix → texte | **faster-whisper** (`base`, int8) en local | Confidentialité ; ~1× temps réel sur Pi 5 pour des réponses courtes | — |
| OCR | Moteurs enfichables : `tesseract` (local, texte imprimé), `ollama_vlm` (VLM sur hub LAN, manuscrit), `mistral` (API Mistral OCR, UE) | Le manuscrit est mal lu par Tesseract → on laisse le choix confidentialité/qualité à l'établissement | `florence2` local sur N100 |
| LLM | Client **compatible OpenAI** unique → Mistral (`mistral-small-latest`) ou Ollama (`qwen2.5:7b-instruct`, etc.) | Un seul code, deux modes de confidentialité | Tout serveur compatible OpenAI |
| Synchronisation | **Syncthing** (dossier « Envoyer seulement » côté kiosque, « Recevoir seulement » côté prof) | Pair-à-pair, chiffré, tolère les coupures, aucun serveur, aucun conflit (chaque kiosque écrit dans son sous-dossier) | `rsync` via `systemd timer` + SSH (script fourni) |

## 3. Arborescence du dépôt

```
teaching-aide-Aristotre-4-all/
├── README.md                     # Présentation, montage, installation, avertissement licence
├── LICENSE.md                    # Texte officiel PolyForm Noncommercial 1.0.0
├── NOTICE                        # « Required Notice » (copyright)
├── Makefile                      # make dev | make build | make test | make deploy
│
├── docs/
│   ├── ARCHITECTURE.md           # Ce document
│   ├── ASSEMBLY.md               # Montage mécanique et câblage pas à pas
│   ├── INSTALL.md                # Installation logicielle d'un kiosque
│   ├── TEACHER_GUIDE.md          # Guide professeur : Obsidian, Syncthing, prompts
│   ├── PRIVACY.md                # RGPD, pseudonymisation, choix OCR/LLM, rétention
│   ├── EVALUATION.md             # Critères et protocole de comparaison des versions
│   └── DATA_FORMAT.md            # Spécification des fichiers Markdown produits
│
├── hardware/
│   ├── BOM.md                    # Liste du matériel
│   ├── wiring.md                 # Brochage GPIO, schéma d'alimentation
│   └── enclosure/                # Boîtier imprimé 3D (OpenSCAD paramétrique)
│       ├── params.scad           # Cotes : écran, imprimante, boutons, agrafeuse, dévidoir
│       ├── base.scad             # Socle (Pi, alim, imprimante, logements passifs)
│       ├── screen_frame.scad     # Cadre écran incliné
│       ├── camera_arm.scad       # Potence caméra au-dessus de la zone de scan
│       ├── button_panel.scad     # Façade 5 boutons
│       └── README.md             # Réglages d'impression (PETG, 0,2 mm, supports)
│
├── backend/
│   ├── pyproject.toml
│   ├── config.example.toml       # Copié en /etc/aristote/config.toml
│   ├── aristote/
│   │   ├── __init__.py
│   │   ├── main.py               # App FastAPI, montage du frontend, cycle de vie
│   │   ├── config.py             # Chargement TOML + variables d'environnement (pydantic-settings)
│   │   ├── events.py             # Bus d'événements interne → WebSocket
│   │   ├── api/
│   │   │   ├── routes_session.py # Utilisateur actif, début/fin de session
│   │   │   ├── routes_tutor.py   # Échanges avec le tuteur
│   │   │   ├── routes_scan.py    # Capture + OCR
│   │   │   ├── routes_print.py   # Impression d'exercices
│   │   │   └── ws.py             # WebSocket (boutons, statut, progression)
│   │   ├── hardware/
│   │   │   ├── base.py           # Interfaces abstraites (Protocol)
│   │   │   ├── buttons.py        # GPIO (gpiozero) | clavier HID | mock
│   │   │   ├── leds.py           # LED des boutons (élève actif)
│   │   │   ├── camera.py         # picamera2 | OpenCV | mock + redressement de page
│   │   │   ├── printer_csn_a2.py # Pilote CSN-A2 (texte, gras, tailles, QR, coupe-ligne)
│   │   │   └── microphone.py     # Enregistrement (sounddevice) | mock
│   │   ├── ocr/
│   │   │   ├── base.py
│   │   │   ├── tesseract_engine.py
│   │   │   ├── ollama_vlm_engine.py
│   │   │   └── mistral_engine.py
│   │   ├── stt/
│   │   │   └── whisper_engine.py
│   │   ├── tutor/
│   │   │   ├── prompts/
│   │   │   │   ├── system_tutor.md        # Prompt système du tuteur socratique
│   │   │   │   ├── evaluate_answer.md     # Évaluation structurée (JSON) d'une réponse
│   │   │   │   └── generate_exercise.md   # Génération d'exercice imprimable
│   │   │   ├── llm_client.py     # Client compatible OpenAI (Mistral / Ollama)
│   │   │   ├── state.py          # Machine à états par item (tentatives, verrou)
│   │   │   ├── agent.py          # Orchestration : évaluer → décider → formuler
│   │   │   ├── misconceptions.py # Catalogue et normalisation des étiquettes d'erreurs
│   │   │   └── curriculum/       # Cours génériques (toutes matières) éditables par le prof
│   │   │       ├── schema.py     # Notions, prérequis, items, type_reponse, misconceptions
│   │   │       └── loader.py
│   │   ├── storage/
│   │   │   ├── markdown_store.py # Écriture atomique des sessions/items en Markdown
│   │   │   └── students.py       # Profils pseudonymisés par kiosque
│   │   └── services/
│   │       └── session_manager.py # Bascule d'élève, sauvegarde, inactivité
│   └── tests/
│       ├── test_state_machine.py
│       ├── test_printer_encoding.py
│       ├── test_markdown_store.py
│       └── test_agent_mocked_llm.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.ts
│       ├── App.vue
│       ├── api.ts                # Client REST + WebSocket
│       ├── stores/session.ts     # État (Pinia) : élève actif, conversation
│       ├── views/
│       │   ├── HomeView.vue      # « Appuie sur ton bouton »
│       │   ├── TutorView.vue     # Conversation, saisie, dictée
│       │   ├── ScanView.vue      # Aperçu caméra, cadrage, résultat OCR à valider
│       │   └── AdminView.vue     # Diagnostic matériel (code PIN)
│       └── components/
│           ├── StudentBadge.vue
│           ├── ChatBubble.vue
│           ├── OnScreenKeyboard.vue
│           ├── AttemptMeter.vue  # Jauge 1-2-3 tentatives
│           └── MathInput.vue
│
├── deploy/
│   ├── install.sh                # Installation complète d'un kiosque (idempotent)
│   ├── provision_kiosk.sh        # Nom du kiosque, élèves, appairage Syncthing
│   ├── systemd/
│   │   ├── aristote-backend.service
│   │   ├── aristote-kiosk.service          # cage + Chromium
│   │   ├── aristote-rsync.service          # Alternative à Syncthing
│   │   └── aristote-rsync.timer
│   ├── udev/99-aristote-printer.rules      # /dev/aristote-printer stable
│   ├── syncthing/setup_kiosk.sh
│   ├── syncthing/setup_teacher.md
│   └── hub/                      # Optionnel : serveur Ollama de classe
│       ├── docker-compose.yml
│       └── README.md
│
├── eval/                         # Harnais d'évaluation (voir docs/EVALUATION.md)
│   ├── weights.toml
│   ├── courses/demo/             # Cours de démonstration multi-matières
│   ├── generators/               # Misconceptions, scénarios, classe synthétique
│   ├── simulated_student.py
│   ├── checks/                   # Vérifications déterministes (réponse, fuite, CER/WER)
│   ├── judges/                   # Jury multi-LLM + grilles
│   ├── bench/                    # Délais, endurance
│   ├── run.py
│   └── report.py
│
└── teacher/
    └── obsidian/
        ├── README.md                         # Installation des plugins et du coffre
        ├── Aristote/
        │   ├── _Correspondance-eleves.md     # Pseudonyme ↔ nom (ne JAMAIS synchroniser vers les kiosques)
        │   ├── Tableau-de-bord.md            # Requêtes Dataview
        │   └── Kiosques/                     # Cible Syncthing (lecture seule)
        ├── prompts/
        │   ├── 01-misconceptions-par-notion.md
        │   ├── 02-clusters-eleves-en-difficulte.md
        │   └── 03-verification-prerequis.md
        └── templates/
            └── Rapport-hebdomadaire.md
```

## 4. Flux principaux

### 4.1 Bascule d'élève
1. Appui sur le bouton n°k → `buttons.py` publie `student.selected(k)` sur le bus.
2. `session_manager` clôture la session de l'élève précédent (écriture Markdown), ouvre celle de l'élève k,
   allume la LED k, diffuse l'événement au frontend par WebSocket.
3. Appui long (3 s) sur le bouton actif → fin de session (« Au revoir »). Inactivité de 10 min → fin automatique.

### 4.2 Item pédagogique (cœur du tuteur)

```
            ┌─────────────┐  réponse élève (texte, dictée ou scan OCR)
            │ EN_COURS    │────────────────────────────────┐
            │ tentatives=0│                                ▼
            └─────────────┘                    LLM evaluate_answer → JSON
                   ▲                           {verdict, misconception, indice_niveau}
                   │ juste                                 │
           ┌───────┴──────┐        partiel/faux           ▼
           │ VALIDÉ       │◄── juste ── tentatives += 1 (si faux)
           │ → item suiv. │              │
           └──────────────┘              ├─ tentatives = 1 → relance socratique (question ouverte)
                                         ├─ tentatives = 2 → indice ciblé sur la misconception
                                         └─ tentatives = 3 → VERROUILLÉ
                                               • la réponse n'est JAMAIS donnée
                                               • diagnostic de la misconception (journalisé)
                                               • question sur un PRÉREQUIS plus simple
                                               • impression d'un ticket de remédiation
                                               • drapeau `a_revoir_prof: true`
```

Le verdict du LLM est validé par schéma (pydantic). En cas de JSON invalide : une seconde tentative, puis repli sur
« je n'ai pas compris ta réponse, peux-tu reformuler ? » **sans** incrémenter le compteur.

### 4.3 Réponse écrite (scan) ou orale (dictée)
Bouton SCAN (ou écran) → aperçu → capture 12 MP → détection des bords et redressement (OpenCV) → OCR via le moteur
configuré → **l'élève relit et corrige le texte reconnu à l'écran** → la réponse validée entre dans le flux 4.2.
Par défaut, l'image est supprimée après validation (`keep_scans = false`) ; seul le texte est conservé.

Réponse orale : appui sur « Dicter » → enregistrement → transcription locale (faster-whisper) → **l'élève relit et
corrige la transcription** → même flux 4.2. Par défaut, l'audio est supprimé après validation.

Avec l'option `eval_capture = true`, l'image ou l'audio est conservé avec le texte brut du moteur et le texte validé
par l'élève, hors du coffre synchronisé : ces paires servent à évaluer les moteurs OCR et de dictée (voir
`EVALUATION.md` § 5.3).

### 4.4 Synchronisation
Le backend écrit dans `/var/lib/aristote/vault/<kiosk-id>/` (écriture atomique : fichier temporaire + `rename`).
Syncthing partage ce dossier en *Send Only* vers `Obsidian/Aristote/Kiosques/<kiosk-id>/` en *Receive Only* chez le
professeur. Le professeur ne modifie jamais ces fichiers ; ses analyses vont dans d'autres dossiers du coffre.

## 5. Format des données (résumé — détail dans `DATA_FORMAT.md`)

```
<kiosk-id>/
├── eleves/
│   └── E07/
│       ├── profil.md                       # niveau, notions acquises (mis à jour par le kiosque)
│       └── sessions/
│           └── 2026-10-14_1032_E07.md      # une session = un fichier
└── kiosque.md                              # état matériel, version logicielle
```

```markdown
---
type: session
eleve: E07
kiosque: K03
debut: 2026-10-14T10:32:05+02:00
fin: 2026-10-14T10:51:40+02:00
matiere: mathematiques
notions: [fractions-equivalentes, addition-fractions]
items_total: 4
items_valides: 2
items_verrouilles: 1
misconceptions: [additionne-numerateurs-et-denominateurs]
a_revoir_prof: true
---
## Item 1 — addition-fractions — VERROUILLÉ (3/3)
- **Question** : Combien font 1/3 + 1/4 ?
- **Tentative 1** (saisie) : 2/7 → faux · misconception `additionne-numerateurs-et-denominateurs`
- **Tentative 2** (scan OCR, confiance 0.91) : 2/12 → faux · même misconception
- **Tentative 3** (dictée) : 2/7 → faux
- **Diagnostic** : l'élève traite la fraction comme deux entiers indépendants…
- **Remédiation** : ticket imprimé « Partager une pizza en 12 » · prérequis proposé `fractions-equivalentes`
```

## 6. Sécurité et vie privée (résumé — détail dans `PRIVACY.md`)

- Pseudonymes uniquement sur les kiosques ; aucune photo de visage (la caméra pointe vers le bureau).
- Clé API stockée dans `/etc/aristote/secrets.env` (droits `600`), jamais dans le dépôt ni dans le coffre.
- Mode « 100 % local » possible : OCR + LLM sur un hub Ollama de classe, aucune donnée ne quitte l'établissement.
- Mode Mistral : hébergement UE ; activer l'option de non-rétention / zero data retention si l'établissement y a droit.
- Écran d'administration protégé par code PIN ; SSH par clé uniquement.
