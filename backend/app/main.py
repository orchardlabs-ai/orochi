from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import appointments, auth, calls, patients, schedule, simulator
from .seed import seed

app = FastAPI(title="Orochi", description="HIPAA-conscious clinic voice-agent prototype")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    seed()


@app.get("/api/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(appointments.router, prefix="/api")
app.include_router(calls.router, prefix="/api")
app.include_router(schedule.router, prefix="/api")
app.include_router(simulator.router, prefix="/api")
