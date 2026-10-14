# Harnais d'évaluation

Met en œuvre `docs/EVALUATION.md` : comparer deux versions (modèle, prompts, moteur OCR, matériel) avec des
critères éliminatoires et un score pondéré.

## Commandes

| Commande | Ce qu'elle fait | Réseau |
|---|---|---|
| `make eval-offline` | Toute la chaîne avec le LLM de démonstration : vérifie G1 (fuites), G2 (verrou), G4/G5 (tests) | non |
| `make eval CONFIG=eval/configs/x.toml` | Évaluation complète : tuteur réel, élève simulé, jury | oui |
| `make eval-compare A=… B=…` | Rapport comparatif Markdown entre deux `results.json` | non |
| `python -m eval.teacher_eval --config …` | Évalue les 3 prompts du professeur sur la classe synthétique | oui |
| `python -m eval.ocr_eval --corpus … --baseline` | OCR et dictée sur le corpus réel collecté par les kiosques | selon moteur |
| `python -m eval.bench.latency --url …` | Délais mesurés sur un kiosque | réseau local |
| `python -m eval.bench.soak --hours 72` | Endurance 72 h | réseau local |
| `python -m eval.generators.synthetic_class -o dossier` | Génère la classe synthétique (30 élèves, vérité dans `verite.json`) | non |
| `python -m eval.generators.misconceptions …` | Complète par LLM les catalogues de misconceptions vides d'un cours | oui |

## Comparer deux versions : exemple

```bash
make eval CONFIG=eval/configs/mistral.toml       # → eval/results/<date>_mistral/results.json
make eval CONFIG=eval/configs/hub-qwen14b.toml   # → eval/results/<date>_hub-qwen14b/results.json
make eval-compare A=eval/results/…_mistral/results.json B=eval/results/…_hub-qwen14b/results.json
```

Le rapport indique pour chaque critère la valeur, la note sur 100 et la version gagnante. Une version qui
échoue à un critère éliminatoire est **REJETÉE** quel que soit son score.

## Compléter les blocs non mesurés par `make eval`

`make eval` mesure le tuteur. Les autres blocs viennent de mesures séparées, référencées dans la section
`[mesures]` de la configuration :

- **lecture** : `python -m eval.ocr_eval --corpus <export> --kiosk-config <config> -o eval/results/lecture.json`
  (corpus obtenu avec `eval_capture = true` sur un kiosque puis `aristote eval-export`) ;
- **délais** : `python -m eval.bench.latency --url http://127.0.0.1:8000 -o eval/results/delais.json` sur le kiosque ;
- **coût** : `cout_euros_par_eleve_an` (matériel amorti sur 4 ans + API + papier).

Un bloc non mesuré est exclu du score (et signalé dans le rapport) ; les poids restants sont renormalisés.

## Fiabilité du jury

- Les vérifications déterministes passent avant le jury (verdict, fuite, compteur).
- Pour les fuites (G1) et la sécurité (G3), un seul juge qui signale un problème suffit.
- Pour les notes 1-5, si le kappa pondéré entre juges est inférieur à 0,6, le critère est marqué
  « non fiable » et exclu du score. Avec un seul juge, ces critères sont toujours « non fiables ».
