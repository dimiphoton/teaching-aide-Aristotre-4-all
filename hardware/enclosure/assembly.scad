// Vue d'ensemble du kiosque assemblé (contrôle visuel ; composants représentés en gris).
include <base.scad>
include <modules.scad>

explode = 0;   // > 0 : vue éclatée (mm)

color("#e8e2d0") { shell("gauche"); shell("droite"); }
color("#f4efe2") translate([0, 0, explode]) { deck("gauche"); deck("droite"); }
color("#3d5a80") translate([0, 0, 2 * explode]) { screen_bracket("gauche"); screen_bracket("droite"); }
color("#3d5a80") translate([0, 0, 2 * explode]) printer_pod();
color("#3d5a80") translate([0, 0, 2 * explode]) { mast_foot(); mast_segment(0); mast_segment(1); camera_arm(); }
color("#3d5a80") translate([-explode, 0, 0]) accessory_dock();
color("#222") scan_corners_layout();

// --- Composants (représentation simplifiée) ---
// Écran
color("#111") translate([screen_cx - screen_w / 2, 0, 0]) screen_frame_to_world() cube([screen_w, screen_t, screen_h]);
// Imprimante (façade)
color("#333") translate([pod_pos[0] + pod_size[0] / 2 - printer_bezel[0] / 2, pod_pos[1] + pod_size[1] / 2 - printer_bezel[1] / 2, H + pod_size[2]])
    cube([printer_bezel[0], printer_bezel[1], 3]);
// Boutons
for (i = [0 : 3]) color(["#d93a3a", "#2f6fdb", "#2e9d55", "#e2b420"][i]) translate([student_button_x[i], button_y, H]) cylinder(d = 33, h = 6);
color("white") translate([scan_button_x, button_y, H]) cylinder(d = 33, h = 6);
// Raspberry Pi 5 (visible en vue éclatée)
color("green") translate([pi_origin[0], pi_origin[1], floor_t + pi_standoff_h]) cube([pi_board[0], pi_board[1], 2]);
// Feuille A4 dans la zone de scan
color("white") translate([scan_center[0] - scan_zone[0] / 2, scan_center[1] - scan_zone[1] / 2, 0]) cube([scan_zone[0], scan_zone[1], 0.3]);
// Micro USB à col de cygne
color("#555") translate([usb_panel[0][0], usb_panel[0][1], H]) cylinder(d = 8, h = 160);
