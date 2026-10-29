from dataclasses import dataclass
from pathlib import Path
import os
from dotenv import load_dotenv
from sqlalchemy import URL

ROOT = Path(__file__).resolve().parents[2]
default_env = ROOT / ".env.services"
if not default_env.is_file(): default_env = ROOT / ".env"
load_dotenv(Path(os.getenv("SERVER_ENV_FILE", str(default_env))), override=False)

@dataclass(frozen=True)
class Settings:
    service: str
    database: str
    username: str
    password: str
    host: str = os.getenv("MYSQL_HOST", "127.0.0.1")
    port: int = int(os.getenv("MYSQL_PORT", "3306"))
    user_root: Path = Path(os.getenv("USER_DATA_ROOT", str(ROOT / "user_data"))).resolve()
    origins: tuple[str, ...] = tuple(x.strip() for x in os.getenv("ALLOWED_ORIGINS", "http://127.0.0.1:5173,http://localhost:5173,http://127.0.0.1:5174,http://localhost:5174").split(",") if x.strip())
    cookie_secure: bool = os.getenv("COOKIE_SECURE", "false").lower() == "true"
    session_seconds: int = 7 * 24 * 60 * 60

    @property
    def database_url(self):
        if not self.password: raise RuntimeError(f"{self.service.upper()}_MYSQL_PASSWORD is required")
        return URL.create("mysql+pymysql", username=self.username, password=self.password,
                          host=self.host, port=self.port, database=self.database, query={"charset":"utf8mb4"})

def for_service(name):
    prefix=name.upper()
    return Settings(name, os.getenv(f"{prefix}_MYSQL_DATABASE", f"study_{name}"),
                    os.getenv(f"{prefix}_MYSQL_USER", f"study_{name}"), os.getenv(f"{prefix}_MYSQL_PASSWORD", ""))

IDENTITY_URL=os.getenv("IDENTITY_URL", "http://127.0.0.1:8001")
LEARNING_URL=os.getenv("LEARNING_URL", "http://127.0.0.1:8002")
AI_URL=os.getenv("AI_URL", "http://127.0.0.1:8003")
SERVICE_KEY=os.getenv("INTERNAL_SERVICE_KEY", "")
