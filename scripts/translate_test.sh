#!/usr/bin/env bash

# Test script for generating SPARQL from NL (using /api/generate-sparql)
# Usage: bash scripts/translate_test.sh

set -euo pipefail

API_URL="http://localhost:8000/api/generate-sparql"

# create temporary file used to store json response
RESPONSE_BODY=$(mktemp)
# event listener to delete temporary file on script exit
trap 'rm -f "$RESPONSE_BODY"' EXIT

echo "Check if FastAPI server is running at $API_URL..."
if ! curl -s -f -o /dev/null "http://localhost:8000/api/status" 2>/dev/null && ! curl -s -o /dev/null "$API_URL" 2>/dev/null; then
    echo -e "\033[1;31mError: FastAPI server is not reachable. Did you run 'uv run python main.py api'?\033[0m"
    exit 1
fi

echo -e "\033[1;32mServer is up. Beginning SPARQL generation tests...\033[0m\n"

QUESTIONS=(
  "Who directed the movie Inception?"
  "Who wrote The Great Gatsby?"
  "What is the capital of France?"
  "When was Barack Obama born?"
  "Where is the Eiffel Tower located?"
  "How many people live in Berlin?"
  "What is the highest mountain in the world?"
  "Which country has the most population?"
)

SUCCESS_COUNT=0
FAIL_COUNT=0

for q in "${QUESTIONS[@]}"; do
  echo -e "\033[1;34mQuestion:\033[0m $q"
  
  # Capture the HTTP status code and the body separately for better error handling
  HTTP_STATUS=$(curl -s -o "$RESPONSE_BODY" -w "%{http_code}" -X POST "$API_URL" \
       -H "Content-Type: application/json" \
       -d "{\"question\": \"$q\"}")

  if [ "$HTTP_STATUS" -ne 200 ]; then
      echo -e "\033[1;31mRequest failed with HTTP $HTTP_STATUS\033[0m"
      jq . "$RESPONSE_BODY" 2>/dev/null || cat "$RESPONSE_BODY"
      ((FAIL_COUNT++))
  else
      # Extract and display the SPARQL query from response
      SPARQL=$(jq -r '.sparql_query' "$RESPONSE_BODY")
      echo -e "\033[1;32mSPARQL Query:\033[0m"
      echo "$SPARQL"
      ((SUCCESS_COUNT++))
  fi
  
  echo "--------------------------------------------------"
  # Sleep for a second to avoid rate-limiting your LLM API during testing
  sleep 1 
done

echo -e "\n\033[1;32mSPARQL generation tests completed.\033[0m"
echo -e "✓ Success: $SUCCESS_COUNT | ✗ Failed: $FAIL_COUNT"

