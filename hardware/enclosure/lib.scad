// Fonctions utilitaires communes.
include <params.scad>

module rounded_box(size, r = 3) {
    hull() for (x = [r, size[0] - r], y = [r, size[1] - r])
        translate([x, y, 0]) cylinder(r = r, h = size[2]);
}

// Colonne avec trou pour insert laiton (vis par le haut).
module insert_boss(h, d = boss_d) {
    difference() {
        cylinder(d = d, h = h);
        translate([0, 0, h - insert_h]) cylinder(d = insert_d, h = insert_h + 0.01);
    }
}

// Trou de vis M3 avec lamage pour la tête (vis par le haut, pièce d'épaisseur t).
module m3_through(t, counterbore = 0) {
    translate([0, 0, -0.01]) cylinder(d = m3_hole, h = t + 0.02);
    if (counterbore > 0) translate([0, 0, t - counterbore]) cylinder(d = m3_head, h = counterbore + 0.01);
}

// Fentes d'aération alignées le long de x.
module vent_slots(n, len, w = 3, pitch = 7, depth = 10) {
    for (i = [0 : n - 1]) translate([i * pitch, 0, -depth / 2])
        hull() { cylinder(d = w, h = depth); translate([0, len, 0]) cylinder(d = w, h = depth); }
}

// Patte de fixation à 2 vis M3 (embase de module), centrée en x.
module screw_flange(size, holes, t = 4) {
    difference() {
        rounded_box([size[0], size[1], t], 4);
        for (p = holes) translate([p[0], p[1], 0]) m3_through(t, 2);
    }
}
