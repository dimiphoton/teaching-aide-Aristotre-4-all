#!/usr/bin/env bash
# Génère les fichiers STL de toutes les pièces dans stl/ et vérifie qu'elles tiennent sur le plateau d'impression.
#   ./build.sh            (OpenSCAD 2021.01 ou plus récent)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p stl
PARTS=(coque_gauche coque_droite dessus_gauche dessus_droit support_ecran_gauche support_ecran_droit
       nacelle_imprimante mat_embase mat_segment bras_camera station_accessoires coin_scan)
BED_X=$(sed -n 's/^bed = \[\([0-9]*\), \([0-9]*\), \([0-9]*\)\].*/\1/p' params.scad)
BED_Y=$(sed -n 's/^bed = \[\([0-9]*\), \([0-9]*\), \([0-9]*\)\].*/\2/p' params.scad)
status=0
for part in "${PARTS[@]}"; do
  openscad -q -o "stl/$part.stl" -D "part=\"$part\"" parts.scad
  read -r sx sy sz minz < <(python3 - "stl/$part.stl" <<'PY'
import sys
xs, ys, zs = [], [], []
for line in open(sys.argv[1]):
    line = line.strip()
    if line.startswith("vertex"):
        _, x, y, z = line.split()
        xs.append(float(x)); ys.append(float(y)); zs.append(float(z))
print(f"{max(xs)-min(xs):.1f} {max(ys)-min(ys):.1f} {max(zs)-min(zs):.1f} {min(zs):.2f}")
PY
)
  fits=$(python3 -c "print('ok' if $sx <= $BED_X and $sy <= $BED_Y and abs($minz) < 0.01 else 'NON')")
  printf '%-22s %7s × %7s × %7s mm   %s\n' "$part" "$sx" "$sy" "$sz" "$fits"
  [[ $fits == ok ]] || status=1
done
exit $status
