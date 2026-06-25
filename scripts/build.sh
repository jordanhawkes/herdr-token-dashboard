#!/usr/bin/env bash
set -euo pipefail
mkdir -p bin
go build -o bin/token-dashboard ./cmd/token-dashboard
