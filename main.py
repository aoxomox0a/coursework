"""
Main entry point for NL-to-SPARQL system.
Run with: python main.py index     (runs indexing pipeline)
          python main.py api       (starts API server)
"""
import argparse


def main():
    parser = argparse.ArgumentParser(description="NL-to-SPARQL System")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # Index command
    subparsers.add_parser("index", help="Run indexing pipeline")

    # API command
    subparsers.add_parser("api", help="Start FastAPI server")

    args = parser.parse_args()

    if args.command == "index":
        print("Running indexing pipeline...")
        from src.indexing.pipeline import run_indexing_pipeline
        run_indexing_pipeline()

    elif args.command == "api":
        print("Starting API server...")
        from api.main import app
        import uvicorn
        from config.settings import API_HOST, API_PORT
        uvicorn.run(app, host=API_HOST, port=API_PORT)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
