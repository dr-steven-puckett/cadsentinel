#!/usr/bin/env bash
set -euo pipefail

API_URL="http://127.0.0.1:8000/ingest/dwg"
DRAWING_DIR="/mnt/cadsentinel/drawings"

echo "=== CadSentinel DWG Batch Ingestion ==="
echo "API:     ${API_URL}"
echo "Source:  ${DRAWING_DIR}"
echo

shopt -s nullglob
dwg_files=("${DRAWING_DIR}"/*.dwg)
shopt -u nullglob

if [ ${#dwg_files[@]} -eq 0 ]; then
  echo "No .dwg files found in ${DRAWING_DIR}"
  exit 0
fi

count=${#dwg_files[@]}
echo "Found ${count} DWG file(s) to ingest."
echo

i=0
for f in "${dwg_files[@]}"; do
  i=$((i+1))
  fname=$(basename "$f")
  echo "[$i/${count}] Ingesting: ${fname}"

  # Extra safety: check that the file is readable
  if [[ ! -r "$f" ]]; then
    echo "  ❌ File is not readable or does not exist: $f"
    echo
    continue
  fi

  # Build the -F argument safely, even with spaces/commas/etc.
  printf -v form_arg 'file=@%s' "$f"

  # Do the POST, capturing body + HTTP status code
  response=$(curl -sS -w "%{http_code}" -F "$form_arg" "${API_URL}" || true)
  http_code="${response: -3}"
  body="${response:0:${#response}-3}"

  if [[ "$http_code" == 2* ]]; then
    # Try to extract document_id if jq is available
    if command -v jq >/dev/null 2>&1; then
      doc_id=$(echo "$body" | jq -r '.document_id // empty')
      if [[ -n "$doc_id" ]]; then
        echo "  ✅ Successfully ingested ${fname} (document_id: ${doc_id})"
      else
        echo "  ✅ Successfully ingested ${fname}"
      fi
    else
      echo "  ✅ Successfully ingested ${fname}"
    fi
  else
    echo "  ❌ Failed to ingest ${fname} (HTTP ${http_code})"
    echo "  Response body:"
    echo "$body" | sed 's/^/    /'
  fi

  echo
done

echo "=== DWG batch ingestion completed for ${count} file(s). ==="
