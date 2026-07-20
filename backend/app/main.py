from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api import auth, vehiculos, servicios, publico, admin

# Orígenes explícitos (sin barra final: el navegador no manda trailing slash en Origin)
_cors_origins = [
    settings.FRONTEND_ORIGIN.rstrip("/"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://[::1]:5173",
]
_cors_origins = list(dict.fromkeys(o for o in _cors_origins if o))

app = FastAPI(
    title="Historial 0km - API",
    description="API del sistema de historial vehicular verificable en blockchain (Polygon).",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    # Vite a veces abre con ::1 u otro puerto; solo hosts locales
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {"ok": True, "service": "historial-0km", "version": app.version}


@app.get("/health")
def health():
    return {"status": "ok"}


app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(vehiculos.router)
app.include_router(servicios.router)
app.include_router(publico.router)
