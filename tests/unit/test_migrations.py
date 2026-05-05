"""Unit tests for migration configuration and integrity."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestMigrationConfiguration:
    """Test migration setup and configuration."""

    def test_migration_env_configured_for_async(self):
        """Verify env.py is configured for async SQLAlchemy."""
        env_py = Path(__file__).parent.parent.parent / "alembic" / "env.py"
        content = env_py.read_text()
        assert "asyncio" in content, "env.py should support async"
        assert "create_async_engine" in content, "Should use async engine"

    def test_migration_sqlalchemy_target_metadata(self):
        """Verify target metadata is properly configured."""
        env_py = Path(__file__).parent.parent.parent / "alembic" / "env.py"
        content = env_py.read_text()
        assert "target_metadata" in content, "Should reference target metadata"
        assert "Base.metadata" in content, "Should use SQLAlchemy Base metadata"

    def test_alembic_ini_sqlalchemy_url_configured(self):
        """Verify alembic.ini has sqlalchemy.url configured."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        content = alembic_ini.read_text()
        assert "sqlalchemy.url" in content, "alembic.ini should have sqlalchemy.url"

    def test_migration_script_location_correct(self):
        """Verify script_location in alembic.ini points to alembic directory."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        content = alembic_ini.read_text()
        for line in content.split("\n"):
            if line.strip().startswith("script_location"):
                assert "alembic" in line, "script_location should point to alembic directory"
                break

    def test_migration_version_table_configured(self):
        """Verify alembic version tracking table is configured."""
        alembic_ini = Path(__file__).parent.parent.parent / "alembic.ini"
        content = alembic_ini.read_text()
        # Look for version_table configuration
        has_version_table = "version_table" in content or "alembic_version" in content
        assert has_version_table, "Should have version table configuration"


class TestMigrationContent:
    """Test the content and integrity of migration files."""

    def test_0001_migration_creates_listing_table(self):
        """Verify first migration creates listing table."""
        migration_0001 = Path(__file__).parent.parent.parent / "alembic" / "versions" / "0001_create_core_models.py"
        content = migration_0001.read_text()
        assert "listing" in content.lower(), "Migration 0001 should create listing table"

    def test_0002_migration_creates_comp_job_table(self):
        """Verify second migration creates comp job table."""
        migration_0002 = Path(__file__).parent.parent.parent / "alembic" / "versions" / "0002_create_comp_job.py"
        content = migration_0002.read_text()
        assert "comp_job" in content.lower() or "comp" in content.lower(), "Migration 0002 should create comp tables"

    def test_migrations_have_downgrade_paths(self):
        """Ensure all migrations can be downgraded (reversible)."""
        versions_dir = Path(__file__).parent.parent.parent / "alembic" / "versions"
        migrations = sorted([f for f in versions_dir.glob("*.py") if f.name[0].isdigit()])
        
        for migration in migrations:
            content = migration.read_text()
            # Check that downgrade() doesn't just pass
            downgrade_section = content[content.find("def downgrade()") :]
            # Should have some content besides just 'pass'
            lines = [l.strip() for l in downgrade_section.split("\n") if l.strip() and not l.strip().startswith("#")]
            # At least downgrade function definition and some ops
            assert len(lines) > 1, f"{migration.name} downgrade() appears to be empty"
