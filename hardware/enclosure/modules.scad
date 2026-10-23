// Modules enfichables sur le plateau : supports d'écran, nacelle d'imprimante, mât de caméra,
// station d'accessoires, coins de la zone de scan.
include <lib.scad>

// ---------------------------------------------------------------------------------------------------------
// Supports d'écran (gauche / droite) — l'écran glisse par le haut dans les rainures
// ---------------------------------------------------------------------------------------------------------
grip_len = 0.65 * screen_h;     // longueur de prise le long du bord de l'écran
front_lip = 6;                  // recouvrement de la face avant (ne pas masquer la dalle)

module screen_frame_to_world() {
    // Repère local : x = largeur, y = épaisseur (vers l'arrière), z = le long de l'écran vers le haut.
    translate([0, screen_front_y, H + screen_lift]) rotate([-screen_tilt, 0, 0]) children();
}

module screen_bracket(side) {
    bx = side == "gauche" ? bracket_x[0] : bracket_x[1];
    inner_right = side == "gauche";  // l'écran est à droite du support gauche
    x_min = bx - bracket_t / 2;
    difference() {
        union() {
            // Embase
            translate([x_min, bracket_y0, H]) cube([bracket_t, bracket_foot[1], 5]);
            // Glissière inclinée
            translate([x_min, 0, 0]) screen_frame_to_world() translate([0, -4, -6]) cube([bracket_t, screen_t + 8, grip_len + 6]);
            // Jambe de force derrière l'écran
            hull() {
                translate([x_min, bracket_y0 + 45, H]) cube([bracket_t, bracket_foot[1] - 45, 5]);
                translate([x_min, 0, 0]) screen_frame_to_world() translate([0, screen_t, -6]) cube([bracket_t, 4, 0.55 * grip_len]);
            }
        }
        // Rainure de l'écran (côté intérieur)
        gx = inner_right ? x_min + bracket_t - bracket_grip : x_min - 1;
        translate([gx, 0, 0]) screen_frame_to_world() translate([0, 0, 0]) cube([bracket_grip + 1, screen_t + clr, grip_len + 10]);
        // Lèvre avant réduite pour ne pas masquer la dalle
        lx = inner_right ? x_min + bracket_t - bracket_grip : x_min + front_lip;
        translate([lx, 0, 0]) screen_frame_to_world() translate([0, -5, 0]) cube([bracket_grip - front_lip, 5.01, grip_len + 10]);
        // Vis d'embase (lamage)
        for (dy = [15, bracket_foot[1] - 15]) translate([bx, bracket_y0 + dy, H]) m3_through(5, 2.5);
        // Rien sous le plateau
        translate([x_min - 50, -50, H - 20]) cube([bracket_t + 100, 400, 20]);
    }
}

// ---------------------------------------------------------------------------------------------------------
// Nacelle de l'imprimante CSN-A2 (encastrée par le haut, clips sur la plaque supérieure)
// ---------------------------------------------------------------------------------------------------------
module printer_pod() {
    translate([pod_pos[0], pod_pos[1], H]) difference() {
        rounded_box(pod_size, 3);
        // Logement du corps de l'imprimante
        translate([pod_wall, pod_wall, 4]) cube([printer_cut[0], printer_cut[1], pod_size[2]]);
        // Fond : passage du câble et vis vers le plateau (vissées depuis l'intérieur avant de poser l'imprimante)
        translate([pod_size[0] / 2 - 13, pod_size[1] / 2 - 6, -1]) rounded_box([26, 12, 10], 3);
        for (p = pod_screws) translate([p[0], p[1], 0]) m3_through(4, 0);
        // Fenêtre arrière pour tirer les câbles pendant le montage
        translate([pod_size[0] / 2 - 20, pod_size[1] - pod_wall - 1, 8]) cube([40, pod_wall + 2, 20]);
    }
}

// ---------------------------------------------------------------------------------------------------------
// Mât de caméra : embase, 2 segments creux (la nappe passe à l'intérieur), bras avec tête de caméra
// ---------------------------------------------------------------------------------------------------------
bore = mast_tube - 2 * mast_wall;                 // alésage du tube
spigot = bore - clr;                              // tenon d'emboîtement
socket_outer = mast_tube + 2 * 3;

module mast_foot() {
    translate([mast_center[0], mast_center[1], H]) difference() {
        union() {
            translate([-mast_foot / 2, -mast_foot / 2, 0]) rounded_box([mast_foot, mast_foot, mast_foot_t], 5);
            translate([-socket_outer / 2, -socket_outer / 2, 0]) rounded_box([socket_outer, socket_outer, mast_foot_t + mast_socket_h], 3);
        }
        translate([-(mast_tube + clr) / 2, -(mast_tube + clr) / 2, mast_foot_t]) cube([mast_tube + clr, mast_tube + clr, 100]);
        translate([-10, -4, -1]) cube([20, 8, 20]);                        // nappe caméra
        for (sx = [-1, 1], sy = [-1, 1]) translate([sx * 16, sy * 16, 0]) m3_through(mast_foot_t, 2);
        translate([0, 0, mast_foot_t + mast_socket_h / 2]) rotate([0, 90, 0]) cylinder(d = m3_hole, h = 50, center = true);
    }
}

