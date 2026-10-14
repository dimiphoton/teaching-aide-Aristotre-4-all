# Confidentialité et RGPD

Les utilisateurs sont des **élèves mineurs**. Ce document décrit ce que le kiosque collecte, où vont les
données, et les réglages à faire valider par l'établissement (chef d'établissement, délégué à la protection des
données). Il ne remplace pas l'analyse juridique de l'établissement, qui reste responsable du traitement.

## 1. Données traitées

| Donnée | Où | Durée par défaut | Réglage |
|---|---|---|---|
| Pseudonyme de l'élève (`E07`) | kiosque, Obsidian du professeur | année scolaire | — |
| Correspondance pseudonyme ↔ nom | **uniquement** `_Correspondance-eleves.md` dans Obsidian | année scolaire | jamais synchronisée |
| Réponses (texte), verdicts, misconceptions, diagnostics | kiosque → Obsidian (Syncthing) | année scolaire | — |
| Photo de la copie | mémoire vive du kiosque, le temps de la relecture | supprimée à la validation | `keep_scans`, `eval_capture` |
| Enregistrement de la voix | mémoire vive du kiosque, le temps de la relecture | supprimé à la validation | `eval_capture` |
| Corpus d'évaluation (image/voix + texte) | kiosque, hors dossier synchronisé | 90 jours | `eval_capture = false` par défaut |

Il n'y a **aucun compte élève**, **aucune photo de visage** (la caméra pointe vers la table) et **aucun
identifiant réseau** associé à l'élève.

## 2. Pseudonymisation

- Les kiosques ne connaissent que des pseudonymes (`deploy/provision_kiosk.sh` refuse tout autre format).
- La table de correspondance reste dans le coffre Obsidian du professeur. Le tableau de bord Dataview affiche
  les noms **localement**.
- Les notes de données envoyées aux prompts d'analyse sont **pseudonymisées**.

## 3. Où partent les données ? Choix de l'établissement

| Traitement | Mode « 100 % local » | Mode « UE » (par défaut) |
|---|---|---|
| Tuteur (LLM) | Ollama sur le hub de classe | API Mistral (hébergée dans l'UE) |
| Lecture des copies (OCR) | modèle de vision sur le hub de classe | API Mistral OCR |
| Dictée | faster-whisper **sur le kiosque** | faster-whisper **sur le kiosque** |
| Synchronisation | Syncthing en réseau local (`--lan-only`) | Syncthing (relais Internet possible, chiffré) |
| Analyses du professeur | Text Generator → Ollama du hub | Text Generator → Mistral |

En mode UE, ce qui est envoyé à l'API : le texte de l'exercice, les réponses de l'élève (pseudonymisées, sans
nom), et l'image de la copie pour l'OCR. Demander à l'établissement de vérifier les conditions du fournisseur :
contrat de sous-traitance (article 28 du RGPD), hébergement, et option de **non-rétention**
(*zero data retention*) quand elle est disponible.

## 4. Sécurité

- Le serveur du kiosque n'écoute que sur `127.0.0.1` ; le pare-feu n'ouvre que SSH et Syncthing.
- Les clés d'API sont dans `/etc/aristote/secrets.env` (droits 640) ; elles ne sont jamais dans le dépôt ni dans le coffre.
- L'écran de diagnostic est protégé par un code PIN (`[admin] pin`, **à changer**).
- Le service tourne sous un utilisateur dédié, avec un système de fichiers en lecture seule hors de `/var/lib/aristote`.
- Garde-fous du tuteur :
  - il refuse les dérives hors sujet et les provocations ;
  - aucun message ne peut révéler la réponse (vérification déterministe avant affichage) ;
  - il ne demande jamais d'information personnelle.

## 5. Droits des personnes

- **Accès / rectification** : toutes les données d'un élève sont dans `Aristote/Kiosques/*/eleves/<pseudo>/`.
- **Effacement** : supprimer ce dossier sur le kiosque (`/var/lib/aristote/vault/<K>/eleves/<pseudo>/`) ;
  Syncthing propage la suppression vers Obsidian. Supprimer ensuite la ligne de correspondance.
- **Fin d'année** : archiver le coffre selon la politique de l'établissement, puis vider
  `/var/lib/aristote/vault/` et `/var/lib/aristote/eval_corpus/` sur chaque kiosque.

## 6. Points à faire valider avant la mise en service

- [ ] Inscription du traitement au registre de l'établissement ; information des familles.
- [ ] Choix du mode (100 % local ou UE) et, en mode UE, validation du fournisseur.
- [ ] Code PIN d'administration changé sur chaque kiosque.
- [ ] `eval_capture` laissé désactivé, sauf campagne d'évaluation autorisée et limitée dans le temps.
- [ ] Papier thermique **sans bisphénol** (BPA/BPS) : manipulé par les élèves.
