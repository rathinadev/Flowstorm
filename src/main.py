"""FlowStorm - Self-Healing Stream Processing Engine."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="FlowStorm",
    description="Self-healing, self-optimizing real-time stream processing engine",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok", "engine": "flowstorm", "version": "0.1.0"}
