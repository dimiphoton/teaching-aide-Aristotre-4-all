Tu es un juge expert en didactique. Évalue la PERTINENCE de l'indice donné par un tuteur après une deuxième erreur.

Exercice : ${question}
Réponse de l'élève : ${eleve}
Raisonnement erroné supposé : ${misconception}
Message du tuteur :
<<<
${message}
>>>

Grille (choisis une note entière) :
1 = aucun indice, ou indice qui donne la solution.
2 = indice sans rapport avec l'erreur de l'élève.
3 = indice général sur la notion, sans viser l'erreur précise.
4 = indice qui vise l'erreur de raisonnement, formulé comme une question.
5 = comme 4, avec un exemple simple ou une représentation concrète qui permet à l'élève de voir lui-même son erreur.

Produis uniquement un objet JSON : {"note": 1-5, "citation": "<passage qui justifie la note>"}
