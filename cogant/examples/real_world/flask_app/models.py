"""SQLAlchemy-flavoured ORM models.

Exercises: class hierarchy, field descriptors, declarative schema,
validation via dunder methods, explicit state machines, and relationships.

No real database is touched — the "session" is an in-memory dict so the
fixture stays hermetic while still exercising the architectural shape of
a typical Flask + SQLAlchemy application.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional


class ValidationError(Exception):
    """Raised when a model field fails validation."""


class Field:
    """Descriptor that performs type coercion and validation."""

    def __init__(
        self,
        *,
        type_: type,
        default: Any = None,
        nullable: bool = True,
        unique: bool = False,
    ) -> None:
        self.type_ = type_
        self.default = default
        self.nullable = nullable
        self.unique = unique
        self.public_name: str = ""

    def __set_name__(self, owner: type, name: str) -> None:
        self.public_name = name

    def __get__(self, instance: Any, owner: type) -> Any:
        if instance is None:
            return self
        return instance.__dict__.get(self.public_name, self.default)

    def __set__(self, instance: Any, value: Any) -> None:
        if value is None:
            if not self.nullable:
                raise ValidationError(f"{self.public_name} may not be null")
        elif not isinstance(value, self.type_):
            try:
                value = self.type_(value)
            except (TypeError, ValueError) as exc:
                raise ValidationError(
                    f"{self.public_name} expected {self.type_.__name__}, got {type(value).__name__}"
                ) from exc
        instance.__dict__[self.public_name] = value


@dataclass
class ModelMetadata:
    """Per-model metadata attached to every persistent class."""

    tablename: str
    primary_key: str = "id"
    created_at: datetime = field(default_factory=datetime.utcnow)


class Model:
    """Base class for all persistent models."""

    __metadata__: ModelMetadata

    id = Field(type_=str, nullable=False, unique=True)

    def __init__(self, **kwargs: Any) -> None:
        if "id" not in kwargs:
            kwargs["id"] = str(uuid.uuid4())
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(self) -> Dict[str, Any]:
        out: Dict[str, Any] = {}
        for klass in type(self).__mro__:
            for key, value in vars(klass).items():
                if isinstance(value, Field):
                    out[key] = getattr(self, key)
        return out

    @classmethod
    def validate(cls, data: Dict[str, Any]) -> None:
        metadata = cls.__metadata__
        if metadata.primary_key not in data:
            raise ValidationError(
                f"{cls.__name__} requires primary key {metadata.primary_key!r}"
            )


class User(Model):
    """A registered user account."""

    __metadata__ = ModelMetadata(tablename="users")

    username = Field(type_=str, nullable=False, unique=True)
    email = Field(type_=str, nullable=False, unique=True)
    password_hash = Field(type_=str, nullable=False)
    is_active = Field(type_=bool, default=True, nullable=False)
    role = Field(type_=str, default="user", nullable=False)

    def deactivate(self) -> None:
        self.is_active = False

    def promote(self, role: str) -> None:
        if role not in {"user", "admin", "moderator"}:
            raise ValidationError(f"Unknown role: {role}")
        self.role = role


class Post(Model):
    """A blog post authored by a user."""

    __metadata__ = ModelMetadata(tablename="posts")

    author_id = Field(type_=str, nullable=False)
    title = Field(type_=str, nullable=False)
    body = Field(type_=str, nullable=False)
    published = Field(type_=bool, default=False, nullable=False)
    tags = Field(type_=list, default=None, nullable=True)

    def publish(self) -> None:
        if not self.title or not self.body:
            raise ValidationError("Post requires title and body before publishing")
        self.published = True

    def unpublish(self) -> None:
        self.published = False


class InMemorySession:
    """A toy stand-in for ``sqlalchemy.orm.Session``."""

    def __init__(self) -> None:
        self._store: Dict[str, Dict[str, Model]] = {}
        self._dirty: List[Model] = []

    def add(self, instance: Model) -> None:
        table = instance.__metadata__.tablename
        self._store.setdefault(table, {})[instance.id] = instance
        self._dirty.append(instance)

    def get(self, model_cls: type, id_: str) -> Optional[Model]:
        table = model_cls.__metadata__.tablename
        return self._store.get(table, {}).get(id_)

    def all(self, model_cls: type) -> Iterable[Model]:
        table = model_cls.__metadata__.tablename
        return list(self._store.get(table, {}).values())

    def delete(self, instance: Model) -> None:
        table = instance.__metadata__.tablename
        self._store.get(table, {}).pop(instance.id, None)

    def commit(self) -> int:
        flushed = len(self._dirty)
        self._dirty.clear()
        return flushed

    def rollback(self) -> None:
        self._dirty.clear()
