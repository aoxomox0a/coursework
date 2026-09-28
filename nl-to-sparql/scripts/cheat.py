import asyncio
import httpx

TARGET_ENDPOINT = "https://api.parliament.uk/sparql"

CHEAT_CODE_QUERY = """
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?property ?object WHERE {
  # Find a node that has the name Keir Starmer
  ?person ?labelProp "Keir Starmer" .
  
  # Get all properties and objects attached to him
  ?person ?property ?object .
  
  # Only look at Parliament-specific properties
  FILTER(STRSTARTS(STR(?property), "https://id.parliament.uk/schema/"))
} 
LIMIT 20
"""


async def run_cheat_code():
    print(f"🕵️  Scanning {TARGET_ENDPOINT} for top properties...")

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                TARGET_ENDPOINT,
                params={"query": CHEAT_CODE_QUERY, "format": "json"},
                headers={"Accept": "application/sparql-results+json"},
                timeout=60.0,
            )

            if response.status_code != 200:
                print(f"❌ Error: Endpoint returned {response.status_code}")
                print(response.text)
                return

            data = response.json()
            bindings = data.get("results", {}).get("bindings", [])

            if not bindings:
                print("⚠️ No properties found. Is the database empty?")
                return

            print("\n🏆 Top 15 Most Used Properties:")
            print("=" * 60)
            print(f"{'RANK':<5} | {'COUNT':<10} | {'PROPERTY URI'}")
            print("-" * 60)

            for i, row in enumerate(bindings, 1):
                prop_uri = row.get("property", {}).get("value", "Unknown")
                count = row.get("count", {}).get("value", "0")
                print(f"{i:<5} | {count:<10} | {prop_uri}")

            print("=" * 60)
            print(
                "\n💡 Pro-Tip: Look at the last word of these URIs (e.g., 'amenity', 'city')."
            )
            print(
                "Use those exact words in your natural language questions to test the LLM!"
            )

        except Exception as e:
            print(f"❌ Failed to connect or execute: {e}")


if __name__ == "__main__":
    asyncio.run(run_cheat_code())
