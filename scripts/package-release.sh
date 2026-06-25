#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

VERSION=${GITHUB_REF_NAME:-${1:-dev}}
PLATFORMS=(
  "darwin amd64"
  "darwin arm64"
  "linux amd64"
  "linux arm64"
)

rm -rf dist
mkdir -p dist

for platform in "${PLATFORMS[@]}"; do
  read -r GOOS GOARCH <<<"$platform"
  name="herdr-token-dashboard_${VERSION}_${GOOS}_${GOARCH}"
  workdir="dist/$name"
  mkdir -p "$workdir/bin"

  echo "building $GOOS/$GOARCH"
  GOOS=$GOOS GOARCH=$GOARCH CGO_ENABLED=0 go build -o "$workdir/bin/token-dashboard" ./cmd/token-dashboard

  cp herdr-plugin.toml README.md LICENSE "$workdir/"
  cp -R docs "$workdir/docs"
  cp -R scripts "$workdir/scripts"

  tar -C dist -czf "dist/$name.tar.gz" "$name"
  rm -rf "$workdir"
done

(
  cd dist
  shasum -a 256 *.tar.gz > checksums.txt
)
