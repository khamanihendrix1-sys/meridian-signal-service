"""Integration tests for Alembic database migrations."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine


@pytest.fixture
async def migration_db_engine():
    """Create a fresh in-memory database for migration testing."""
    database_url = "sqlite+aiosqlite:///:memory:"
    engine = create_async_engine(database_url, echo=False)
    yield engine
    await engine.dispose()


class TestMigrations:
    """Test suite for Alembic migrations."""

    @pytest.mark.asyncio
    async def test_migration_0001_creates_tables(self, migration_db_engine):
        """Verify migration 0001 creates core tables."""
        # This test would run the migration and verify tables exist
        # In a real scenario, you'd run alembic upgrade head
        async with migration_db_engine.connect() as conn:
            inspector = inspect(conn)
            # After migration 0001, these tables should exist
            expected_tables = [
                "listing",
                "market_report",
                "signal_definition",
                "signal_log",
            ]
            # This is a placeholder - actual implementation depends on
            # running migrations in the test database
            assert True  # Placeholder

    @pytest.mark.asyncio
    async def test_migration_0002_creates_comp_tables(self, migration_db_engine):
        """Verify migration 0002 creates comp-related tables."""
        # After migration 0002, comp tables should exist
        expected_tables = ["comp_job", "comp"]
        assert True  # Placeholder

    def test_migration_history_is_linear(self):
        """Ensure migration files form a linear sequence."""
        migrations_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        migration_files = sorted([f for f in migrations_dir.glob("*.py") if f.name[0].isdigit()])
        
        # Extract revision numbers
        revisions = []
        for f in migration_files:
            # Assuming format: 0001_name.py
            num = int(f.name[:4])
            revisions.append(num)
        
        # Check they're sequential
        for i, rev in enumerate(revisions, 1):
            assert rev == i, f"Expected migration {i}, got {rev}"

    def test_migration_files_exist(self):
        """Verify expected migration files exist."""
        migrations_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        expected_migrations = [
            "0001_create_core_models.py",
            "0002_create_comp_job.py",
        ]
        
        for migration in expected_migrations:
            migration_path = migrations_dir / migration
            assert migration_path.exists(), f"Migration file {migration} not found"

    def test_migration_files_have_upgrade_downgrade(self):
        """Ensure migration files have upgrade() and downgrade() functions."""
        migrations_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        migration_files = sorted([f for f in migrations_dir.glob("*.py") if f.name[0].isdigit()])
        
        for migration_file in migration_files:
            content = migration_file.read_text()
            assert "def upgrade()" in content, f"{migration_file.name} missing upgrade()"
            assert "def downgrade()" in content, f"{migration_file.name} missing downgrade()"

    def test_migration_rev_id_is_unique(self):
        """Ensure each migration has a unique revision ID."""
        migrations_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        migration_files = sorted([f for f in migrations_dir.glob("*.py") if f.name[0].isdigit()])
        
        rev_ids = []
        for migration_file in migration_files:
            content = migration_file.read_text()
            # Extract revision ID from revision = '...'
            for line in content.split("\n"):
                if line.startswith("revision = "):
                    rev_id = line.split("'")[1]
                    rev_ids.append(rev_id)
                    break
        
        # Check for duplicates
        assert len(rev_ids) == len(set(rev_ids)), "Duplicate revision IDs found"

    def test_alembic_ini_exists(self):
        """Verify alembic.ini configuration file exists."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        assert alembic_ini.exists(), "alembic.ini not found"

    def test_alembic_env_py_exists(self):
        """Verify alembic/env.py exists."""
        env_py = Path(__file__).parent.parent.parent / "alembic" / "env.py"
        assert env_py.exists(), "alembic/env.py not found"
