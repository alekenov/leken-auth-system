from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
from datetime import timedelta
import uvicorn

from auth import (
    User, UserCreate, UserLogin, UserResponse, Token,
    get_password_hash, authenticate_user, create_access_token,
    get_current_user, get_user_by_username, get_user_by_email,
    users_db, ACCESS_TOKEN_EXPIRE_MINUTES
)

app = FastAPI(
    title="Leken API",
    description="Simple FastAPI backend server",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Item(BaseModel):
    id: Optional[int] = None
    name: str
    description: Optional[str] = None
    price: float

items_db = []

@app.get("/")
async def root():
    return {"message": "Welcome to Leken API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Leken API"}

@app.post("/register", response_model=UserResponse)
async def register(user: UserCreate):
    if get_user_by_username(user.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    if get_user_by_email(user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    hashed_password = get_password_hash(user.password)
    user_dict = {
        "id": len(users_db) + 1,
        "username": user.username,
        "email": user.email,
        "hashed_password": hashed_password
    }
    users_db.append(user_dict)

    return UserResponse(
        id=user_dict["id"],
        username=user_dict["username"],
        email=user_dict["email"]
    )

@app.post("/login", response_model=Token)
async def login(user: UserLogin):
    authenticated_user = authenticate_user(user.username, user.password)
    if not authenticated_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": authenticated_user["username"]},
        expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/me", response_model=UserResponse)
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return UserResponse(
        id=current_user["id"],
        username=current_user["username"],
        email=current_user["email"]
    )

@app.get("/users", response_model=List[UserResponse])
async def get_users(current_user: dict = Depends(get_current_user)):
    return [
        UserResponse(id=user["id"], username=user["username"], email=user["email"])
        for user in users_db
    ]

@app.get("/items", response_model=List[Item])
async def get_items(current_user: dict = Depends(get_current_user)):
    return items_db

@app.get("/items/{item_id}", response_model=Item)
async def get_item(item_id: int):
    for item in items_db:
        if item.get("id") == item_id:
            return item
    raise HTTPException(status_code=404, detail="Item not found")

@app.post("/items", response_model=Item)
async def create_item(item: Item):
    item_dict = item.dict()
    item_dict["id"] = len(items_db) + 1
    items_db.append(item_dict)
    return item_dict

@app.put("/items/{item_id}", response_model=Item)
async def update_item(item_id: int, item: Item):
    for i, existing_item in enumerate(items_db):
        if existing_item.get("id") == item_id:
            item_dict = item.dict()
            item_dict["id"] = item_id
            items_db[i] = item_dict
            return item_dict
    raise HTTPException(status_code=404, detail="Item not found")

@app.delete("/items/{item_id}")
async def delete_item(item_id: int):
    for i, item in enumerate(items_db):
        if item.get("id") == item_id:
            del items_db[i]
            return {"message": "Item deleted successfully"}
    raise HTTPException(status_code=404, detail="Item not found")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8011)