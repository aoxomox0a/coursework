#!/usr/bin/env bash

# Test script for SPARQL-to-NL explanation endpoint
# Usage: bash scripts/explain_test.sh

set -euo pipefail

API_URL="http://localhost:8000/api/generate-nl"

# create temporary file used to store json response
RESPONSE_BODY=$(mktemp)
# event listener to delete temporary file on script exit
trap 'rm -f "$RESPONSE_BODY"' EXIT

echo "Check if FastAPI server is running at $API_URL..."
if ! curl -s -f -o /dev/null "http://localhost:8000/api/status" 2>/dev/null && ! curl -s -o /dev/null "$API_URL" 2>/dev/null; then
    echo -e "\033[1;31mError: FastAPI server is not reachable. Did you run 'uv run python main.py api'?\033[0m"
    exit 1
fi

echo -e "\033[1;32mServer is up. Beginning SPARQL explanation tests...\033[0m\n"

SPARQL_QUERIES=(
  "SELECT ?person WHERE { ?person a dbo:Person . ?person foaf:name \"Barack Obama\"@en . }"
  "SELECT ?film ?director WHERE { ?film dbo:director ?director . ?film dbp:name \"Inception\"@en . }"
  "SELECT ?book ?author WHERE { ?book a dbo:Book . ?book dbo:author ?author . ?book dbp:name \"The Great Gatsby\"@en . }"
  "SELECT ?city ?country WHERE { ?city a dbo:City . ?city dbo:country ?country . ?city dbp:name \"Paris\"@en . }"
  "SELECT ?mountain ?height WHERE { ?mountain a dbo:Mountain . ?mountain dbo:elevation ?height . }"
)

SUCCESS_COUNT=0
FAIL_COUNT=0

for sparql in "${SPARQL_QUERIES[@]}"; do
  echo -e "\033[1;34mSPARQL Query:\033[0m"
  echo "$sparql"
  echo ""
  
  # Capture the HTTP status code and the body separately for better error handling
  HTTP_STATUS=$(curl -s -o "$RESPONSE_BODY" -w "%{http_code}" -X POST "$API_URL" \
       -H "Content-Type: application/json" \
       -d "{\"sparql_query\": \"$sparql\"}")

  if [ "$HTTP_STATUS" -ne 200 ]; then
      echo -e "\033[1;31mRequest failed with HTTP $HTTP_STATUS\033[0m"
      jq . "$RESPONSE_BODY" 2>/dev/null || cat "$RESPONSE_BODY"
      ((FAIL_COUNT++))
  else
      # pretty print json using jq
      jq . "$RESPONSE_BODY"
      ((SUCCESS_COUNT++))
  fi
  
  echo "--------------------------------------------------"
  # Sleep for a second to avoid rate-limiting your LLM API during testing
  sleep 1 
done

echo -e "\n\033[1;32mExplanation tests completed.\033[0m"
echo -e "✓ Success: $SUCCESS_COUNT | ✗ Failed: $FAIL_COUNT"
