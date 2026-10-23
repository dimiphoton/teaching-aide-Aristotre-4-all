# Câblage

## Vue d'ensemble

```
             ┌──────────────── Secteur (multiprise 3 prises) ─────────────────┐
             │                         │                                       │
   Alim officielle 27 W USB-C   Alim 9 V / 2 A (jack)                   Alim 5 V écran (si besoin)
             │                         │
             ▼                         ▼  embase jack (paroi arrière)
  ┌───────────────────────┐      ┌───────────────┐
  │ Raspberry Pi 5        │      │ CSN-A2        │◄── TX/RX/GND ── adaptateur USB-TTL CP2102 ── USB ──┐
  │  GPIO ── boutons/LED  │      │ (nacelle)     │                                                   │
  │  CSI  ── nappe 1 m ───┼──► mât ──► bras ──► Camera Module 3                                      │
  │  USB  ── tactile écran, micro (rallonge USB), CP2102 ◄──────────────────────────────────────────┘
  │  µHDMI ── écran       │
  └───────────────────────┘
```

**Masse commune obligatoire** entre l'alimentation 9 V de l'imprimante, l'imprimante et l'adaptateur USB-TTL,
sinon les données série sont corrompues.

## Brochage GPIO (numérotation BCM)

| Fonction | GPIO | Broche | Câblage |
|---|---|---|---|
| Bouton élève 1 (rouge) | 5 | 29 | contact NO entre la broche et GND (pull-up interne) |
| Bouton élève 2 (bleu) | 6 | 31 | idem |
| Bouton élève 3 (vert) | 13 | 33 | idem |
| Bouton élève 4 (jaune) | 19 | 35 | idem |
| Bouton SCAN (blanc) | 26 | 37 | idem |
| LED élève 1 | 12 | 32 | → ULN2803A entrée 1 (broche 1) |
| LED élève 2 | 16 | 36 | → ULN2803A entrée 2 (broche 2) |
| LED élève 3 | 20 | 38 | → ULN2803A entrée 3 (broche 3) |
| LED élève 4 | 21 | 40 | → ULN2803A entrée 4 (broche 4) |
| LED SCAN | 25 | 22 | → ULN2803A entrée 5 (broche 5) |
| 5 V | — | 2 | anodes (+) des 5 LED, et COM (broche 10) de l'ULN2803A |
| GND | — | 6, 9, 14, 39 | boutons, ULN2803A broche 9 |

Les broches sont modifiables dans `/etc/aristote/config.toml` (`[hardware.buttons]`, `[hardware.leds]`).

## Plaque ULN2803A (plaque à pastilles 50 × 70)

```
          ULN2803A (DIP-18)
   GPIO12 ─ 1 IN1      OUT1 18 ─ cathode (–) LED élève 1
   GPIO16 ─ 2 IN2      OUT2 17 ─ cathode (–) LED élève 2
   GPIO20 ─ 3 IN3      OUT3 16 ─ cathode (–) LED élève 3
   GPIO21 ─ 4 IN4      OUT4 15 ─ cathode (–) LED élève 4
   GPIO25 ─ 5 IN5      OUT5 14 ─ cathode (–) LED SCAN
            6 IN6      OUT6 13
            7 IN7      OUT7 12
            8 IN8      OUT8 11
      GND ─ 9 GND      COM  10 ─ +5 V
   Anodes (+) des 5 LED ─ +5 V   (LED 5 V à résistance intégrée : aucune résistance à ajouter)
```

Repérer la polarité des LED des boutons (souvent marquée + / – sur le support de LED). Une LED montée à
l'envers ne s'allume pas mais ne s'abîme pas : il suffit de la retourner.

## Imprimante CSN-A2 (version TTL)

| Fil de l'imprimante | Vers |
|---|---|
| VH (rouge, alimentation) | + de l'embase jack 9 V |
| GND (noir, alimentation) | – de l'embase jack 9 V |
| RX (entrée données) | TX du CP2102 |
| TX (sortie données) | RX du CP2102 (optionnel : capteur papier) |
| GND (données) | GND du CP2102 |

Vitesse : 19 200 bauds en général ; si le ticket de test est illisible, essayer 9 600 (`baudrate` dans la
configuration). Le ticket imprimé en maintenant le bouton de l'imprimante à la mise sous tension indique sa vitesse.

## Caméra

Nappe **Raspberry Pi 5 22 → 15 broches, 1 m** : du connecteur CAM/DISP 0 du Pi, à travers la fente du plateau,
puis dans l'embase, les deux segments et le bras du mât, jusqu'à la tête. Contacts côté Pi : vers le connecteur
Ethernet ; côté caméra : vers la carte. Vérifier avec `rpicam-hello --list-cameras`.

## Écran

- Micro-HDMI 0 du Pi → HDMI de l'écran (passage sous l'écran, fente du plateau).
- USB du Pi → port tactile de l'écran (alimente aussi l'écran si sa consommation le permet ; sinon alimentation
  5 V séparée sur la multiprise).

## Vérification

```bash
aristote diag buttons   # chaque appui s'affiche, la LED de l'élève s'allume
aristote diag printer   # ticket de test (accents, symboles mathématiques, image)
aristote diag camera    # photo enregistrée, détection de la feuille
aristote diag mic       # niveau sonore en dBFS
```
