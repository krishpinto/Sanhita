"""Test DB setup. Swaps app.db's module-level `engine` for an in-memory
SQLite engine on a StaticPool (one shared connection) *before* any test
module is collected -- file-backed SQLite under the test sandbox intermittently
reported 'attempt to write a readonly database' on the second connection from
a QueuePool, which StaticPool's single shared connection sidesteps entirely.

This must happen at module import time (not inside a fixture) because
test_api_flow.py triggers the FastAPI startup event at collection time, and
functions in app.db resolve the module-global `engine` name at *call* time --
so reassigning app.db.engine here, before anything calls init_db(), is
enough for every later call (including inside routers via Depends) to see
the patched engine.
"""

from sqlalchemy.pool import StaticPool
from sqlmodel import create_engine

import app.db as db_module

db_module.engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
