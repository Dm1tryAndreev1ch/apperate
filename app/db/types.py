"""Custom SQLAlchemy column types."""
from __future__ import annotations

import uuid

from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import ARRAY as PGARRAY
from sqlalchemy.dialects.postgresql import JSONB as PGJSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.types import String, TypeDecorator

from app.security.encryption import encryption_service


class EncryptedString(TypeDecorator):
    """Encrypt string values transparently at the column level."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return encryption_service.encrypt_text(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        try:
            return encryption_service.decrypt_text(value)
        except Exception:
            # Return raw value if decryption fails
            return value


def JSONBType(**kwargs):
    """Return a JSONB column type compatible with SQLite for tests."""
    pg_jsonb = PGJSONB(**kwargs)
    return pg_jsonb.with_variant(SQLiteJSON(), "sqlite")


class UUIDArray(TypeDecorator):
    """Store UUID arrays with Postgres ARRAY and SQLite JSON."""

    impl = SQLiteJSON
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(SQLiteJSON())
        return dialect.type_descriptor(PGARRAY(PGUUID(as_uuid=True)))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "sqlite":
            return [str(v) for v in value]
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == "sqlite":
            return [uuid.UUID(v) if not isinstance(v, uuid.UUID) else v for v in value]
        return value


class GUID(TypeDecorator):
    """Platform-independent GUID/UUID type."""

    impl = PGUUID
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "sqlite":
            return dialect.type_descriptor(String(36))
        return dialect.type_descriptor(PGUUID(as_uuid=True))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if not isinstance(value, uuid.UUID):
            value = uuid.UUID(str(value))
        if dialect.name == "sqlite":
            return str(value)
        return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        return uuid.UUID(str(value))



