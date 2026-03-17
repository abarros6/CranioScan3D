#!/usr/bin/env bash
# =============================================================================
# CranioScan3D — quick smoke test script
#
# Runs a fast end-to-end dry-run of the pipeline and the full pytest suite
# to verify that the Python environment is correctly set up.
#
# Usage:
#   bash scripts/run_quick_test.sh
#   bash scripts/run_quick_test.sh --tests-only
#   bash scripts/run_quick_test.sh --dry-run-only
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"

# ── Colours ────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'
info()  { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }

# ── Argument parsing ────────────────────────────────────────────────────────
RUN_TESTS=true
RUN_DRY_RUN=true

for arg in "$@"; do
    case "$arg" in
        --tests-only)   RUN_DRY_RUN=false ;;
        --dry-run-only) RUN_TESTS=false ;;
        --help|-h)
            echo "Usage: $0 [--tests-only | --dry-run-only]"
            exit 0
            ;;
    esac
done

# ── Resolve Python ──────────────────────────────────────────────────────────
if [[ -f "$VENV_PYTHON" ]]; then
    PYTHON="$VENV_PYTHON"
    info "Using virtualenv Python: $PYTHON"
elif command -v python3 &>/dev/null; then
    PYTHON="python3"
    warn "Virtualenv not found; using system python3. Run 'make setup' first."
else
    error "No Python interpreter found. Run 'make setup' to create the virtualenv."
    exit 1
fi

# ── Change to project root ──────────────────────────────────────────────────
cd "$PROJECT_ROOT"

echo ""
echo "============================================================"
echo "  CranioScan3D quick test"
echo "  Project: $PROJECT_ROOT"
echo "  Python:  $($PYTHON --version)"
echo "============================================================"
echo ""

PASS_COUNT=0
FAIL_COUNT=0

# ── Section 1: Import smoke test ───────────────────────────────────────────
info "Smoke test: verifying Python package imports..."

$PYTHON - <<'PYEOF'
import sys

modules = [
    "cranioscan",
    "cranioscan.config",
    "cranioscan.pipeline",
    "cranioscan.extraction.frame_extractor",
    "cranioscan.reconstruction.sparse",
    "cranioscan.reconstruction.undistort",
    "cranioscan.reconstruction.dense",
    "cranioscan.mesh.processing",
    "cranioscan.mesh.scale",
    "cranioscan.landmarks.curvature",
    "cranioscan.landmarks.detector",
    "cranioscan.measurement.cranial_indices",
    "cranioscan.measurement.report",
    "cranioscan.utils.logging",
    "cranioscan.utils.shell",
    "cranioscan.utils.io",
    "cranioscan.utils.validation",
]

failed = []
for m in modules:
    try:
        __import__(m)
        print(f"  OK  {m}")
    except Exception as e:
        print(f"  FAIL {m}: {e}", file=sys.stderr)
        failed.append(m)

if failed:
    print(f"\n{len(failed)} import(s) failed!", file=sys.stderr)
    sys.exit(1)
else:
    print(f"\nAll {len(modules)} imports OK.")
PYEOF

PASS_COUNT=$((PASS_COUNT + 1))
info "Import smoke test PASSED"

# ── Section 2: Config loading test ─────────────────────────────────────────
info "Smoke test: loading default and fast configs..."

$PYTHON - <<'PYEOF'
from cranioscan.config import Config

cfg_default = Config.from_yaml("configs/default.yaml")
assert cfg_default.extraction.frame_interval == 15
assert cfg_default.mesh.poisson_depth == 9
assert cfg_default.reconstruction.colmap_bin == "colmap"

cfg_fast = Config.from_yaml("configs/fast.yaml")
assert cfg_fast.extraction.frame_interval == 30
assert cfg_fast.dense.refine_mesh == False
assert cfg_fast.extraction.resize_max_dim == 1280

# Test override mechanism
cfg_override = Config.from_yaml("configs/default.yaml", overrides={"mesh.poisson_depth": 5})
assert cfg_override.mesh.poisson_depth == 5

print("Config loading: OK")
PYEOF

PASS_COUNT=$((PASS_COUNT + 1))
info "Config loading test PASSED"

# ── Section 3: Pytest suite ─────────────────────────────────────────────────
if [[ "$RUN_TESTS" == "true" ]]; then
    echo ""
    info "Running pytest test suite..."
    echo "------------------------------------------------------------"

    if $PYTHON -m pytest tests/ -v --tb=short; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "------------------------------------------------------------"
        info "pytest suite PASSED"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "------------------------------------------------------------"
        error "pytest suite FAILED"
    fi
fi

# ── Section 4: Pipeline dry run ────────────────────────────────────────────
if [[ "$RUN_DRY_RUN" == "true" ]]; then
    echo ""
    info "Running pipeline dry-run (no COLMAP/OpenMVS required)..."
    echo "------------------------------------------------------------"

    FAKE_VIDEO="/tmp/cranioscan_test_video.mp4"

    # Create a minimal valid mp4 for the dry-run argument (won't be read)
    if [[ ! -f "$FAKE_VIDEO" ]]; then
        $PYTHON - <<PYEOF
import cv2, numpy as np
fourcc = cv2.VideoWriter_fourcc(*"mp4v")
writer = cv2.VideoWriter("$FAKE_VIDEO", fourcc, 30.0, (320, 240))
rng = np.random.default_rng(0)
for _ in range(60):
    writer.write(rng.integers(0, 256, (240, 320, 3), dtype=np.uint8))
writer.release()
print("Created test video: $FAKE_VIDEO")
PYEOF
    fi

    if $PYTHON -m cranioscan.pipeline \
        --input "$FAKE_VIDEO" \
        --output-dir /tmp/cranioscan_dry_run \
        --config configs/fast.yaml \
        --dry-run; then
        PASS_COUNT=$((PASS_COUNT + 1))
        echo "------------------------------------------------------------"
        info "Pipeline dry-run PASSED"
    else
        FAIL_COUNT=$((FAIL_COUNT + 1))
        echo "------------------------------------------------------------"
        error "Pipeline dry-run FAILED"
    fi
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "============================================================"
if [[ "$FAIL_COUNT" -eq 0 ]]; then
    echo -e "  ${GREEN}All $PASS_COUNT checks PASSED${NC}"
    echo "  CranioScan3D environment is correctly set up."
    echo "  Ready to run: cranioscan --input <video.mp4>"
else
    echo -e "  ${RED}$FAIL_COUNT check(s) FAILED, $PASS_COUNT passed${NC}"
    echo "  Fix the errors above before running on real data."
fi
echo "============================================================"
echo ""

[[ "$FAIL_COUNT" -eq 0 ]]
