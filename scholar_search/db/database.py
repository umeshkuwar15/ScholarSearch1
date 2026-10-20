
import os
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.exc import SQLAlchemyError


PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "scholarsearch_db")

DATABASE_URL = URL.create(
    "mysql+pymysql",
    username=MYSQL_USER,
    password=MYSQL_PASSWORD,
    host=MYSQL_HOST,
    port=MYSQL_PORT,
    database=MYSQL_DATABASE,
    query={"charset": "utf8mb4"},
)
engine = create_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def init_db():
    """Verify the MySQL server and configured schema, then create model tables."""
    server_url = DATABASE_URL.set(database=None)
    server_engine = create_engine(server_url, echo=False, pool_pre_ping=True)
    try:
        with server_engine.connect() as connection:
            database_exists = connection.execute(
                text("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA WHERE SCHEMA_NAME = :name"),
                {"name": MYSQL_DATABASE},
            ).scalar_one_or_none()
    except (SQLAlchemyError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            f"Could not connect to MySQL at {MYSQL_HOST}:{MYSQL_PORT}. "
            "Check that MySQL Server is running and MYSQL_HOST, MYSQL_PORT, "
            "MYSQL_USER, and MYSQL_PASSWORD in .env are correct."
        ) from exc
    finally:
        server_engine.dispose()

    if database_exists is None:
        raise RuntimeError(
            f"MySQL database '{MYSQL_DATABASE}' does not exist. Open MySQL Workbench, "
            f"connect to {MYSQL_HOST}:{MYSQL_PORT}, and run: "
            f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE};"
        )

    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        Base.metadata.create_all(bind=engine)
    except (SQLAlchemyError, ModuleNotFoundError) as exc:
        raise RuntimeError(
            f"Could not initialize tables in MySQL database '{MYSQL_DATABASE}'. "
            "Check the MySQL credentials and database permissions."
        ) from exc


def get_session():
    return SessionLocal()


def close_session(session):
    if session:
        session.close()
