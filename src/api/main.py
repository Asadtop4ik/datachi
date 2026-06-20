"""FastAPI ilova. Faza 0: /health. /chat Faza 4'da qo'shiladi."""

from __future__ import annotations

from fastapi import FastAPI

app = FastAPI(title="Datachi AI Analytics")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
