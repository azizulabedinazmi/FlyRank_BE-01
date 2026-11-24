"""The one place that decides where tasks live. Swapping storage engines means editing this file only."""
from repository import TaskRepository
from sqlite_repository import SqliteTaskRepository


def make_repository() -> TaskRepository:
    return SqliteTaskRepository()
