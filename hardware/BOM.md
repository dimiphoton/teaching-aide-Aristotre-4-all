# BOM — Liste du matériel (1 kiosque)

> Prix indicatifs TTC en euros (fourchette constatée chez les revendeurs agréés Raspberry Pi et grands sites de
> e-commerce). Vérifiez la disponibilité au moment de la commande. « ou équivalent » = toute référence respectant
> **exactement** les caractéristiques indiquées.

## 1. Calcul et stockage

| # | Composant | Référence recommandée | Caractéristiques impératives | Qté | Prix ≈ |
|---|---|---|---|---|---|
| 1 | Ordinateur monocarte | **Raspberry Pi 5 – 8 Go** (SC1112) | 8 Go RAM, GPIO 40 broches, 2 ports CSI/DSI | 1 | 85 € |
| 2 | Alimentation | **Alimentation officielle Raspberry Pi 27 W USB-C** (prise EU) | 5,1 V / 5 A USB-PD — indispensable pour alimenter les ports USB à 1,6 A | 1 | 13 € |
| 3 | Refroidissement | **Raspberry Pi Active Cooler** | Ventilateur piloté, clipsé | 1 | 6 € |
| 4 | Stockage | **Raspberry Pi SSD Kit 256 Go** (M.2 HAT+ + SSD NVMe) | Les journaux écrivent en continu : un SSD évite l'usure des cartes SD | 1 | 45 € |
| 4b | *Variante économique* | Carte microSD Raspberry Pi A2 64 Go | Classe A2 obligatoire | (1) | (12 €) |

## 2. Interface élève

| # | Composant | Référence recommandée | Caractéristiques impératives | Qté | Prix ≈ |
|---|---|---|---|---|---|
| 5 | Écran tactile | **Waveshare 10.1" HDMI LCD capacitif 1280×800** ou équivalent | 10,1", IPS, ≥ 1280×800, entrée HDMI, tactile **capacitif** USB HID (sans pilote), alimentation 5 V par USB | 1 | 75–95 € |
| 6 | Câble vidéo | Câble micro-HDMI → HDMI, 30 cm | Le Pi 5 n'a que des ports micro-HDMI | 1 | 6 € |
| 7 | Câble tactile | USB-A → (micro-USB ou USB-C selon écran), 30 cm | Données + alimentation de l'écran | 1 | 4 € |
| 8 | Boutons élèves | Boutons arcade **30 mm à LED 5 V**, 4 couleurs distinctes (rouge, bleu, vert, jaune) | Contact NO momentané, LED 5 V avec résistance intégrée, cosses 4,8 mm ou 2,8 mm | 4 | 12 € |
| 9 | Bouton SCAN | Bouton arcade 30 mm à LED 5 V, **blanc** | Idem | 1 | 3 € |
| 10 | Pilote LED | **ULN2803A** (DIP-18) + support | 8 canaux Darlington, commande 3,3 V → LED 5 V | 1 | 2 € |
| 11 | Carte d'interface | Plaque de prototypage format HAT pour Pi (avec connecteur 2×20 traversant) | Doit laisser passer le câble caméra | 1 | 6 € |
| 12 | Câblage boutons | Câbles Dupont F-F 20 cm + cosses femelles isolées (taille des boutons) | — | 1 lot | 6 € |

## 3. Capteurs

| # | Composant | Référence recommandée | Caractéristiques impératives | Qté | Prix ≈ |
|---|---|---|---|---|---|
| 13 | Caméra | **Raspberry Pi Camera Module 3** (standard, **pas** la version *Wide*) | 12 MP IMX708, **autofocus** (indispensable pour lire une copie à 25–35 cm), champ standard = moins de distorsion | 1 | 27 € |
| 14 | Nappe caméra | Nappe **Raspberry Pi 5** 22 broches → 15 broches, **300 mm** | Le Pi 5 utilise le petit connecteur 22 broches | 1 | 3 € |
| 15 | Micro | Micro **USB à col de cygne, cardioïde** (plug-and-play, UAC) | Directionnel pour limiter le bruit de la classe ; pas de pilote | 1 | 15–25 € |
| 16 | *Optionnel* Haut-parleur | Mini enceinte alimentée USB avec entrée USB-audio | Pour la lecture vocale (fonction future) | (1) | (12 €) |

## 4. Impression

| # | Composant | Référence recommandée | Caractéristiques impératives | Qté | Prix ≈ |
|---|---|---|---|---|---|
| 17 | Imprimante thermique | **CSN-A2 version TTL** (ex. Adafruit « Mini Thermal Receipt Printer », produit 597) | Interface **TTL** (pas RS-232), 5–9 V, papier 57/58 mm, rouleau Ø ≤ 39 mm | 1 | 50–60 € |
| 18 | Adaptateur série | Convertisseur **USB-TTL CP2102** (logique 3,3 V, E/S tolérantes 5 V) | Port stable `/dev/aristote-printer` via règle udev ; identique sur Pi ou mini-PC | 1 | 4 € |
| 19 | Alimentation imprimante | Bloc **9 V / 2 A** (jack 5,5 × 2,1) + adaptateur jack femelle → bornier | Alimentation séparée obligatoire (pointes à ~2 A). 5 V / 2 A fonctionne aussi, impression plus claire | 1 | 10 € |
| 20 | Papier | Rouleaux thermiques **57 mm × Ø 30–38 mm, sans BPA ni BPS** | Contact avec les mains d'enfants → papier sans bisphénol | 10 | 10 € |

