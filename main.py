"""Application entrypoint.

This module re-exports the FastAPI application configured in ``main_db`` so
that tooling expecting ``main:app`` continues to work while the project uses
the single, database-backed implementation.
"""

from main_db import app

__all__ = ["app"]


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8011)
