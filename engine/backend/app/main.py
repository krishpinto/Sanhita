from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.db import init_db
from app.routers import answers, encounters, opinions, protocols, results


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title="Vitalis Protocol Engine", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(encounters.router)
app.include_router(answers.router)
app.include_router(protocols.router)
app.include_router(results.router)
app.include_router(opinions.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
