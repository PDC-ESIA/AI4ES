#!/usr/bin/env bash
# Compila os binários estáticos do probe para linux/amd64 e linux/arm64.
#
# São ARTEFATOS DE BUILD, não compilados em runtime pelo harness: o harness só
# precisa dos binários prontos em disco (ver shared/tools/probe.py). Go NÃO é
# necessário onde o harness roda — só aqui, onde os binários são construídos.
#
# Preferência: Go local (>=1.21). Fallback automático: imagem `golang` no
# Docker, para ambientes sem Go instalado.
set -euo pipefail
cd "$(dirname "$0")"

build_local() {
  CGO_ENABLED=0 GOOS=linux GOARCH=amd64 go build -o probe-linux-amd64 .
  CGO_ENABLED=0 GOOS=linux GOARCH=arm64 go build -o probe-linux-arm64 .
}

build_docker() {
  docker run --rm -v "$PWD":/src -w /src \
    -e CGO_ENABLED=0 -e GOOS=linux \
    golang:1.22-alpine sh -c \
    'GOARCH=amd64 go build -o probe-linux-amd64 . && GOARCH=arm64 go build -o probe-linux-arm64 .'
}

if command -v go >/dev/null 2>&1; then
  echo "Compilando com Go local ($(go version))..."
  build_local
else
  echo "Go não encontrado no host; compilando via imagem golang no Docker..."
  build_docker
fi

echo "OK: probe-linux-amd64, probe-linux-arm64"
file probe-linux-amd64 probe-linux-arm64 2>/dev/null || true
