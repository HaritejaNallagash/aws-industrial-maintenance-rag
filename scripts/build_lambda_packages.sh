#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
BUILD_DIR="${REPO_ROOT}/build"

mkdir -p "${BUILD_DIR}"

rm -f "${BUILD_DIR}/ingestion-lambda.zip"
rm -f "${BUILD_DIR}/query-lambda.zip"

WIN_ROOT="$(cygpath -w "${REPO_ROOT}")"
WIN_BUILD="$(cygpath -w "${BUILD_DIR}")"

powershell.exe -NoProfile -Command "
Set-Location '${WIN_ROOT}'
Compress-Archive -Path 'src' -DestinationPath '${WIN_BUILD}\ingestion-lambda.zip' -Force
"

powershell.exe -NoProfile -Command "
Set-Location '${WIN_ROOT}'
Compress-Archive -Path 'src' -DestinationPath '${WIN_BUILD}\query-lambda.zip' -Force
"

echo "Created:"
echo "  ${BUILD_DIR}/ingestion-lambda.zip"
echo "  ${BUILD_DIR}/query-lambda.zip"