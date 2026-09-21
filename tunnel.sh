#!/usr/bin/env bash
# Start Cloudflare Tunnel for FlatSplit.
#
# Makes your FlatSplit server accessible anywhere from mobile data / outside Wi-Fi.
#
# Usage:
#   ./tunnel.sh
#
set -euo pipefail

echo "================================================="
echo " FlatSplit - Cloudflare Tunnel"
echo "================================================="
echo

if ! command -v cloudflared >/dev/null 2>&1; then
  echo "[!] 'cloudflared' is not installed."
  echo
  if [ -d "/data/data/com.termux" ]; then
    echo "To install on Termux, run:"
    echo "  pkg update && pkg install cloudflared"
    echo
    echo "If package is not found, enable the TUR repo first:"
    echo "  pkg install tur-repo && pkg install cloudflared"
  else
    echo "To install cloudflared:"
    echo "  https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/"
  fi
  echo
  exit 1
fi

echo "Starting Cloudflare quick tunnel to http://127.0.0.1:8000 ..."
echo "Look for the URL below ending in .trycloudflare.com :"
echo "-------------------------------------------------"
echo

exec cloudflared tunnel --url http://127.0.0.1:8000
