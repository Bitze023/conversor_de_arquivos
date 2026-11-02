#!/usr/bin/env bash
# Registra o conversor local no Google Chrome (Native Messaging).
# Uso: bash install.sh ID_DA_EXTENSAO

set -euo pipefail

HOST_NAME="com.mediadownloader.converter"
EXT_ID="${1:-}"

if [[ ! "$EXT_ID" =~ ^[a-p]{32}$ ]]; then
    echo "ERRO: informe o ID da extensão (32 letras de a até p)."
    echo "Uso: bash install.sh ID_DA_EXTENSAO"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HOST_PATH="$SCRIPT_DIR/converter_host.py"
TARGET_DIR="$HOME/.config/google-chrome/NativeMessagingHosts"

if [[ ! -f "$HOST_PATH" ]]; then
    echo "ERRO: converter_host.py não encontrado em $SCRIPT_DIR"
    exit 1
fi

chmod u+x "$HOST_PATH"
mkdir -p "$TARGET_DIR"
mkdir -p "$HOME/MediaConverter/entrada" "$HOME/MediaConverter/saida"

cat > "$TARGET_DIR/$HOST_NAME.json" <<JSON
{
  "name": "$HOST_NAME",
  "description": "Conversor local do YouTube Media Downloader",
  "path": "$HOST_PATH",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://$EXT_ID/"
  ]
}
JSON

echo "Conversor registrado com sucesso!"
echo "Arquivo de registro: $TARGET_DIR/$HOST_NAME.json"
echo "Pasta de entrada: $HOME/MediaConverter/entrada"
echo "Pasta de saída:   $HOME/MediaConverter/saida"