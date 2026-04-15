import uvicorn
from fastapi import FastAPI
from src.models.domain_core import init_db, seed_db
from src.views.api import router as api_router
import os

PORT = os.getenv("PORT", "").strip()
app = FastAPI(title="Telegram Bot API", version="1.0.0")

@app.on_event("startup")
async def on_startup() -> None:
	# Cria as tabelas e popula dados de teste, se necessário
	init_db()
	seed_db()

app.include_router(api_router, prefix="/api")

if __name__ == "__main__":

	uvicorn.run(
		"main:app",
		host="0.0.0.0",
		port=int(PORT) if PORT.isdigit() else 3000,
		reload=True,
	)

