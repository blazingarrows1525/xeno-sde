"""Dev entrypoint for the Kairos CRM API.

    cd apps/crm
    python run.py            # -> http://127.0.0.1:8000  (docs at /docs)

Selects the selector event loop on Windows so asyncpg's SSL transport tears down
cleanly, and makes `app` importable regardless of the launch directory.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, log_level="info")
