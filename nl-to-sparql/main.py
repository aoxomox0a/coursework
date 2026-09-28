"""
Main entry point for NL-to-SPARQL system.
Run with: python main.py index     (runs indexing pipeline)
          python main.py api       (starts API server)
"""

import argparse
import asyncio


def run_api():
    from api.main import app
    import uvicorn
    from config.settings import API_HOST, API_PORT

    uvicorn.run(app, host=API_HOST, port=API_PORT)


async def run_index():
    from config.settings import SPARQL_ENDPOINT
    from src.indexing.pipeline import run_indexing_pipeline

    await run_indexing_pipeline(custom_endpoint=SPARQL_ENDPOINT)


def main():
    parser = argparse.ArgumentParser(description="NL-to-SPARQL System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    subparsers.add_parser("index", help="Run indexing pipeline")
    subparsers.add_parser("api", help="Start FastAPI server")

    args = parser.parse_args()

    if args.command == "index":
        asyncio.run(run_index())

    elif args.command == "api":
        run_api()
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
