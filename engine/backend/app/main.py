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

# The web app and the API are deployed to different hosts, so every request
# the browser makes is cross-origin and only happens if this allows it.
#
# allow_credentials is off because nothing here rides on a cookie -- an
# encounter is identified by a bearer token the client sends explicitly. That
# also means allow_origins can safely be widened in a pinch, which it cannot
# be when credentials are on.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_origin_regex=settings.cors_origin_regex,
    allow_credentials=False,
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
