from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, validator
from typing import List, Optional
import re
from datetime import timedelta, datetime
from sqlalchemy.orm import Session
import uvicorn

from database import create_tables, get_db, Item as ItemModel
from auth_db import (
    UserCreate, UserLogin, UserResponse, Token,
    authenticate_user, create_access_token, get_current_user,
    get_user_by_username, get_user_by_email, create_user,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from crm_api import router as crm_router
from product_api import router as product_router
from inventory_management import router as inventory_router

app = FastAPI(
    title="Leken API",
    description="FastAPI backend with SQLite database",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8888", "http://localhost:8011", "http://127.0.0.1:8888", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)

# Include Inventory Management router first (more specific routes)
app.include_router(inventory_router, prefix="/api", tags=["Inventory"])

# Include Enhanced Product API router
app.include_router(product_router, prefix="/api", tags=["Products"])

# Include CRM API router last (more general routes)
app.include_router(crm_router, prefix="/api", tags=["CRM"])

class ItemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    price: float

class ItemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str] = None
    price: float
    created_at: datetime

    class Config:
        from_attributes = True

class ProfileUpdate(BaseModel):
    city: Optional[str] = None
    position: Optional[str] = None
    address: Optional[str] = None
    phone: Optional[str] = None

    @validator('city')
    def validate_city(cls, v):
        if v and v not in ["Алматы", "Астана"]:
            raise ValueError('Город должен быть "Алматы" или "Астана"')
        return v

    @validator('position')
    def validate_position(cls, v):
        if v and v not in ["Менеджер", "Флорист"]:
            raise ValueError('Должность должна быть "Менеджер" или "Флорист"')
        return v

    @validator('phone')
    def validate_phone(cls, v):
        if v and not re.match(r'^\+7\d{10}$', v):
            raise ValueError('Телефон должен быть в формате +7XXXXXXXXXX (11 цифр)')
        return v

@app.on_event("startup")
async def startup():
    create_tables()

@app.get("/")
async def root():
    return {"message": "Welcome to Leken API with SQLite"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Leken API", "database": "SQLite"}

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    if get_user_by_username(db, user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if get_user_by_email(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    db_user = create_user(db, user)
    return db_user

@app.post("/login", response_model=Token)
async def login(user: UserLogin, db: Session = Depends(get_db)):
    authenticated_user = authenticate_user(db, user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": authenticated_user.username},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
async def read_users_me(current_user = Depends(get_current_user)):
    return current_user

@app.get("/users", response_model=List[UserResponse])
async def get_users(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    from database import User as UserModel
    users = db.query(UserModel).all()
    return users

# Public endpoint for demo purposes
@app.get("/api/users", response_model=List[UserResponse])
async def get_users_public(db: Session = Depends(get_db)):
    from database import User as UserModel
    users = db.query(UserModel).all()
    return users

@app.get("/items", response_model=List[ItemResponse])
async def get_items(current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    items = db.query(ItemModel).all()
    return items

@app.get("/items/{item_id}", response_model=ItemResponse)
async def get_item(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item

@app.post("/items", response_model=ItemResponse)
async def create_item(item: ItemCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    db_item = ItemModel(
        name=item.name,
        description=item.description,
        price=item.price
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item

@app.put("/items/{item_id}", response_model=ItemResponse)
async def update_item(item_id: int, item: ItemCreate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db_item.name = item.name
    db_item.description = item.description
    db_item.price = item.price
    db.commit()
    db.refresh(db_item)
    return db_item

@app.delete("/items/{item_id}")
async def delete_item(item_id: int, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    db_item = db.query(ItemModel).filter(ItemModel.id == item_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Item not found")

    db.delete(db_item)
    db.commit()
    return {"message": "Item deleted successfully"}

@app.put("/profile", response_model=UserResponse)
async def update_profile(profile: ProfileUpdate, current_user = Depends(get_current_user), db: Session = Depends(get_db)):
    from database import User as UserModel

    # Получаем пользователя из базы данных
    db_user = db.query(UserModel).filter(UserModel.id == current_user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Обновляем только переданные поля
    if profile.city is not None:
        db_user.city = profile.city
    if profile.position is not None:
        db_user.position = profile.position
    if profile.address is not None:
        db_user.address = profile.address
    if profile.phone is not None:
        db_user.phone = profile.phone

    db.commit()
    db.refresh(db_user)
    return db_user

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8011)