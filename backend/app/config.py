from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    # IP del host (ej. salida de nslookup ... 8.8.8.8). Evita fallos de DNS en Windows con sufijo .com.ar.
    DATABASE_HOSTADDR: str = ""

    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 480

    # Llave Fernet (Fernet.generate_key()) que cifra en reposo las claves privadas
    # custodiadas. Es independiente de JWT_SECRET: comprometer una no expone la otra.
    # Vacía, se usa la llave derivada de JWT_SECRET de las versiones anteriores.
    WALLET_ENCRYPTION_KEY: str = ""

    # Si está vacío, /admin usa los primeros 32 caracteres de JWT_SECRET (legacy).
    ADMIN_API_TOKEN: str = ""

    RPC_URL: str
    # Proveedores RPC de respaldo, separados por coma. Se usan si el principal no responde.
    RPC_URL_FALLBACK: str = ""
    CHAIN_ID: int
    CONTRACT_ADDRESS: str
    ADMIN_PRIVATE_KEY: str
    CONTRACT_ABI_PATH: str = "app/abi/HistorialCeroKM.json"

    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET: str = "historial-evidencias"
    R2_PUBLIC_URL: str = ""

    FRONTEND_ORIGIN: str = "http://localhost:5173"


settings = Settings()
