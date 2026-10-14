# Formats de données

Deux formats sont à connaître :

1. **le cours** (`curriculum.yaml`), écrit par le professeur et installé sur les kiosques ;
2. **les fichiers produits par les kiosques** (Markdown + en-tête YAML), synchronisés dans Obsidian.

## 1. Écrire un cours

Un cours est un fichier YAML : des **notions** reliées par des **prérequis**. Chaque notion a des **questions**
(items) et un **catalogue de misconceptions** (raisonnements erronés connus). Modèle complet :
[`backend/aristote/tutor/curriculum/demo.yaml`](../backend/aristote/tutor/curriculum/demo.yaml).

```yaml
id: maths-5e-fractions          # identifiant du cours
titre: Les fractions
matiere: mathématiques
niveau: 5e                      # règle le niveau de langue du tuteur
langue: fr
consignes_tuteur: >             # facultatif : consignes ajoutées au prompt du tuteur
  Utilise des exemples de partage (pizzas, tablettes de chocolat).

notions:
  - id: addition-fractions      # minuscules, chiffres, tirets
    titre: Addition de fractions
    prerequis: [fractions-equivalentes]
    misconceptions:
      - id: additionne-numerateurs-et-denominateurs
        description: Additionne les numérateurs entre eux et les dénominateurs entre eux.
    items:
      - id: af-1
        question: "Calcule 1/3 + 1/4."
        type_reponse: nombre
        reponse: "7/12"
        variantes: ["14/24"]
        indices: ["Quelle part de pizza obtiens-tu avec un tiers puis un quart ?"]
        difficulte: 2           # 1 à 3
```

### Types de réponse

Le type de réponse rend le produit utilisable dans toutes les matières. Il permet de **vérifier la réponse** et de
**bloquer toute fuite** sans connaître la matière.

| `type_reponse` | Champs obligatoires | Vérification automatique | Exemple |
|---|---|---|---|
| `nombre` | `reponse` (+ `tolerance` : `"0.01"` ou `"1%"`) | égalité numérique ; accepte 3,5 · 7/12 · 2×10³ · « sept douzièmes » | calcul, conversion |
| `expression` | `reponse` (+ `forme: texte` pour comparer sans calcul symbolique) | équivalence symbolique (SymPy) | 3x + 6, H2O |
| `choix` | `choix` (liste), `reponse` (lettre ou texte de l'option) | égalité | QCM, vrai/faux |
| `mots_cles` | `mots_cles` (synonymes séparés par `|`) | présence de tous les mots-clés, sinon le LLM tranche | date, personnage, vocabulaire |
| `ouverte` | `criteres` (grille de réussite) ; `reponse` = réponse modèle | jugement du LLM selon les critères | justifier, argumenter |

### Bonnes pratiques

- 3 à 6 items par notion, de difficulté croissante.
- Un catalogue de 2 à 4 misconceptions par notion. S'il est vide, `python -m eval.generators.misconceptions`
  peut le proposer (à relire).
- Les **indices** du professeur sont reformulés par le tuteur au 2e essai ; ils ne doivent pas contenir la réponse.
- Vérifier le cours : `aristote --config /etc/aristote/config.toml config` charge et valide tout le fichier
  (prérequis inconnus, cycles, champs manquants).
- Installer : copier le fichier dans `/etc/aristote/cours/`, renseigner `[tutor] curriculum`, puis
  `sudo systemctl restart aristote-backend`.

## 2. Fichiers produits par un kiosque

```
<kiosque>/                         ex. K03/
├── kiosque.md                     état : version, cours, moteurs, périphériques détectés
├── cours.md                       structure du cours (notions, prérequis, misconceptions) — SANS les réponses
└── eleves/
    └── E07/
        ├── profil.md              synthèse de l'élève
        └── sessions/
            └── 2026-10-14_1032_E07.md
```

### Session (`type: session`)

```markdown
---
type: session
eleve: E07
kiosque: K03
statut: terminee            # en_cours | terminee
debut: '2026-10-14T10:32:05+02:00'
fin: '2026-10-14T10:51:40+02:00'
duree_min: 19.6
matiere: mathématiques
notions: [addition-fractions, fractions-equivalentes]
items_total: 2
items_valides: 1
items_verrouilles: 1
tentatives: 4
erreurs: 3
misconceptions: [additionne-numerateurs-et-denominateurs]
a_revoir_prof: true         # au moins un item verrouillé
fin_motif: appui_long       # appui_long | changement_eleve | inactivite | fin_ecran | arret_kiosque
---

# Session E07 — 14/10/2026 10:32

## Item 1 — addition-fractions — VERROUILLÉ (3/3)

**Question** (`af-1`) : Calcule 1/3 + 1/4.

- **Tentative 1** (saisie, 10:33:12) → faux · misconception `additionne-numerateurs-et-denominateurs`
  > 2/7
  - Tuteur : Que représente le 7 dans ta réponse ?
- **Tentative 2** (scan, confiance 0.91, 10:35:40) → faux · misconception `additionne-numerateurs-et-denominateurs`
  > 1/3 + 1/4 = 2/7
  - Texte reconnu avant correction : 1/3 + 1/4 = 2/1
  - Tuteur : …

- **Diagnostic** : Additionne terme à terme, comme pour des entiers.
- **Prérequis proposé** : `fractions-equivalentes`
- **Remédiation** (ticket imprimé) : Parts égales — 1/3 = ?/6 / 1/4 = ?/8
```

Statuts d'item : `VALIDÉ`, `VERROUILLÉ` (3 erreurs), `EN COURS`, `ABANDONNÉ`. Le compteur `(n/3)` compte les
réponses fausses ou partielles ; les demandes d'aide et les réponses hors sujet ne comptent pas.

Le texte des élèves est **neutralisé** avant écriture : les caractères Markdown/Obsidian sont échappés et
`::` devient `: :`. Une réponse d'élève ne peut donc pas créer de tag, de lien ou de champ Dataview.

### Profil (`type: profil`)

```yaml
type: profil
eleve: E07
kiosque: K03
bouton: 3
sessions: 5
derniere_session: '2026-10-14T10:51:40+02:00'
notions_acquises: [fractions-equivalentes]
notions_fragiles: [addition-fractions]     # verrouillées, pas encore revalidées
misconceptions: {additionne-numerateurs-et-denominateurs: 3}
```

Une notion fragile redevient acquise dès que l'élève la valide plus tard sans verrou. Le tuteur propose en
priorité les notions fragiles, puis les nouvelles notions dont les prérequis sont acquis.

### Étiquettes de misconceptions

- Identifiant du catalogue du cours (`additionne-numerateurs-et-denominateurs`) : erreur connue.
- `nouvelle:<identifiant>` : raisonnement identifié par l'IA mais absent du catalogue. Le tableau de bord les
  marque 🆕 ; le professeur peut les ajouter au cours.
