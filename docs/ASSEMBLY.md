# Montage d'un kiosque

Durée : environ 2 h 30 par kiosque, sans compter l'impression 3D (≈ 45 h, voir
[`hardware/enclosure/README.md`](../hardware/enclosure/README.md)).

**Outils** : fer à souder (inserts et plaque ULN), tournevis cruciforme, clé de 5,5 mm, pince coupante,
pied à coulisse, colliers de serrage.

## 0. Avant d'imprimer : mesurer

Les cotes marquées `[À MESURER]` dans [`hardware/enclosure/params.scad`](../hardware/enclosure/params.scad)
dépendent de vos modèles. Mesurez-les au pied à coulisse, corrigez le fichier, puis lancez `./build.sh` pour
régénérer les STL.

| Paramètre | Quoi mesurer |
|---|---|
| `screen_w`, `screen_h`, `screen_t` | largeur, hauteur et épaisseur au bord de l'écran (avec sa coque) |
| `printer_cut`, `printer_depth` | découpe de façade et profondeur du corps de la CSN-A2 (notice du fabricant) |
| `button_d` | diamètre de perçage des boutons arcade (souvent 28 à 30 mm) |
| `stapler_pocket`, `tape_pocket` | largeur, longueur et profondeur souhaitée des logements |
| `usb_panel` | ouverture et entraxe des vis de la rallonge USB |

## 1. Préparer les pièces imprimées

1. Ébavurer, vérifier que les boutons entrent dans les perçages et l'imprimante dans la nacelle.
2. Poser les **inserts M3** au fer à souder (220 °C, pression légère et verticale) :
   - 6 dans le haut des colonnes de chaque coque (12) ;
   - 12 dans les bossages sous les dessus, **par le dessus** (4 supports d'écran, 4 nacelle, 4 mât) ;
   - 2 dans la face droite de la station d'accessoires.

## 2. Électronique

1. **Raspberry Pi 5** : clipser l'Active Cooler, monter le M.2 HAT+ et le SSD (notice du kit), avec le
   connecteur GPIO traversant fourni.
2. Visser le Pi dans la **coque droite** (4 × M2,5), connecteurs USB/Ethernet vers l'arrière.
3. Souder la **plaque ULN2803A** (schéma : [`hardware/wiring.md`](../hardware/wiring.md)) et la visser dans la
   **coque gauche**.
4. Visser l'**embase jack 9 V** dans la paroi arrière droite. Brancher l'adaptateur **CP2102** sur un port USB du
   Pi et le fixer au pont prévu avec un collier.
5. Assembler les deux coques : 4 boulons M3 × 12 + écrous à travers les parois centrales. Les câbles passent par
   la grande ouverture de ces parois.

## 3. Dessus et boutons

1. Clipser les 4 boutons élèves (rouge 1, bleu 2, vert 3, jaune 4) et le bouton **SCAN** (blanc).
2. Câbler chaque bouton : contact NO → GPIO, COM → GND ; LED → ULN2803A et +5 V (voir `wiring.md`).
3. Visser la **rallonge USB du micro** (2 × M3 + écrous) dans le dessus droit.
4. Passer les câbles de l'écran (HDMI, USB) par la fente sous l'écran, et celui de l'imprimante par la fente
   sous la nacelle.
5. Poser les dessus (le rebord centre la pièce) et les visser : 12 × M3 × 8.

## 4. Modules enfichables

1. **Supports d'écran** : 2 × M3 × 10 chacun. Glisser l'écran par le haut dans les rainures ; brancher HDMI et USB.
2. **Nacelle** : la visser (4 × M3 × 10 depuis l'intérieur), passer le câble de l'imprimante dans le trou du fond,
   brancher l'imprimante (alimentation sur l'embase jack, données sur le CP2102), l'encastrer par le haut jusqu'au
   clic, charger le papier (sans BPA).
3. **Mât de caméra** :
   - visser la caméra sous la tête du bras (4 × M2 × 6), objectif vers le bas, et y brancher la nappe de 1 m ;
   - enfiler la nappe dans le bras, puis dans le segment 2, le segment 1 et l'embase ;
   - emboîter les pièces et les goupiller avec des vis M3 × 35 + écrous ;
   - passer la nappe dans la fente du dessus, visser l'embase (4 × M3 × 10), brancher la nappe sur le port
     CAM/DISP 0 du Pi.
4. **Station d'accessoires** : 2 × M3 × 10 depuis l'intérieur de la coque gauche (avant de poser le dessus
   gauche, ou par la fente de câbles). Y placer l'agrafeuse sans agrafe et le dévidoir.
5. **Zone de scan** : poser les 4 coins noirs sur la table, à droite du plateau, pour former un rectangle A4
   paysage centré sous la caméra. Les fixer avec de la pâte adhésive. Un fond sombre (sous-main noir) améliore
   la détection de la feuille.
6. Coller les 8 patins antidérapants sous les coques.

## 5. Alimentation

Brancher la multiprise : alimentation officielle 27 W → Pi ; alimentation 9 V → jack de l'imprimante ; écran (si
alimentation séparée). Un seul câble secteur sort vers la prise murale.

## 6. Contrôle

Installer le logiciel ([`INSTALL.md`](INSTALL.md)), puis :

```bash
aristote diag buttons   # 4 boutons + SCAN, LED
aristote diag printer   # ticket de test
aristote diag camera    # « Page détectée et redressée » avec une feuille dans la zone
aristote diag mic       # niveau > -45 dBFS en parlant à 30 cm
```
