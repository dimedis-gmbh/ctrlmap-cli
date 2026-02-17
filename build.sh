#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUILD_DIR="${SCRIPT_DIR}/.build_tmp"
DIST_DIR="${SCRIPT_DIR}/dist"
PYTHON="${PYTHON:-python3}"

echo "Cleaning previous build artifacts..."
rm -rf "${SCRIPT_DIR}/build" "${BUILD_DIR}" "${DIST_DIR}"

echo "Creating build directory..."
mkdir -p "${BUILD_DIR}" "${DIST_DIR}"

VERSION="${VERSION:-0.0.0-src}"

echo "Copying source code..."
cp -r "${SCRIPT_DIR}/ctrlmap_cli" "${BUILD_DIR}/ctrlmap_cli"

echo "Baking version: ${VERSION}"
INIT_PY="${BUILD_DIR}/ctrlmap_cli/__init__.py"
sed "s/0.0.0-src/${VERSION}/" "${INIT_PY}" > "${INIT_PY}.tmp"
mv "${INIT_PY}.tmp" "${INIT_PY}"

echo "Installing dependencies..."
"${PYTHON}" -m pip install \
    requests PyYAML markdownify \
    --target "${BUILD_DIR}" \
    --quiet

echo "Building zipapp..."
"${PYTHON}" -m zipapp \
    "${BUILD_DIR}" \
    --output "${DIST_DIR}/ctrlmap-cli" \
    --python "/usr/bin/env python3" \
    --main "ctrlmap_cli.__main__:main"

chmod +x "${DIST_DIR}/ctrlmap-cli"

echo "Cleaning up..."
rm -rf "${BUILD_DIR}"

echo "Done: ${DIST_DIR}/ctrlmap-cli"
