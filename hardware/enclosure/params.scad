// =====================================================================================================
// Aristote 4 All — paramètres du plateau modulaire
// Toutes les cotes en millimètres. Repère : origine au coin AVANT-GAUCHE-BAS du plateau,
// x vers la droite, y vers l'arrière (côté opposé à l'élève), z vers le haut.
// MESUREZ VOS COMPOSANTS au pied à coulisse et corrigez les valeurs marquées [À MESURER].
// =====================================================================================================

// --- Imprimante 3D --------------------------------------------------------------------------------------
bed = [220, 220, 250];          // plateau d'impression (Ender-3, Prusa MK4, Bambu A1/P1…)
$fn = 48;

// --- Jeux et visserie -----------------------------------------------------------------------------------
clr       = 0.4;                // jeu d'emboîtement
m3_hole   = 3.4;                // passage de vis M3
m3_head   = 6.2;                // tête de vis M3 (fraisage cylindrique)
insert_d  = 4.2;                // trou pour insert laiton M3 × 5 (diamètre selon fabricant)
insert_h  = 5.8;
m25_hole  = 2.7;                // M2,5 (Raspberry Pi)

// --- Plateau (base) -------------------------------------------------------------------------------------
W = 400;                        // largeur totale (2 moitiés de 200 mm)
D = 200;                        // profondeur
H = 50;                         // hauteur totale, plateau supérieur compris
wall = 3;                       // parois
floor_t = 3;                    // fond
deck_t = 3;                     // plateau supérieur (épaisseur ≤ 4 mm pour les boutons arcade à clips)
half_w = W / 2;
shell_h = H - deck_t;           // hauteur des coques
boss_d = 8;                     // colonnes de fixation
corner_r = 6;

// Vis plateau supérieur → coques (coordonnées locales à une moitié)
deck_screws = [[8, 8], [half_w - 8, 8], [8, D - 8], [half_w - 8, D - 8], [half_w / 2, 8], [half_w / 2, D - 8]];
// Boulons d'assemblage des deux moitiés (y, z) à travers les parois centrales
join_bolts = [[20, 15], [20, 35], [D - 20, 15], [D - 20, 35]];   // hors de l'ouverture centrale des parois

// --- Boutons arcade 30 mm --------------------------------------------------------------------------------
button_d = 30.2;                // [À MESURER] diamètre de perçage conseillé par le fabricant
button_y = 32;
student_button_x = [30, 70, 110, 150];
scan_button_x = 236;            // écarté des boutons élèves pour éviter les confusions

// --- Écran 10,1" ------------------------------------------------------------------------------------------
screen_w = 257;                 // [À MESURER] largeur avec coque
screen_h = 170;                 // [À MESURER] hauteur avec coque
screen_t = 14;                  // [À MESURER] épaisseur au bord
screen_tilt = 15;               // inclinaison vers l'arrière (degrés)
screen_lift = 8;                // garde au sol au-dessus du plateau
screen_cx = 155;                // centre de l'écran en x
screen_front_y = 92;            // bord inférieur avant de l'écran
bracket_t = 14;                 // épaisseur (x) d'un support latéral
bracket_grip = 10;              // profondeur de prise sur le bord de l'écran
bracket_foot = [bracket_t, 90]; // empreinte au sol (x, y)
bracket_x = [screen_cx - screen_w / 2 - bracket_t / 2 - clr, screen_cx + screen_w / 2 + bracket_t / 2 + clr];
bracket_y0 = screen_front_y - 14;
screen_cable_slot = [[120, 150], [65, 16]];   // passage HDMI + USB tactile sous l'écran (position, taille)

