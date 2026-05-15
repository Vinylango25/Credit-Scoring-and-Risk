from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from . import models
from .routers import kpis, scoring, loans

# Create all tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Credit Scoring Platform API",
    description="End-to-end credit scoring with ML, CRB, and TransUnion integration",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(kpis.router)
app.include_router(scoring.router)
app.include_router(loans.router)


@app.get("/")
def root():
    return {"message": "Credit Scoring Platform API", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "ok"}