## 5. Mécanique et alimentation générale

| # | Composant | Référence recommandée | Caractéristiques impératives | Qté | Prix ≈ |
|---|---|---|---|---|---|
| 21 | Filament | **PETG** 1,75 mm | Plus robuste et moins cassant que le PLA en usage scolaire ; ≈ 700 g par kiosque | 1 kg | 20 € |
| 22 | Inserts | Inserts laiton à chaud M3 × 5 mm (lot de 50) + vis M3 × 8/12 mm | — | 1 lot | 8 € |
| 23 | Visserie Pi | Entretoises M2,5 × 11 mm + vis M2,5 (pour M.2 HAT+) | Souvent incluses dans le kit SSD | 1 lot | 3 € |
| 24 | Patins | Patins antidérapants silicone | Stabilité sur la table | 4 | 2 € |
| 25 | Multiprise | Multiprise 3 prises avec interrupteur, câble 1,5 m | Un seul câble secteur sort du kiosque | 1 | 10 € |

## 6. Accessoires passifs (logements prévus dans le boîtier)

| # | Composant | Référence recommandée | Remarque | Qté | Prix ≈ |
|---|---|---|---|---|---|
| 26 | Agrafeuse sans agrafe | Type « Harinacs » / « Paper Clinch » (capacité 4–5 feuilles) | Cotes de logement paramétrables dans `enclosure/params.scad` | 1 | 8–12 € |
| 27 | Dévidoir de ruban adhésif | Dévidoir de bureau pour rouleaux 19 mm × 33 m | Idem | 1 | 5 € |

## 7. Récapitulatif

| Poste | Coût ≈ |
|---|---|
| Calcul et stockage | 149 € |
| Interface élève | 114–134 € |
| Capteurs | 45–55 € |
| Impression | 74–84 € |
| Mécanique et alimentation | 43 € |
| Accessoires passifs | 13–17 € |
| **Total par kiosque** | **≈ 440–480 €** |
| **Classe de 30 élèves (8 kiosques)** | **≈ 3 500–3 850 €** |

Variante économique (microSD au lieu du SSD, écran générique) : ≈ 390 € par kiosque.

## 8. Équipement de classe (optionnel)

| Composant | Usage | Recommandation | Prix ≈ |
|---|---|---|---|
| Hub IA local | Mode « 100 % local » : LLM + OCR manuscrit (VLM) via Ollama pour 8 kiosques | Mac mini M4 24 Go, **ou** PC avec GPU NVIDIA 12 Go VRAM (RTX 3060 12 Go d'occasion) | 700–1 000 € |
| Routeur dédié | Si le Wi-Fi de l'établissement isole les appareils (Syncthing passe alors par relais Internet) | Petit routeur de voyage OpenWrt (ex. GL.iNet) | 30–60 € |
| Rouleaux de papier | Consommable annuel | ≈ 1 rouleau / kiosque / semaine | 30 € / kiosque / an |

## 9. Brochage GPIO (résumé — détail dans `wiring.md`)

| Fonction | GPIO (BCM) | Broche physique | Câblage |
|---|---|---|---|
| Bouton élève 1 | GPIO 5 | 29 | Bouton entre GPIO et GND (pull-up interne) |
| Bouton élève 2 | GPIO 6 | 31 | idem |
| Bouton élève 3 | GPIO 13 | 33 | idem |
| Bouton élève 4 | GPIO 19 | 35 | idem |
| Bouton SCAN | GPIO 26 | 37 | idem |
| LED élève 1 | GPIO 12 | 32 | → ULN2803A entrée 1 ; sortie 1 → cathode LED ; anode LED → 5 V |
| LED élève 2 | GPIO 16 | 36 | → ULN2803A entrée 2 |
| LED élève 3 | GPIO 20 | 38 | → ULN2803A entrée 3 |
| LED élève 4 | GPIO 21 | 40 | → ULN2803A entrée 4 |
| LED SCAN | GPIO 25 | 22 | → ULN2803A entrée 5 |
| 5 V LED / ULN2803A COM | 5 V | 2 | Broche 10 (COM) de l'ULN2803A au 5 V |
| Masse | GND | 6, 9, 14, 39 | Masse commune ULN2803A (broche 9) |
| Imprimante | USB | — | CP2102 : TX → RX imprimante, RX → TX imprimante, GND → GND imprimante **et** GND alim 9 V |
