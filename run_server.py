import uvicorn
import sys
import os
import argparse

if __name__ == "__main__":
    default_port = int(os.environ.get("PORT", 8080))
    default_host = os.environ.get("HOST", "0.0.0.0")

    parser = argparse.ArgumentParser(description="Wishlist Discovery Engine Server")
    parser.add_argument("--port", type=int, default=default_port, help="Port to run the dashboard server on")
    parser.add_argument("--host", type=str, default=default_host, help="Host address")
    args = parser.parse_args()

    cwd = os.path.dirname(os.path.abspath(__file__))
    if cwd not in sys.path:
        sys.path.insert(0, cwd)
        
    print(f"Importing FastAPI app...", flush=True)
    from dashboard.api import app
    print(f"Starting Uvicorn server on http://{args.host}:{args.port}", flush=True)
    uvicorn.run(app, host=args.host, port=args.port)
