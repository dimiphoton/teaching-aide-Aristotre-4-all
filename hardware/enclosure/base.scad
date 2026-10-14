// Plateau : 2 coques (gauche / droite) + 2 plateaux supérieurs, assemblés par boulons M3.
include <lib.scad>

function x0(side) = side == "gauche" ? 0 : half_w;

module half_region(side, z0 = -1, h = H + 2) {
    translate([x0(side), -1, z0]) cube([half_w, D + 2, h]);
}

// ---------------------------------------------------------------------------------------------------------
// Coque
// ---------------------------------------------------------------------------------------------------------
module shell(side) {
    difference() {
        union() {
            intersection() {
                difference() {
                    rounded_box([W, D, shell_h], corner_r);
                    translate([wall, wall, floor_t]) rounded_box([W - 2 * wall, D - 2 * wall, shell_h], corner_r - wall);
                }
                half_region(side);
            }
            // Paroi de jonction, avec grande ouverture pour les câbles
            jx = side == "gauche" ? half_w - wall : half_w;
            difference() {
                translate([jx, 0, 0]) cube([wall, D, shell_h]);
                translate([jx - 1, 40, floor_t + 6]) cube([wall + 2, D - 80, shell_h - floor_t - 12]);
            }
            // Colonnes de fixation du plateau supérieur
            for (p = deck_screws) translate([x0(side) + p[0], p[1], 0]) insert_boss(shell_h);
            if (side == "gauche") {
                // Plaque à pastilles du ULN2803A
                for (p = perf_holes) translate([perf_origin[0] + p[0], perf_origin[1] + p[1], 0])
                    difference() { cylinder(d = 6, h = floor_t + 5); cylinder(d = m25_hole - 0.3, h = 30); }
                // Bossages des boulons de la station d'accessoires (paroi gauche)
                for (b = dock_bolts) translate([0, b[0], b[1]]) rotate([0, 90, 0]) cylinder(d = 10, h = wall + 3);
            } else {
                // Raspberry Pi 5 : entretoises (vis M2,5 autotaraudeuses ou inserts M2,5)
                for (p = pi_holes) translate([pi_origin[0] + p[0], pi_origin[1] + p[1], 0])
                    difference() { cylinder(d = 6, h = floor_t + pi_standoff_h); cylinder(d = m25_hole - 0.3, h = 30); }
                // Pont pour collier de serrage (adaptateur USB-TTL)
                translate([pod_pos[0] + 10, pod_pos[1] + pod_size[1] + 20, 0]) difference() {
                    cube([24, 10, floor_t + 6]);
                    translate([-1, 2, floor_t]) cube([26, 6, 3]);
                }
            }
        }
        // Boulons de jonction (écrous côté droit)
        for (b = join_bolts) translate([half_w - wall - 1, b[0], b[1]]) rotate([0, 90, 0]) cylinder(d = m3_hole, h = 2 * wall + 2);
        // Patins antidérapants (Ø 10)
        for (x = [25, half_w - 25], y = [25, D - 25]) translate([x0(side) + x, y, -0.01]) cylinder(d = 10.5, h = 1);
        if (side == "gauche") {
            for (i = [0 : 7]) translate([20 + i * 7, D - wall - 1, floor_t + 22]) cube([3, wall + 2, 16]);
            translate([30, 120, 0]) vent_slots(8, 50, depth = 2 * floor_t + 1);
            // Boulons de la station d'accessoires
            for (b = dock_bolts) translate([-1, b[0], b[1]]) rotate([0, 90, 0]) cylinder(d = m3_hole, h = wall + 5);
        } else {
            // Aération sous le Pi et dans la paroi arrière
            translate([pi_origin[0] + 8, pi_origin[1] + 12, 0]) vent_slots(6, 55, depth = 2 * floor_t + 1);
            for (i = [0 : 8]) translate([half_w + 62 + i * 7, D - wall - 1, floor_t + 22]) cube([3, wall + 2, 16]);
            // Jack d'alimentation de l'imprimante et passage USB-C du Pi (paroi arrière)
            translate([dc_jack[0][0], D - wall - 1, dc_jack[0][1]]) rotate([-90, 0, 0]) cylinder(d = dc_jack[1], h = wall + 2);
            translate([usbc_slot[0][0] - usbc_slot[1][0] / 2, D - wall - 1, usbc_slot[0][1] - usbc_slot[1][1] / 2])
                cube([usbc_slot[1][0], wall + 2, usbc_slot[1][1]]);
        }
    }
}

