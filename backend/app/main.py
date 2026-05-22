from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.config import settings
from app.routes import documents, chat, evaluation, auth, vendors

app = FastAPI(
    title=settings.app_name,
    description="Enterprise Knowledge Assistant — a full-stack RAG application "
                "using LangChain, pgvector, and FastAPI.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal server error: {str(exc)}"},
    )


@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}


app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(evaluation.router)
app.include_router(auth.router)
app.include_router(vendors.router)
