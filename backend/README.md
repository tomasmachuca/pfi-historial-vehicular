# Backend - Historial 0km

API en FastAPI que orquesta autenticacion, almacenamiento de evidencias en Cloudflare R2, hashing SHA-256 y registro on-chain en Polygon mediante Web3.py.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate         # Linux/Mac
pip install -r requirements.txt
cp .env.example .env
# Editar .env con tus credenciales
```

## Crear el esquema en la base

```bash
psql "$DATABASE_URL" -f sql/schema.sql
```

(Si usas Supabase, podes pegar el SQL en el editor de la consola).

## Levantar la API

```bash
uvicorn app.main:app --reload --port 8000
```

OpenAPI UI: http://localhost:8000/docs

## Crear una concesionaria (admin)

```bash
curl -X POST http://localhost:8000/admin/concesionarias \
  -H "X-Admin-Token: <primeros 32 chars de JWT_SECRET>" \
  -H "Content-Type: application/json" \
  -d '{"nombre":"Toyota Centro","email":"toyota@demo.com","password":"secreta"}'
```

El endpoint:
1. Genera una wallet nueva.
2. La autoriza on-chain (admin firma `autorizarConcesionaria`).
3. La fondea con 0.5 MATIC desde la wallet admin.
4. Guarda la PK cifrada en la DB.
