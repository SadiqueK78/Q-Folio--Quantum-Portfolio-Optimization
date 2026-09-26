# Vercel entrypoint: Vercel's FastAPI runtime looks for `app` in index.py.
from app.api.main import app  # noqa: F401