// ---------------------------------------------------------------------------------------------------------
// Plateau supérieur : perçages des boutons et embases des modules enfichables
// ---------------------------------------------------------------------------------------------------------
function in_half(side, x) = side == "gauche" ? x < half_w : x >= half_w;

// Embases (coordonnées globales) : [x, y] de chaque insert sous le plateau.
function bracket_inserts() = [for (bx = bracket_x) for (dy = [15, bracket_foot[1] - 15]) [bx, bracket_y0 + dy]];
function pod_inserts() = [for (p = pod_screws) [pod_pos[0] + p[0], pod_pos[1] + p[1]]];
function mast_inserts() = [for (sx = [-1, 1], sy = [-1, 1]) [mast_center[0] + sx * 16, mast_center[1] + sy * 16]];
function module_inserts() = concat(bracket_inserts(), pod_inserts(), mast_inserts());

module deck(side) {
    translate([0, 0, shell_h]) difference() {
        union() {
            intersection() {
                union() {
                    rounded_box([W, D, deck_t], corner_r);
                    // Rebord de centrage qui entre dans la coque
                    difference() {
                        translate([wall + clr, wall + clr, -4]) rounded_box([W - 2 * (wall + clr), D - 2 * (wall + clr), 4], corner_r - wall);
                        translate([wall + clr + 1.6, wall + clr + 1.6, -5]) rounded_box([W - 2 * (wall + clr + 1.6), D - 2 * (wall + clr + 1.6), 6], 2);
                    }
                }
                half_region(side, -10, 20);
            }
            // Colonnes à insert sous le plateau pour les modules
            for (p = module_inserts()) if (in_half(side, p[0])) translate([p[0], p[1], -6]) cylinder(d = boss_d, h = 6);
        }
        // Vis du plateau supérieur
        for (p = deck_screws) translate([x0(side) + p[0], p[1], -1]) cylinder(d = m3_hole, h = deck_t + 2);
        // Dégagement du rebord autour des colonnes de la coque
        for (p = deck_screws) translate([x0(side) + p[0], p[1], -5]) cylinder(d = boss_d + 1, h = 5);
        // Inserts des modules (posés par le haut)
        for (p = module_inserts()) if (in_half(side, p[0])) translate([p[0], p[1], -6.01]) cylinder(d = insert_d, h = deck_t + 6.02);
        // Boutons
        for (bx = concat(student_button_x, [scan_button_x])) if (in_half(side, bx))
            translate([bx, button_y, -1]) cylinder(d = button_d, h = deck_t + 2);
        // Passages de câbles : écran, imprimante, nappe caméra
        if (in_half(side, screen_cable_slot[0][0]))
            translate([screen_cable_slot[0][0], screen_cable_slot[0][1], -1]) rounded_box([screen_cable_slot[1][0], screen_cable_slot[1][1], deck_t + 2], 4);
        if (side == "droite") {
            translate([pod_pos[0] + pod_size[0] / 2 - 15, pod_pos[1] + pod_size[1] / 2 - 7, -1]) rounded_box([30, 14, deck_t + 2], 4);
            translate([mast_center[0] - 10, mast_center[1] - 4, -1]) cube([20, 8, deck_t + 2]);
            // Rallonge USB du micro (vis M3 + écrous dessous)
            translate([usb_panel[0][0] - usb_panel[1][0] / 2, usb_panel[0][1] - usb_panel[1][1] / 2, -1])
                cube([usb_panel[1][0], usb_panel[1][1], deck_t + 2]);
            for (sx = [-1, 1]) translate([usb_panel[0][0] + sx * usb_panel[2] / 2, usb_panel[0][1], -1]) cylinder(d = m3_hole, h = deck_t + 2);
        }
        // Repères en creux sous les boutons élèves (1 à 4) et SCAN
        for (i = [0 : 3]) if (in_half(side, student_button_x[i]))
            translate([student_button_x[i], button_y - 24, deck_t - 0.6])
                linear_extrude(1) text(str(i + 1), size = 6, halign = "center", valign = "center");
        if (in_half(side, scan_button_x))
            translate([scan_button_x, button_y - 24, deck_t - 0.6])
                linear_extrude(1) text("SCAN", size = 5, halign = "center", valign = "center");
    }
}
