#!/bin/bash
set -eo pipefail
export WM_PROJECT_DIR=/usr/share/openfoam
case_name=${1:-coarse}
cd "/case/$case_name"
if [ -d postProcessing ]; then echo "This case already has results. Generate a new case instead of remeshing it." >&2; exit 2; fi
/usr/bin/python3 /scripts/tets_to_hex.py mesh.msh
gmshToFoam mesh-hex.msh > log.convert 2>&1
/usr/bin/python3 - <<'PY'
from pathlib import Path
import re
p=Path('constant/polyMesh/boundary');s=p.read_text()
s,n=re.subn(r'(\bdome\s*\{\s*type\s+)patch',r'\1wall',s)
if n!=1:raise RuntimeError('Expected one dome wall patch')
p.write_text(s)
PY
checkMesh -allGeometry -allTopology > log.checkMesh 2>&1
if ! grep -q 'Mesh OK' log.checkMesh; then tail -80 log.checkMesh; exit 2; fi
simpleFoam > log.solver 2>&1
