import os

# Set before any app code is imported. The engine does not connect until used.
os.environ.setdefault(
    "DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test"
)