module mast_segment(n) {
    z0 = H + mast_foot_t + n * mast_segment_len;
    translate([mast_center[0], mast_center[1], z0]) difference() {
        union() {
            translate([-mast_tube / 2, -mast_tube / 2, 0]) cube([mast_tube, mast_tube, mast_segment_len]);
            translate([-spigot / 2, -spigot / 2, mast_segment_len - 1]) cube([spigot, spigot, spigot_len + 1]);
        }
        translate([-bore / 2, -bore / 2, -1]) cube([bore, bore, mast_segment_len - 3]);   // cloison de 2 mm en haut
        translate([-9, -2.5, -1]) cube([18, 5, mast_segment_len + spigot_len + 2]);        // passage de la nappe
        // Goupilles M3 (embase ou segment inférieur / segment supérieur)
        translate([0, 0, mast_socket_h / 2 - (n == 0 ? 0 : spigot_len / 2 + 3)]) rotate([0, 90, 0]) cylinder(d = m3_hole, h = 50, center = true);
        translate([0, 0, mast_segment_len + spigot_len / 2]) rotate([0, 90, 0]) cylinder(d = m3_hole, h = 50, center = true);
    }
}

module camera_arm() {
    z0 = H + mast_foot_t + 2 * mast_segment_len;
    sleeve = mast_tube + 6;
    translate([mast_center[0], mast_center[1], z0]) difference() {
        union() {
            translate([-sleeve / 2, -sleeve / 2, 0]) rounded_box([sleeve, sleeve, spigot_len + 4], 3);
            translate([0, -arm_section[0] / 2, spigot_len + 4 - arm_section[1]]) cube([arm_len, arm_section[0], arm_section[1]]);
            // Tête : plaque de caméra horizontale, objectif vers le bas
            translate([arm_len - 17, -17, spigot_len + 4 - arm_section[1] - 3]) rounded_box([34, 34, arm_section[1] + 3], 3);
        }
        translate([-(spigot + 2 * clr) / 2, -(spigot + 2 * clr) / 2, -1]) cube([spigot + 2 * clr, spigot + 2 * clr, spigot_len + 1]);
        translate([0, 0, spigot_len / 2]) rotate([0, 90, 0]) cylinder(d = m3_hole, h = sleeve + 2, center = true);
        // Canal de la nappe : du mât jusqu'à la tête
        translate([-9, -9, spigot_len - 1]) cube([18, 18, 3]);
        translate([0, -9, spigot_len + 4 - arm_section[1] + 2.5]) cube([arm_len - 8, 18, arm_section[1] - 5]);
        // Logement de la carte caméra (25 × 24) ouvert vers le bas, trous M2, fenêtre d'objectif
        translate([arm_len, 0, spigot_len + 4 - arm_section[1] - 3]) {
            translate([-cam_board[0] / 2 - clr, -cam_board[1] / 2 - clr, -1]) cube([cam_board[0] + 2 * clr, cam_board[1] + 2 * clr, 4]);
            for (sx = [-1, 1], sy = [-1, 1]) translate([sx * cam_holes[0] / 2, sy * cam_holes[1] / 2, 0]) cylinder(d = 1.8, h = 12);
            translate([-9, -cam_board[1] / 2 - clr, 2.9]) cube([18, cam_board[1] + 2 * clr, arm_section[1] - 3]);
        }
    }
}

// ---------------------------------------------------------------------------------------------------------
// Station d'accessoires (flanc gauche) : agrafeuse sans agrafe + dévidoir de ruban adhésif
// ---------------------------------------------------------------------------------------------------------
module accessory_dock() {
    translate([-dock_size[0], dock_y, 0]) difference() {
        rounded_box(dock_size, corner_r);
        // Logements ouverts vers le haut
        translate([4, (dock_size[1] - stapler_pocket[1]) / 2, dock_size[2] - stapler_pocket[2]])
            rounded_box([stapler_pocket[0], stapler_pocket[1], stapler_pocket[2] + 1], 3);
        translate([8 + stapler_pocket[0], (dock_size[1] - tape_pocket[1]) / 2, dock_size[2] - tape_pocket[2]])
            rounded_box([tape_pocket[0], tape_pocket[1], tape_pocket[2] + 1], 3);
        // Évidement par le dessous (économie de matière)
        translate([6, 6, -1]) rounded_box([dock_size[0] - 12, dock_size[1] - 12, dock_size[2] - stapler_pocket[2] - 2], 4);
        // Inserts M3 horizontaux dans la face qui touche le plateau
        for (b = dock_bolts) translate([dock_size[0] - 9, b[0] - dock_y, b[1]]) rotate([0, 90, 0]) cylinder(d = insert_d, h = 10);
        // Encoche pour attraper l'agrafeuse
        translate([4 + stapler_pocket[0] / 2, -1, dock_size[2] - 12]) rotate([-90, 0, 0])
            hull() { cylinder(d = 24, h = 10); translate([0, -30, 0]) cylinder(d = 24, h = 10); }
    }
}

// ---------------------------------------------------------------------------------------------------------
// Coins de la zone de scan (imprimer en filament noir : la feuille blanche ressort mieux)
// ---------------------------------------------------------------------------------------------------------
module scan_corner() {
    difference() {
        union() { cube([corner_leg, corner_w, corner_t]); cube([corner_w, corner_leg, corner_t]); }
        translate([corner_w / 2, corner_w / 2, corner_t - 0.6]) cylinder(d = 4, h = 1);
    }
}

module scan_corners_layout() {
    // Position sur la table (assemblage) : les 4 coins de la zone A4 paysage
    for (sx = [0, 1], sy = [0, 1])
        translate([scan_center[0] + (sx - 0.5) * scan_zone[0], scan_center[1] + (sy - 0.5) * scan_zone[1], 0])
            mirror([sx, 0, 0]) mirror([0, sy, 0]) translate([-corner_w, -corner_w, 0]) scan_corner();
}
