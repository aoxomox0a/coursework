#!/usr/bin/env bash

# abort if error
# set -e: abort if error.
# set -u: abort if undeclared variable
# set -o pipefail: abort if command inside pipeline fails. 
set -euo pipefail

API_URL="http://localhost:8000/api/answer"

# create temporary file used to store json response so we don't have to parse it
RESPONSE_BODY=$(mktemp)
# event listener to delete temporary file on script exit
trap 'rm -f "$RESPONSE_BODY"' EXIT

echo "Check if FastAPI server is running at $API_URL..."
# Send a silent GET request to the root or a health endpoint just to see if the port is open
if ! curl -s -f -o /dev/null "http://localhost:8000/api/status" && ! curl -s -o /dev/null "$API_URL"; then
    echo -e "\033[1;31mError: FastAPI server is not reachable. Did you run 'uv run uvicorn main:app'?\033[0m"
    exit 1
fi

echo -e "\033[1;32mServer is up. Beginning prompt tests...\033[0m\n"

QUESTIONS=(
  "Who directed the movie Inception released in 2010?"
  "Who directed Inception?"
  "Who wrote The Great Gatsby?"
  "What is the capital of France?"
  "When was Barack Obama born?"
  "Where is the Eiffel Tower located?"
)

for q in "${QUESTIONS[@]}"; do
  echo -e "\033[1;34mQuestion:\033[0m $q"
  
  # Capture the HTTP status code and the body separately for better error handling
  HTTP_STATUS=$(curl -s -o "$RESPONSE_BODY" -w "%{http_code}" -X POST "$API_URL" \
       -H "Content-Type: application/json" \
       -d "{\"question\": \"$q\"}")

  if [ "$HTTP_STATUS" -ne 200 ]; then
      echo -e "\033[1;31mRequest failed with HTTP $HTTP_STATUS\033[0m"
      jq . "$RESPONSE_BODY" 2>/dev/null || cat "$RESPONSE_BODY"
      #echo "$RESPONSE_BODY" | jq . || echo "$RESPONSE_BODY"
  else
      # pretty print json using jq
      jq . "$RESPONSE_BODY"
  fi
  
  echo "--------------------------------------------------"
  # Sleep for a second to avoid rate-limiting your LLM API during testing
  sleep 1 
done

echo -e "\033[1;32mAll manual tests completed.\033[0m"
