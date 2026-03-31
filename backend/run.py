import os

from app.main import app


if __name__ == "__main__":
    import uvicorn

    host = (os.getenv("MARKETPLACE_HOST") or "0.0.0.0").strip() or "0.0.0.0"
    port = int((os.getenv("MARKETPLACE_PORT") or "8080").strip() or "8080")
    reload_enabled = (os.getenv("MARKETPLACE_RELOAD") or "").strip().lower() in {"1", "true", "yes", "on"}
    uvicorn.run("app.main:app", host=host, port=port, reload=reload_enabled)
