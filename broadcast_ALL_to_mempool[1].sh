#!/bin/bash
# BROADCAST ALL MESH TX TO MEMPOOL - CURL VERSION
# Total isMy tx: 146
RAW_DIR="./raw"
for txid in $(cat mesh_complete_all_txids_FIXED.txt); do
  if [ -f "$RAW_DIR/${txid}.hex" ]; then
    echo "Broadcasting $txid..."
    curl -s -X POST https://mempool.space/api/tx -H "Content-Type: text/plain" --data-binary @$RAW_DIR/${txid}.hex
    echo ""
    sleep 0.5
  fi
done
