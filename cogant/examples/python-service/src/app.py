"""Main FastAPI application for the example service."""

from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config import get_settings
from events import (
    ItemCreatedEvent,
    UserCreatedEvent,
    UserUpdatedEvent,
    event_emitter,
)
from models import Base, Item, ItemDB, ItemCreatedEvent, User, UserDB
from models import ErrorResponse, PaginationParams

app = FastAPI(
    title="Example Python Service",
    description="A sample microservice for COGANT analysis",
    version="0.1.0",
)

settings = get_settings()

# Database setup
engine = create_engine(
    settings.database_url,
    echo=settings.echo_sql,
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)
Base.metadata.create_all(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    print(f"Starting {settings.app_name} v{settings.app_version}")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    print(f"Shutting down {settings.app_name}")


@app.get("/", tags=["health"])
async def root():
    """Root endpoint - service health check."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
    }


@app.get("/health", tags=["health"])
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": settings.app_name}


@app.post(f"{settings.api_prefix}/users", response_model=User, tags=["users"])
async def create_user(user: User, db: Session = Depends(get_db)):
    """Create a new user."""
    # Check if user already exists
    existing = db.query(UserDB).filter(UserDB.username == user.username).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )

    # Create new user
    db_user = UserDB(
        username=user.username,
        email=user.email,
        full_name=user.full_name,
        is_active=user.is_active,
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Emit event
    await event_emitter.emit(
        UserCreatedEvent(data={"user_id": db_user.id, "username": db_user.username})
    )

    return db_user


@app.get(f"{settings.api_prefix}/users", response_model=list[User], tags=["users"])
async def list_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """List all users with pagination."""
    users = db.query(UserDB).offset(skip).limit(limit).all()
    return users


@app.get(f"{settings.api_prefix}/users/{{user_id}}", response_model=User, tags=["users"])
async def get_user(user_id: int, db: Session = Depends(get_db)):
    """Get a user by ID."""
    user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@app.put(f"{settings.api_prefix}/users/{{user_id}}", response_model=User, tags=["users"])
async def update_user(user_id: int, user: User, db: Session = Depends(get_db)):
    """Update a user."""
    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update fields
    db_user.username = user.username
    db_user.email = user.email
    db_user.full_name = user.full_name
    db_user.is_active = user.is_active

    db.commit()
    db.refresh(db_user)

    # Emit event
    await event_emitter.emit(
        UserUpdatedEvent(data={"user_id": db_user.id, "username": db_user.username})
    )

    return db_user


@app.delete(f"{settings.api_prefix}/users/{{user_id}}", status_code=204, tags=["users"])
async def delete_user(user_id: int, db: Session = Depends(get_db)):
    """Delete a user."""
    db_user = db.query(UserDB).filter(UserDB.id == user_id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(db_user)
    db.commit()


@app.post(f"{settings.api_prefix}/items", response_model=Item, tags=["items"])
async def create_item(item: Item, db: Session = Depends(get_db)):
    """Create a new item."""
    # Verify user exists
    user = db.query(UserDB).filter(UserDB.id == item.owner_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Create item
    db_item = ItemDB(
        name=item.name, description=item.description, owner_id=item.owner_id
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Emit event
    await event_emitter.emit(
        ItemCreatedEvent(
            data={"item_id": db_item.id, "owner_id": db_item.owner_id, "name": db_item.name}
        )
    )

    return db_item


@app.get(f"{settings.api_prefix}/items", response_model=list[Item], tags=["items"])
async def list_items(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    owner_id: Optional[int] = None,
    db: Session = Depends(get_db),
):
    """List items with optional filtering by owner."""
    query = db.query(ItemDB)
    if owner_id:
        query = query.filter(ItemDB.owner_id == owner_id)
    items = query.offset(skip).limit(limit).all()
    return items


@app.get(f"{settings.api_prefix}/items/{{item_id}}", response_model=Item, tags=["items"])
async def get_item(item_id: int, db: Session = Depends(get_db)):
    """Get an item by ID."""
    item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


@app.put(f"{settings.api_prefix}/items/{{item_id}}", response_model=Item, tags=["items"])
async def update_item(item_id: int, item: Item, db: Session = Depends(get_db)):
    """Update an item."""
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.name = item.name
    db_item.description = item.description
    db.commit()
    db.refresh(db_item)
    return db_item


@app.delete(f"{settings.api_prefix}/items/{{item_id}}", status_code=204, tags=["items"])
async def delete_item(item_id: int, db: Session = Depends(get_db)):
    """Delete an item."""
    db_item = db.query(ItemDB).filter(ItemDB.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(db_item)
    db.commit()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host=settings.host,
        port=settings.port,
        log_level="info" if not settings.debug else "debug",
    )
