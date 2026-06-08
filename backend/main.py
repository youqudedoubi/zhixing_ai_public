from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from code.backend.api.files import router as files_router
from code.backend.api.topics import router as topics_router
from code.backend.api.chat import router as chat_router
from code.backend.api.simulation import router as simulation_router

app = FastAPI(title="知行AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(files_router)
app.include_router(topics_router)
app.include_router(chat_router)
app.include_router(simulation_router)


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(FileNotFoundError)
async def not_found_handler(request: Request, exc: FileNotFoundError):
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(FileExistsError)
async def exists_handler(request: Request, exc: FileExistsError):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.get("/")
def root():
    return {"name": "知行AI", "version": "v1.0", "docs": "/docs"}


@app.get("/api/health")
def health():
    return {"status": "ok"}
