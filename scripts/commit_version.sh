#!/bin/bash
# Script para padronizar commits e versionamento semântico (v0.1, v0.2, ...)
# Uso: ./scripts/commit_version.sh "Mensagem do commit"

set -euo pipefail

VERSION_FILE="VERSION"
if [ ! -f "$VERSION_FILE" ]; then
    echo "0.1" > "$VERSION_FILE"
fi

# Lê versão atual
CUR_VERSION=$(cat "$VERSION_FILE")
IFS='.' read -r MAJOR MINOR <<< "$CUR_VERSION"

# Incrementa versão minor
NEW_MINOR=$((MINOR + 1))
NEW_VERSION="$MAJOR.$NEW_MINOR"

# Atualiza arquivo de versão
echo "$NEW_VERSION" > "$VERSION_FILE"

# Padroniza mensagem de commit
MSG="[v$NEW_VERSION] $1"

git add .
git commit -m "$MSG"
git tag "v$NEW_VERSION"

echo "Commit realizado e versão atualizada para v$NEW_VERSION"
