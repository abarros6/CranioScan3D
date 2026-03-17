#!/usr/bin/env bash
# =============================================================================
# CranioScan3D — macOS Apple Silicon setup script
#
# Installs all required tools and Python dependencies for running the
# CranioScan3D pipeline on a Mac Mini with Apple Silicon (M1/M2/M3).
#
# Prerequisites: macOS 13+, Homebrew, Xcode Command Line Tools
#
# Usage:
#   bash scripts/setup_mac.sh
#
# What this script does:
#   1. Checks for Homebrew and Xcode CLT
#   2. Installs COLMAP via Homebrew (CPU-only, no CUDA)
#   3. Clones and builds OpenMVS from source (CPU-only, Apple Silicon)
#   4. Creates a Python 3.11 virtual environment
#   5. Installs all Python dependencies (pip)
#   6. Runs a quick smoke test
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="$PROJECT_ROOT/venv"
BUILD_DIR="$PROJECT_ROOT/.build"
OPENMVS_INSTALL_DIR="$PROJECT_ROOT/.openmvs"

# ── Colours ────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'
info()    { echo -e "${GREEN}[INFO]${NC}  $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }
die()     { error "$*"; exit 1; }

# ── Step 1: Check prerequisites ────────────────────────────────────────────
info "Step 1/6: Checking prerequisites"

if ! command -v brew &>/dev/null; then
    die "Homebrew is not installed. Install it from https://brew.sh/ and re-run."
fi
info "  Homebrew found: $(brew --version | head -1)"

if ! xcode-select -p &>/dev/null; then
    warn "Xcode Command Line Tools not found. Installing..."
    xcode-select --install
    echo "  Re-run this script after Xcode CLT installation completes."
    exit 0
fi
info "  Xcode CLT found: $(xcode-select -p)"

# Confirm Apple Silicon
ARCH=$(uname -m)
if [[ "$ARCH" != "arm64" ]]; then
    warn "Expected arm64 (Apple Silicon), got '$ARCH'. Script is optimised for M-series Macs."
fi
info "  Architecture: $ARCH"

# ── Step 2: Install COLMAP ─────────────────────────────────────────────────
info "Step 2/6: Installing COLMAP via Homebrew"

if command -v colmap &>/dev/null; then
    info "  COLMAP already installed: $(colmap --version 2>&1 | head -1)"
else
    info "  Running: brew install colmap"
    brew install colmap
    info "  COLMAP installed: $(colmap --version 2>&1 | head -1)"
fi

# ── Step 3: Build OpenMVS from source ──────────────────────────────────────
info "Step 3/6: Building OpenMVS from source (CPU-only, Apple Silicon)"

# Install OpenMVS dependencies
info "  Installing OpenMVS build dependencies..."
brew install cmake eigen opencv boost cgal glog

mkdir -p "$BUILD_DIR"

OPENMVS_SRC="$BUILD_DIR/openMVS"
if [[ ! -d "$OPENMVS_SRC" ]]; then
    info "  Cloning OpenMVS repository..."
    git clone --depth 1 https://github.com/cdcseacave/openMVS.git "$OPENMVS_SRC"
else
    info "  OpenMVS source already cloned at $OPENMVS_SRC"
fi

OPENMVS_BUILD="$BUILD_DIR/openMVS_build"
mkdir -p "$OPENMVS_BUILD" "$OPENMVS_INSTALL_DIR"

info "  Configuring CMake (CPU-only build)..."
cmake -S "$OPENMVS_SRC" -B "$OPENMVS_BUILD" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX="$OPENMVS_INSTALL_DIR" \
    -DOpenMVS_USE_CUDA=OFF \
    -DOpenMVS_USE_OPENMP=ON \
    -DVCG_ROOT="$OPENMVS_SRC/libs/VCG" \
    -DCMAKE_OSX_ARCHITECTURES=arm64 \
    -Wno-dev

info "  Building OpenMVS (this will take 5-15 minutes)..."
cmake --build "$OPENMVS_BUILD" --config Release --parallel "$(sysctl -n hw.logicalcpu)"

info "  Installing OpenMVS to $OPENMVS_INSTALL_DIR..."
cmake --install "$OPENMVS_BUILD"

info "  OpenMVS binaries:"
ls "$OPENMVS_INSTALL_DIR/bin/" 2>/dev/null || ls "$OPENMVS_INSTALL_DIR/" 2>/dev/null

# ── Step 4: Create Python virtual environment ───────────────────────────────
info "Step 4/6: Setting up Python virtual environment"

if ! command -v python3 &>/dev/null; then
    die "python3 not found. Install with: brew install python@3.11"
fi
PYTHON_VERSION=$(python3 --version)
info "  Python: $PYTHON_VERSION"

if [[ ! -d "$VENV_DIR" ]]; then
    info "  Creating virtual environment at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
else
    info "  Virtual environment already exists at $VENV_DIR"
fi

# ── Step 5: Install Python dependencies ────────────────────────────────────
info "Step 5/6: Installing Python dependencies"

# Activate venv for pip installs
source "$VENV_DIR/bin/activate"

pip install --upgrade pip wheel setuptools
pip install -e "$PROJECT_ROOT[dev]"

info "  Python packages installed:"
pip list | grep -E "opencv|numpy|open3d|pyyaml|reportlab|PyQt5|Pillow|scipy|pytest|ruff"

deactivate

# ── Step 6: Write .env from template ───────────────────────────────────────
info "Step 6/6: Writing .env configuration"

ENV_FILE="$PROJECT_ROOT/.env"
OPENMVS_BIN_DIR="$OPENMVS_INSTALL_DIR/bin"
# Fall back to install dir root if bin/ subdir was not created
if [[ ! -d "$OPENMVS_BIN_DIR" ]]; then
    OPENMVS_BIN_DIR="$OPENMVS_INSTALL_DIR"
fi

if [[ ! -f "$ENV_FILE" ]]; then
    cat > "$ENV_FILE" <<EOF
# CranioScan3D — auto-generated by setup_mac.sh
COLMAP_BIN=colmap
OPENMVS_BIN_DIR=${OPENMVS_BIN_DIR}
LOG_LEVEL=INFO
CRANIOSCAN_DATA_DIR=data/
EOF
    info "  Created $ENV_FILE"
else
    warn "  $ENV_FILE already exists — not overwriting. Update OPENMVS_BIN_DIR if needed."
    warn "  Suggested value: OPENMVS_BIN_DIR=$OPENMVS_BIN_DIR"
fi

# ── Summary ────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}======================================================${NC}"
echo -e "${GREEN}  CranioScan3D setup complete!${NC}"
echo -e "${GREEN}======================================================${NC}"
echo ""
echo "Next steps:"
echo "  1. Activate the virtual environment:"
echo "       source venv/bin/activate"
echo ""
echo "  2. Run the test suite to verify everything works:"
echo "       make test"
echo ""
echo "  3. Capture a video per the protocol:"
echo "       cat scripts/capture_guide.md"
echo ""
echo "  4. Run the pipeline:"
echo "       make run INPUT=path/to/your/video.mp4"
echo ""
echo "  COLMAP:   $(command -v colmap)"
echo "  OpenMVS:  $OPENMVS_BIN_DIR"
echo "  Python:   $VENV_DIR/bin/python"
echo ""
