from collections.abc import Generator

from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

# check_same_thread is a SQLite-only concern; Postgres rejects it outright.
connect_args = {"check_same_thread": False} if settings.is_sqlite else {}

engine = create_engine(
    settings.sqlalchemy_url,
    connect_args=connect_args,
    # Neon suspends an idle compute after a few minutes and drops its
    # connections. A pooled connection handed out afterwards is already dead,
    # and the request using it fails with a bewildering "server closed the
    # connection unexpectedly". pool_pre_ping spends one cheap round-trip
    # checking before handing a connection over. Harmless on SQLite.
    pool_pre_ping=True,
    # Neon counts connections, and a small web service holding a large idle
    # pool is a good way to hit that ceiling for no benefit.
    **({"pool_size": 5, "max_overflow": 5} if not settings.is_sqlite else {}),
)


def init_db() -> None:
    """Creates any table that does not exist yet.

    This is not a migration system: it adds new tables, and it silently
    ignores a column that has changed on an existing one. That is fine while
    the schema only grows, and stops being fine the first time real patient
    data has to survive a column change -- see HOSTING.md.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    with Session(engine) as session:
        yield session
