# Hub IA de classe (mode 100 % local)

Un seul ordinateur de la salle fait tourner le modèle de langage et le modèle de vision (OCR manuscrit) pour
tous les kiosques. Aucune donnée d'élève ne quitte l'établissement.

## Matériel

| Option | Modèles conseillés | Remarque |
|---|---|---|
| PC + GPU NVIDIA 12 Go (RTX 3060 12 Go d'occasion) | `qwen2.5:14b-instruct` (Q4) + `qwen2.5vl:7b` | Le plus économique |
| Mac mini M4 24 Go | idem, via Ollama natif (`brew install ollama`) | Silencieux, peu gourmand |

## Installation (PC Linux + Docker)

```bash
cd deploy/hub
docker compose up -d
docker compose exec ollama ollama pull qwen2.5:14b-instruct
docker compose exec ollama ollama pull qwen2.5vl:7b
sudo apt install avahi-daemon && sudo hostnamectl set-hostname hub   # nom réseau hub.local
```

## Configuration des kiosques

Dans `/etc/aristote/config.toml` :

```toml
[llm]
base_url = "http://hub.local:11434/v1"
model = "qwen2.5:14b-instruct"
api_key_env = ""

[ocr]
engine = "vlm"
base_url = "http://hub.local:11434/v1"
model = "qwen2.5vl:7b"
api_key_env = ""
```

Puis `sudo systemctl restart aristote-backend` et vérifier l'écran de diagnostic (ligne « llm »).

## Choisir les modèles

Les modèles ne se choisissent pas au jugé : comparer les candidats avec le harnais d'évaluation
(`make eval`, voir `docs/EVALUATION.md`). Un modèle qui laisse fuir une seule réponse (critère G1) est écarté.
