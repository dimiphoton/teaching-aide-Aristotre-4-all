# Plateau modulaire imprimable en 3D

![Plateau assemblé](../../docs/images/plateau-assemblage.png)

Le kiosque est un **plateau compact (400 × 200 × 50 mm)** qui contient l'électronique. Les composants
**s'enfichent** sur le dessus, chacun dans son embase vissée sur inserts laiton :

| Module | Embase | Fixation |
|---|---|---|
| Écran 10,1" | 2 supports latéraux, l'écran glisse par le haut dans les rainures (inclinaison 15°) | 2 × M3 par support |
| Imprimante CSN-A2 | Nacelle : l'imprimante s'encastre par le haut et se clipse | 4 × M3 vissées depuis l'intérieur de la nacelle |
| Caméra | Mât creux en 2 segments + bras ; la nappe passe dans le mât | 4 × M3 + goupilles M3 |
| Micro à col de cygne | Rallonge USB-A à visser dans le plateau | 2 × M3 + écrous |
| Boutons | 4 boutons élèves + SCAN, perçages Ø 30 mm repérés 1 à 4 | clips des boutons |
| Agrafeuse + dévidoir | Station d'accessoires sur le flanc gauche | 2 × M3 à travers la paroi |
| Zone de scan | 4 coins (A4 paysage) posés sur la table, à droite | aucune |

Toutes les cotes sont dans [`params.scad`](params.scad) ; les valeurs marquées `[À MESURER]` doivent être
vérifiées au pied à coulisse sur vos composants (écran, imprimante, agrafeuse, dévidoir) avant d'imprimer.

## Fichiers

| Fichier | Contenu |
|---|---|
| `params.scad` | Tous les paramètres (plateau d'impression, composants, positions) |
| `lib.scad` | Fonctions communes |
| `base.scad` | Coques et plateaux supérieurs |
| `modules.scad` | Supports d'écran, nacelle, mât, bras, station, coins de scan |
| `parts.scad` | Chaque pièce posée à plat pour l'impression (`-D 'part="…"'`) |
| `assembly.scad` | Vue d'ensemble (`-D explode=60` : vue éclatée) |
| `build.sh` | Génère `stl/*.stl` et vérifie que chaque pièce tient sur le plateau d'impression |
| `stl/` | STL prêts à imprimer (régénérer avec `./build.sh` après toute modification de `params.scad`) |

## Pièces à imprimer

Plateau d'impression minimal : **220 × 220 mm** (Ender-3, Prusa MK4, Bambu Lab A1/P1). Toutes les pièces sont
vérifiées par `build.sh`.

| Pièce (`stl/`) | Qté | Dimensions (mm) | Orientation | Supports | Durée ≈ |
|---|---|---|---|---|---|
| `coque_gauche` | 1 | 200 × 200 × 47 | fond sur le plateau | non | 9 h |
| `coque_droite` | 1 | 200 × 200 × 47 | fond sur le plateau | non | 9 h |
| `dessus_gauche` | 1 | 200 × 200 × 9 | face visible sur le plateau | non | 4 h |
| `dessus_droit` | 1 | 200 × 200 × 9 | face visible sur le plateau | non | 4 h |
| `support_ecran_gauche` | 1 | 116 × 90 × 14 | couché sur le flanc | non | 2 h |
| `support_ecran_droit` | 1 | 116 × 90 × 14 | couché sur le flanc | non | 2 h |
| `nacelle_imprimante` | 1 | 110 × 64 × 64 | à l'envers (dessus sur le plateau) | non | 4 h |
| `mat_embase` | 1 | 46 × 46 × 30 | à plat | non | 1 h |
| `mat_segment` | **2** | 142 × 26 × 26 | couché | non (ponts de 21 mm) | 2 × 2 h |
| `bras_camera` | 1 | 213 × 34 × 22 | à l'envers | non | 3 h |
| `station_accessoires` | 1 | 118 × 124 × 50 | à plat | non | 5 h |
| `coin_scan` | **4** | 40 × 40 × 2 | à plat, **filament noir** | non | 4 × 10 min |

Total ≈ 45 h et ≈ 700 g de PETG par kiosque.

### Réglages conseillés (PETG)

- Buse 0,4 mm, couches de 0,2 mm (0,16 mm pour la nacelle et le bras).
- 3 périmètres, 4 couches pleines dessus/dessous, remplissage gyroïde 20 % (40 % pour l'embase du mât et le bras).
- Buse 235-245 °C, plateau 80 °C, ventilation 40 %.
- Les coques et dessus font 200 mm : bord (*brim*) de 5 mm si les coins se soulèvent.

## Assemblage mécanique (résumé — détail dans `docs/ASSEMBLY.md`)

1. Poser les **inserts laiton M3** au fer à souder (≈ 220 °C) : 12 dans les colonnes des coques, 12 dans les
   bossages sous les dessus (posés par le dessus), 2 dans la station d'accessoires.
2. Assembler les deux coques : 4 boulons M3 × 12 + écrous à travers les parois centrales.
3. Visser le Raspberry Pi (moitié droite) et la plaque ULN2803A (moitié gauche) ; câbler (`hardware/wiring.md`).
4. Clipser les boutons dans les dessus, visser les dessus (12 × M3 × 8).
5. Visser les modules : supports d'écran, nacelle, embase du mât, rallonge USB du micro, station d'accessoires.
6. Passer la nappe caméra dans l'embase, les 2 segments et le bras **avant** d'emboîter chaque pièce ;
   goupiller avec des vis M3 × 35 + écrous.

## Visserie (par kiosque)

| Élément | Qté |
|---|---|
| Inserts laiton M3 × 5,7 (Ø ext. ≈ 4,6) | 26 |
| Vis M3 × 8 (dessus → coques) | 12 |
| Vis M3 × 10 (modules, station, rallonge USB) | 16 |
| Vis M3 × 12 + écrous (jonction des coques) | 4 |
| Vis M3 × 35 + écrous (goupilles du mât et du bras) | 3 |
| Écrous M3 (rallonge USB) | 2 |
| Vis M2,5 × 6 (Pi, plaque ULN) | 8 |
| Vis M2 × 6 (caméra) | 4 |
