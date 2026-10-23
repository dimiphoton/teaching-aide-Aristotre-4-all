# Guide du professeur

## En classe

- **4 élèves par kiosque.** Chaque élève a son bouton de couleur (1 rouge, 2 bleu, 3 vert, 4 jaune) : un appui
  ouvre sa session. Un appui long (3 s) sur son bouton, ou « J'ai fini », la ferme. Une session est aussi fermée
  après 10 minutes sans activité.
- **Répondre** :
  - **écrire** au clavier de l'écran ;
  - **scanner** sa copie : poser la feuille dans la zone de scan et appuyer sur SCAN, puis relire et corriger le
    texte lu avant de valider ;
  - **dicter** sa réponse : même relecture avant validation.
- **Le tuteur ne donne jamais la réponse** :
  - 1re erreur : une question pour faire relire le raisonnement ;
  - 2e erreur : un indice ciblé ;
  - 3e erreur : l'exercice s'arrête et un **ticket de révision** s'imprime, à agrafer dans le cahier
    (agrafeuse sans agrafe dans la station). L'exercice est signalé « à revoir » dans votre tableau de bord.
- **Imprimer** : le bouton 🖨️ imprime la question en cours sur un ticket ; l'élève répond dessus puis le scanne.

## Mise en route (une fois)

1. **Obsidian** : copier le dossier [`teacher/obsidian/`](../teacher/obsidian/README.md) dans votre coffre et
   installer les plugins Dataview, Templater et Text Generator (détails dans son README).
2. **Correspondance** : remplir `Aristote/_Correspondance-eleves.md` (pseudonyme → nom). Ce fichier ne quitte
   jamais votre ordinateur.
3. **Syncthing** : suivre [`deploy/syncthing/setup_teacher.md`](../deploy/syncthing/setup_teacher.md). Donner
   votre identifiant Syncthing à la personne qui installe les kiosques, puis accepter chaque kiosque en
   « Recevoir seulement » dans `Aristote/Kiosques/<K>`.
4. **Cours** : écrire votre cours en YAML ([`DATA_FORMAT.md`](DATA_FORMAT.md)) ou partir du cours de démonstration.

## Chaque semaine

1. Ouvrir **`Aristote/Tableau-de-bord`** :
   - exercices à revoir ;
   - misconceptions fréquentes ;
   - réussite par notion ;
   - activité par élève ;
   - notions fragiles ;
   - état des kiosques.
2. **Préparer les données** : commande *Templater: Create new note from template* →
   `Preparer-donnees-analyse` → période (7 ou 14 jours).
3. **Lancer les prompts** sur la note de données (*Text Generator: Generate & Insert*) :

   | Prompt | Question |
   |---|---|
   | 01 Misconceptions par notion | Qu'est-ce que la classe comprend mal, et pourquoi ? |
   | 02 Groupes d'élèves en difficulté | Qui regrouper pour la remédiation, autour de quelle difficulté ? |
   | 03 Vérification des prérequis | Les échecs viennent-ils de prérequis non maîtrisés ? Mon graphe de prérequis est-il juste ? |

4. **Décider** dans une note `Rapport-hebdomadaire` : activité en classe entière, groupes de besoin, élèves à
   voir individuellement, misconceptions 🆕 à ajouter au cours.

> Les analyses de l'IA sont des hypothèses : elles citent leurs extraits, vérifiez-les avant d'agir.

## Faire évoluer le cours

- Ajouter les misconceptions 🆕 pertinentes au catalogue de la notion concernée.
- Corriger les prérequis signalés comme incohérents par le prompt 03.
- Déposer le nouveau fichier sur chaque kiosque (`/etc/aristote/cours/`) et redémarrer le service.
  Les fichiers `cours.md` du coffre se mettent à jour automatiquement.
