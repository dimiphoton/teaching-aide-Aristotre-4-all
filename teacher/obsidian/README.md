# Coffre Obsidian du professeur

Ce dossier est un modèle de coffre (*vault*) Obsidian. Copiez son contenu dans votre coffre (ou ouvrez-le
directement comme coffre), puis reliez les kiosques avec Syncthing (`deploy/syncthing/setup_teacher.md`).

```
Aristote/
├── _Correspondance-eleves.md   # pseudonymes ↔ noms : reste ICI, n'est jamais synchronisé ni envoyé à une IA
├── Tableau-de-bord.md          # requêtes Dataview
├── Kiosques/                   # cible Syncthing (lecture seule) : un sous-dossier par kiosque
└── Analyses/                   # notes de données et résultats des prompts
prompts/                        # 3 prompts Text Generator
templates/                      # Templater : préparation des données ; modèle de rapport
```

## 1. Plugins à installer

*Paramètres → Modules complémentaires → Parcourir* :

| Plugin | Rôle | Réglage |
|---|---|---|
| **Dataview** | Tableau de bord | activer *Enable JavaScript Queries* |
| **Templater** | Prépare la note de données à analyser | *Template folder location* : `templates` |
| **Text Generator** | Lance les prompts sur la note de données | *Templates path* : `prompts` ; choisir le fournisseur LLM |
| **Smart Connections** *(facultatif)* | Recherche sémantique et discussion avec le coffre | exclure `Aristote/_Correspondance-eleves.md` |

### Fournisseur LLM de Text Generator : confidentialité

Les données envoyées sont pseudonymisées, mais ce sont des productions d'élèves mineurs. Par ordre de préférence :

1. **Ollama du hub de classe** (*Custom / OpenAI-compatible*, URL `http://hub.local:11434/v1`) : rien ne quitte l'établissement ;
2. **Mistral** (hébergement UE) ;
3. tout autre fournisseur seulement si l'établissement l'a validé.

## 2. Analyser en 3 étapes

1. **Préparer les données** : palette de commandes → *Templater: Create new note from template* →
   `Preparer-donnees-analyse` → choisir la période (14 jours par défaut). Une note
   `Aristote/Analyses/Données AAAA-MM-JJ (14 j)` est créée : texte brut, pseudonymisé, structure du cours incluse.
2. **Lancer un prompt** : ouvrir cette note, placer le curseur à la fin, palette → *Text Generator: Templates:
   Generate & Insert* → choisir l'un des trois prompts.
3. **Décider** : reporter les conclusions dans une note créée depuis `templates/Rapport-hebdomadaire.md`.

| Prompt | Question à laquelle il répond |
|---|---|
| `01-misconceptions-par-notion` | Quelles notions la classe comprend-elle mal, et quels raisonnements erronés l'expliquent ? |
| `02-clusters-eleves-en-difficulte` | Quels élèves regrouper pour la remédiation, autour de quelle difficulté commune ? |
| `03-verification-prerequis` | Les échecs viennent-ils de prérequis non maîtrisés ? Le graphe de prérequis du cours est-il juste ? |

> Si votre version de Text Generator ne reconnaît pas `{{content}}`, sélectionnez tout le texte de la note
> de données et remplacez `{{content}}` par `{{selection}}` dans le prompt. Les prompts fonctionnent aussi par
> simple copier-coller dans n'importe quel assistant (y compris Smart Connections Chat).

## 3. Bonnes pratiques

- Les sorties de l'IA sont des **hypothèses** : chaque conclusion cite ses extraits ; vérifiez-les avant d'agir.
- Remplacez les pseudonymes par les noms **uniquement** dans vos notes de décision, jamais dans les notes de données.
- Ajoutez au cours les misconceptions marquées 🆕 si elles sont pertinentes : les analyses suivantes seront plus précises.