// --- Imprimante thermique CSN-A2 (montage encastré) -------------------------------------------------------
printer_cut = [103.5, 58];      // [À MESURER] découpe de façade (x, y)
printer_bezel = [111, 65];      // façade
printer_depth = 57;             // [À MESURER] profondeur du corps sous la façade
pod_wall = 3;
pod_top_t = 2.5;                // épaisseur sous la façade (clips de l'imprimante : 1,5 à 3 mm)
pod_size = [printer_cut[0] + 2 * pod_wall, printer_cut[1] + 2 * pod_wall, printer_depth + pod_top_t + 4];
pod_pos = [W - 12 - pod_size[0], 10];      // coin avant-gauche de la nacelle sur le plateau
pod_screws = [[8, 8], [pod_size[0] - 8, 8], [8, pod_size[1] - 8], [pod_size[0] - 8, pod_size[1] - 8]];

// --- Mât de caméra -----------------------------------------------------------------------------------------
mast_tube = 26;                 // section carrée extérieure
mast_wall = 2.6;
mast_foot = 46;                 // embase carrée
mast_socket_h = 25;             // profondeur d'emboîtement du premier segment dans l'embase
mast_foot_t = 5;
mast_center = [W - 26, 100];    // derrière la nacelle de l'imprimante, côté zone de scan
mast_segment_len = 124;         // 2 segments (+ emboîtement) : objectif à camera_height au-dessus de la table
spigot_len = 18;
camera_height = 300;            // hauteur de l'objectif au-dessus de la table
scan_zone = [297, 210];         // A4 paysage, posé à droite du plateau
scan_gap = 5;                   // écart entre le plateau et la zone de scan
scan_center = [W + scan_gap + scan_zone[0] / 2, mast_center[1]];
arm_len = scan_center[0] - mast_center[0];
arm_section = [22, 16];         // (largeur, hauteur) du bras, creux pour la nappe
cam_board = [25, 24];           // Camera Module 3
cam_holes = [21, 12.5];         // entraxe des trous M2 (x, y)
cam_hole_offset_y = 2.0;        // trous à 2 mm du bord haut de la carte

// --- Micro (rallonge USB-A à visser, « panel mount ») -------------------------------------------------------
usb_panel = [[318, 150], [15.5, 8.5], 28];    // position, ouverture, entraxe des vis [À MESURER]

// --- Raspberry Pi 5 (moitié droite, au plus près du mât : nappe caméra plus courte) ----------------------
// Carte tournée de 90° : 56 mm en x, 85 mm en y, connecteurs USB/Ethernet vers l'arrière.
pi_board = [56, 85];
pi_origin = [212, 98];          // coin de la carte
pi_holes = [[3.5, 3.5], [52.5, 3.5], [3.5, 61.5], [52.5, 61.5]];
pi_standoff_h = 6;
perf_origin = [135, 62];        // plaque à pastilles 50 × 70 (ULN2803A), moitié gauche
perf_holes = [[2, 2], [48, 2], [2, 68], [48, 68]];

// --- Paroi arrière (moitié droite) ----------------------------------------------------------------------
dc_jack = [[345, 22], 8.2];     // embase jack 5,5 × 2,1 de l'alim imprimante 9 V
usbc_slot = [[250, 16], [14, 8.5]];   // passage de la fiche USB-C de l'alim du Pi

// --- Station d'accessoires (agrafeuse sans agrafe + dévidoir), fixée sur le flanc gauche -------------
dock_size = [118, 124, H];      // (x, y, z)
stapler_pocket = [42, 112, 36]; // [À MESURER] agrafeuse sans agrafe (l, L, profondeur du logement)
tape_pocket = [58, 112, 36];    // [À MESURER] dévidoir de ruban adhésif
dock_y = (D - dock_size[1]) / 2;
dock_bolts = [[dock_y + 25, 24], [dock_y + dock_size[1] - 25, 24]];  // (y, z) à travers la paroi gauche

// --- Coins de la zone de scan ----------------------------------------------------------------------------
corner_leg = 40;
corner_w = 12;
corner_t = 2;

// --- Vérification : chaque pièce doit tenir sur le plateau d'impression -----------------------------
module check_fits(size, name) {
    if (size[0] > bed[0] || size[1] > bed[1] || size[2] > bed[2])
        echo(str("ATTENTION : ", name, " (", size, ") dépasse le plateau d'impression ", bed));
}
