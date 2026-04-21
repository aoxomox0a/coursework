#!/usr/bin/env bash

# Test script for SPARQL to Natural Language explanation API
# Tests the /api/explain endpoint with various SPARQL queries

# abort if error
set -euo pipefail

API_URL="http://localhost:8000/api/explain"

# create temporary file used to store json response
RESPONSE_BODY=$(mktemp)
# event listener to delete temporary file on script exit
trap 'rm -f "$RESPONSE_BODY"' EXIT

echo "Check if FastAPI server is running at $API_URL..."
if ! curl -s -f -o /dev/null "http://localhost:8000/health"; then
    echo -e "\033[1;31mError: FastAPI server is not reachable. Did you run 'uv run python main.py api'?\033[0m"
    exit 1
fi

echo -e "\033[1;32mServer is up. Beginning SPARQL explanation tests...\033[0m\n"

# Array of SPARQL queries to test
QUERIES=(
  "SELECT ?capital WHERE { <http://dbpedia.org/resource/France> <http://dbpedia.org/ontology/capital> ?capital . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?director WHERE { <http://dbpedia.org/resource/Inception> dbo:director ?director . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?author WHERE { <http://dbpedia.org/resource/The_Great_Gatsby> dbo:author ?author . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?capital WHERE { ?country dbo:capital ?capital . FILTER (?country = <http://dbpedia.org/resource/Germany>) . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?birthDate WHERE { <http://dbpedia.org/resource/Barack_Obama> dbo:birthDate ?birthDate . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?location WHERE { <http://dbpedia.org/resource/Eiffel_Tower> dbo:location ?location . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?founded WHERE { <http://dbpedia.org/resource/Berlin> dbo:foundingDate ?founded . }"
  
  "PREFIX dbo: <http://dbpedia.org/ontology/> SELECT ?population WHERE { ?city dbo:populationTotal ?population . FILTER (?city = <http://dbpedia.org/resource/New_York_City>) . }"
)

for query in "${QUERIES[@]}"; do
  echo -e "\033[1;34mSPARQL Query:\033[0m"
  echo "$query"
  echo ""
  
  # Capture the HTTP status code and the body separately
  HTTP_STATUS=$(curl -s -o "$RESPONSE_BODY" -w "%{http_code}" -X POST "$API_URL" \
       -H "Content-Type: application/json" \
       -d "{\"sparql_query\": $(echo "$query" | jq -R .)}")

  if [ "$HTTP_STATUS" -ne 200 ]; then
      echo -e "\033[1;31mRequest failed with HTTP $HTTP_STATUS\033[0m"
      jq . "$RESPONSE_BODY" 2>/dev/null || cat "$RESPONSE_BODY"
  else
      # Extract and pretty print the explanation
      echo -e "\033[1;32mExplanation:\033[0m"
      jq -r '.explanation' "$RESPONSE_BODY" 2>/dev/null || cat "$RESPONSE_BODY"
      echo ""
  fi
  
  echo "--------------------------------------------------"
  # Sleep for a second to avoid rate-limiting the LLM API
  sleep 1 
done

echo -e "\033[1;32mAll SPARQL explanation tests completed.\033[0m"
