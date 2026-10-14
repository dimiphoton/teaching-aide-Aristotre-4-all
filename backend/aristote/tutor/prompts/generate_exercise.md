Tu crées un court exercice de remédiation imprimé sur un ticket de caisse (32 caractères par ligne),
pour un élève de niveau ${niveau} en ${matiere}.

- Notion travaillée : ${notion}
- Prérequis à consolider : ${prerequis}
- Erreur de raisonnement observée : ${misconception}
- Exercice sur lequel l'élève a bloqué (NE PAS le reprendre, NE PAS en donner la solution) : ${question}

Contraintes :
- 2 à 3 questions très courtes, progressives, qui travaillent le prérequis et font apparaître l'erreur
  de raisonnement par un exemple simple ou concret.
- Aucune question ne doit permettre de lire directement la réponse de l'exercice bloqué.
- Texte simple, sans Markdown ni LaTeX ; utilise « / » pour les fractions et « x » pour les multiplications.

Produis uniquement un objet JSON :
{"titre": "<5 mots max>", "consigne": "<1 phrase>", "questions": ["...", "..."]}
