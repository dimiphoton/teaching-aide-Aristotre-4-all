// Pièces à imprimer, posées à plat à l'origine. Choisir la pièce avec -D 'part="…"' (voir build.sh).
include <base.scad>
include <modules.scad>

part = "coque_gauche";

// Ramène une pièce dessinée en coordonnées « assemblage » à l'origine, dans son orientation d'impression.
module to_origin(offset) translate(-offset) children();

if (part == "coque_gauche")       shell("gauche");
else if (part == "coque_droite")  to_origin([half_w, 0, 0]) shell("droite");
// Plateaux supérieurs imprimés face visible contre le plateau d'impression (meilleur état de surface).
else if (part == "dessus_gauche") translate([0, D, H]) rotate([180, 0, 0]) deck("gauche");
else if (part == "dessus_droit")  translate([-half_w, D, H]) rotate([180, 0, 0]) deck("droite");
// Supports d'écran imprimés couchés sur le flanc.
else if (part == "support_ecran_gauche")
    rotate([0, -90, 0]) translate([-(bracket_x[0] - bracket_t / 2), -bracket_y0 + 2, -H]) screen_bracket("gauche");
else if (part == "support_ecran_droit")
    rotate([0, 90, 0]) translate([-(bracket_x[1] + bracket_t / 2), -bracket_y0 + 2, -H]) screen_bracket("droite");
// Nacelle imprimée à l'envers (plaque supérieure contre le plateau).
else if (part == "nacelle_imprimante")
    translate([0, pod_size[1], pod_size[2]]) rotate([180, 0, 0]) to_origin([pod_pos[0], pod_pos[1], H]) printer_pod();
else if (part == "mat_embase")    to_origin([mast_center[0] - mast_foot / 2, mast_center[1] - mast_foot / 2, H]) mast_foot();
// Segments couchés (meilleure résistance en flexion que debout).
else if (part == "mat_segment")
    rotate([0, 90, 0]) to_origin([mast_center[0] + mast_tube / 2, mast_center[1] - mast_tube / 2, H + mast_foot_t]) mast_segment(0);
else if (part == "bras_camera")
    translate([0, 0, spigot_len + 4]) rotate([180, 0, 0])
        to_origin([mast_center[0] - (mast_tube + 6) / 2, mast_center[1], H + mast_foot_t + 2 * mast_segment_len]) camera_arm();
else if (part == "station_accessoires") to_origin([-dock_size[0], dock_y, 0]) accessory_dock();
else if (part == "coin_scan")     scan_corner();
