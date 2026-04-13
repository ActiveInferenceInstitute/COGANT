"""Service layer for the Flask-style app.

Exercises: dependency injection, business-logic orchestration,
error handling with try/except chains, and service-level transactions.
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any, Dict, List, Optional

from .config import BaseConfig
from .models import InMemorySession, Post, User, ValidationError


class ServiceError(Exception):
    """Raised on recoverable business-logic errors."""


class AuthorizationError(ServiceError):
    """Raised when the current principal may not perform the action."""


class NotFoundError(ServiceError):
    """Raised when a requested resource does not exist."""


def _hash_password(raw: str, secret: str) -> str:
    """Compute a HMAC-SHA256 of the password. Hermetic and deterministic."""
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


class UserService:
    """CRUD + auth operations for ``User`` instances."""

    def __init__(self, session: InMemorySession, config: BaseConfig) -> None:
        self.session = session
        self.config = config

    def register(self, username: str, email: str, password: str) -> User:
        if not username or not email or not password:
            raise ValidationError("username, email and password are required")
        existing = [u for u in self.session.all(User) if u.username == username]
        if existing:
            raise ServiceError(f"username already taken: {username}")
        user = User(
            username=username,
            email=email,
            password_hash=_hash_password(password, self.config.get("SECRET_KEY")),
        )
        try:
            self.session.add(user)
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise
        return user

    def authenticate(self, username: str, password: str) -> Optional[User]:
        for candidate in self.session.all(User):
            if candidate.username != username:
                continue
            if not candidate.is_active:
                return None
            expected = _hash_password(password, self.config.get("SECRET_KEY"))
            if hmac.compare_digest(candidate.password_hash, expected):
                return candidate
            return None
        return None

    def promote(self, actor: User, target_id: str, new_role: str) -> User:
        if actor.role != "admin":
            raise AuthorizationError("only admins may promote users")
        target = self.session.get(User, target_id)
        if target is None:
            raise NotFoundError(f"User {target_id} not found")
        target.promote(new_role)
        self.session.commit()
        return target

    def deactivate(self, actor: User, target_id: str) -> User:
        if actor.role not in {"admin", "moderator"}:
            raise AuthorizationError("only admins or moderators may deactivate users")
        target = self.session.get(User, target_id)
        if target is None:
            raise NotFoundError(f"User {target_id} not found")
        target.deactivate()
        self.session.commit()
        return target


class PostService:
    """CRUD operations for ``Post`` instances."""

    def __init__(self, session: InMemorySession, config: BaseConfig) -> None:
        self.session = session
        self.config = config

    def create(self, author: User, title: str, body: str, tags: Optional[List[str]] = None) -> Post:
        if not author.is_active:
            raise AuthorizationError("inactive users may not create posts")
        post = Post(
            author_id=author.id,
            title=title,
            body=body,
            tags=list(tags or []),
        )
        try:
            self.session.add(post)
            self.session.commit()
        except ValidationError:
            self.session.rollback()
            raise
        return post

    def publish(self, actor: User, post_id: str) -> Post:
        post = self.session.get(Post, post_id)
        if post is None:
            raise NotFoundError(f"Post {post_id} not found")
        if post.author_id != actor.id and actor.role not in {"admin", "moderator"}:
            raise AuthorizationError("not the author")
        try:
            post.publish()
            self.session.commit()
        except ValidationError:
            self.session.rollback()
            raise
        return post

    def list_published(self) -> List[Post]:
        return [p for p in self.session.all(Post) if p.published]

    def delete(self, actor: User, post_id: str) -> None:
        post = self.session.get(Post, post_id)
        if post is None:
            raise NotFoundError(f"Post {post_id} not found")
        if post.author_id != actor.id and actor.role != "admin":
            raise AuthorizationError("not the author or admin")
        self.session.delete(post)
        self.session.commit()


class ServiceContainer:
    """Minimal DI container wiring a session + config to concrete services."""

    def __init__(self, config: BaseConfig) -> None:
        self.config = config
        self.session = InMemorySession()
        self.users = UserService(self.session, config)
        self.posts = PostService(self.session, config)

    def snapshot(self) -> Dict[str, Any]:
        return {
            "users": [u.to_dict() for u in self.session.all(User)],
            "posts": [p.to_dict() for p in self.session.all(Post)],
        }
