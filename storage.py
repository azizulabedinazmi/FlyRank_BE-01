"""The one place that decides where tasks live. Swapping storage engines means editing this file only.

A2 version:
    from sqlite_repository import SqliteTaskRepository
    return SqliteTaskRepository()
"""
import os

from dotenv import load_dotenv

from postgres_repository import PostgresTaskRepository
from repository import TaskRepository

# Reads .env when you run uvicorn on your machine. Real environment variables (e.g. from docker compose) win.
load_dotenv()


def make_repository() -> TaskRepository:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")
    return PostgresTaskRepository(url)
