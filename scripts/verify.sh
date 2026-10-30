#!/usr/bin/env bash
# Release gate: install, version consistency, tests, and the CLI doing real work.
set -uo pipefail
cd "$(dirname "$0")/.."

fail() { echo "GATE FAILED: $*"; exit 1; }

echo "== check 1/4: editable install"
python3 -m pip install -q -e ".[dev]" || fail "install"

echo "== check 2/4: version consistency (pyproject vs module)"
pv=$(python3 - <<'PY'
import pathlib, re
try:
    import tomllib
    print(tomllib.loads(pathlib.Path("pyproject.toml").read_text())["project"]["version"])
except ModuleNotFoundError:                     # Python 3.9/3.10 have no tomllib
    text = pathlib.Path("pyproject.toml").read_text()
    print(re.search(r'(?m)^version\s*=\s*"([^"]+)"', text).group(1))
PY
)
mv=$(python3 -c "import tokentracker;print(tokentracker.__version__)")
[ "$pv" = "$mv" ] || { echo "pyproject says $pv, module says $mv"; fail "version drift"; }
echo "version $pv consistent"

echo "== check 3/4: test suite"
python3 -m pytest -q || fail "tests"

echo "== check 4/5: CLI smoke on the bundled fixtures (expects exit 0)"
out=$(mktemp)
python3 -m tokentracker.cli report tests/fixtures --top 3 > "$out" 2>&1
code=$?
[ "$code" = "0" ] || { echo "expected exit 0, got $code"; cat "$out"; rm -f "$out"; fail "cli exit code"; }
grep -q "Where the context went" "$out" || { cat "$out"; rm -f "$out"; fail "cli output"; }
echo "smoke ok: $(grep -m1 -i 'model calls' "$out" | sed 's/tokentracker: //')"
rm -f "$out"

echo "== check 5/5: the built wheel actually contains the package"
tmpd=$(mktemp -d)
python3 -m build --wheel --outdir "$tmpd" -q >/dev/null 2>&1
python3 - "$tmpd" <<'PY'
import glob, shutil, sys, zipfile
w = glob.glob(sys.argv[1] + "/*.whl")[0]
inside = [n for n in zipfile.ZipFile(w).namelist() if n.startswith("tokentracker/") and n.endswith(".py")]
shutil.rmtree(sys.argv[1], ignore_errors=True)
if len(inside) < 5:
    sys.exit("wheel has %d module file(s); the package is missing" % len(inside))
PY
[ $? -eq 0 ] || fail "wheel is missing the package; an editable install hides this"
echo "wheel contains the package"

echo "ALL CHECKS PASSED"
