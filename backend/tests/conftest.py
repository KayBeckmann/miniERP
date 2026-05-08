import os

# Set required env vars before any app import
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("SECRET_KEY", "test_secret_key_for_testing_must_be_32chars!")
os.environ.setdefault("FIRST_SUPERUSER_EMAIL", "test@test.com")
os.environ.setdefault("FIRST_SUPERUSER_PASSWORD", "testpassword")
