from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.routers import approvals, browser_proxy, chat, tasks


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Aquí se podrán inicializar pools de conexión a DB cuando existan
    yield


app = FastAPI(
    title="Rachael – api-core",
    description="Orquestador central: planificador/ejecutor de Rachael.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(chat.router, prefix="/v1", tags=["chat"])
app.include_router(tasks.router, prefix="/v1", tags=["tasks"])
app.include_router(approvals.router, prefix="/v1", tags=["approvals"])
app.include_router(browser_proxy.router, prefix="/internal", tags=["internal"])


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok"}
