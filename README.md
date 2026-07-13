# PFI — Sistema de Historial Vehicular Verificable para 0 km basado en Blockchain

Monorepo del Proyecto Final de Ingeniería (UADE). Integra tres componentes con un
único pipeline de integración continua, análisis de calidad (SonarCloud), análisis
estático de seguridad (CodeQL) y actualización de dependencias (Dependabot).

**Autores:** Machuca, Tomás (LU 1136779) · Perez Grunau, Gonzalo (LU 1137658)
**Tutor:** Sabatino, Pablo Luis Esteban

## Estructura del monorepo

```
pfi-historial-vehicular/
├── backend/       # API FastAPI (Python 3.11)  -> app/, tests/, requirements.txt
├── frontend/      # Interfaz React (Vite + Vitest)
├── contracts/     # Smart contracts Solidity (Hardhat)
├── .github/       # Pipeline de CI, Dependabot y plantilla de PR
└── sonar-project.properties
```

## Cómo correr cada componente

### Backend
```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload      # servidor de desarrollo
pytest --cov=app                   # tests con cobertura
```

### Frontend
```bash
cd frontend
npm install
npm run dev                        # servidor de desarrollo
npm run lint                       # linter
npm test -- --coverage             # tests con cobertura
```

### Contracts
```bash
cd contracts
npm install
npx hardhat compile                # compila los contratos
npx hardhat test                   # tests de los contratos
```

## Flujo de trabajo

Todo desarrollo sale de `develop` en ramas `feature/nombre-tarea` y vuelve por Pull
Request. El merge queda bloqueado hasta que pasen los jobs del pipeline, el Quality
Gate de SonarCloud y CodeQL, y haya una aprobación del compañero. Cuando `develop`
está estable para una entrega o demo, se abre un PR de `develop` → `main`.

Los mensajes de commit siguen la convención [Conventional Commits](https://www.conventionalcommits.org/es/).
