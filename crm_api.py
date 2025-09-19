from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel, validator, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy.orm import Session
import re

from database import (
    get_db, Client, Product, Inventory, Order, OrderItem,
    ProductInventory, User
)
from auth_db import get_current_user

# Create FastAPI router
router = APIRouter()

# Pydantic models for API
class ClientCreate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)  # Имя опционально
    phone: str = Field(..., pattern=r'^\+7\d{10}$')
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    address: Optional[str] = Field(None, max_length=500)
    client_type: str = Field(..., pattern=r'^(заказчик|получатель|оба)$')
    notes: Optional[str] = Field(None, max_length=1000)

class ClientUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100)
    phone: Optional[str] = Field(None, pattern=r'^\+7\d{10}$')
    email: Optional[str] = Field(None, pattern=r'^[^@]+@[^@]+\.[^@]+$')
    address: Optional[str] = Field(None, max_length=500)
    client_type: Optional[str] = Field(None, pattern=r'^(заказчик|получатель|оба)$')
    notes: Optional[str] = Field(None, max_length=1000)

class ClientResponse(BaseModel):
    id: int
    name: Optional[str]  # Имя опционально
    phone: str
    email: Optional[str]
    address: Optional[str]
    client_type: str
    notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Расширенные модели для статистики клиентов
class ClientWithStatistics(BaseModel):
    """Клиент с базовой статистикой для списка"""
    id: int
    name: Optional[str]
    phone: str
    email: Optional[str]
    client_type: str
    notes: Optional[str]
    created_at: datetime

    # Статистика
    total_orders: int
    first_order_date: Optional[datetime]
    last_order_date: Optional[datetime]
    total_spent: float
    average_order_value: float

class ClientStatistics(BaseModel):
    """Детальная статистика клиента"""
    client_id: int
    client_name: Optional[str]
    client_phone: str

    # Основные метрики
    total_orders: int
    total_spent: float
    average_order_value: float

    # Временные метрики
    first_order_date: Optional[datetime]
    last_order_date: Optional[datetime]
    days_since_first_order: Optional[int]
    days_since_last_order: Optional[int]

    # Детальная статистика по статусам заказов
    orders_by_status: Dict[str, int]

    # Статистика по категориям продуктов
    favorite_categories: List[Dict[str, Any]]

    # Сводка по месяцам
    monthly_spending: List[Dict[str, Any]]

class OrderSummary(BaseModel):
    """Краткая информация о заказе для истории клиента"""
    id: int
    status: str
    delivery_date: datetime
    total_price: Optional[float]
    created_at: datetime
    items_count: int
    items_summary: str  # "3 букета, 1 композиция"

class ClientOrderHistory(BaseModel):
    """История заказов клиента с пагинацией"""
    client_id: int
    client_name: Optional[str]
    total_orders: int
    orders: List[OrderSummary]
    page: int
    page_size: int
    has_more: bool

class ProductCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: float = Field(..., gt=0)
    category: str = Field(..., pattern=r'^(букет|композиция|горшечный)$')
    preparation_time: Optional[int] = Field(None, ge=0)  # minutes
    image_url: Optional[str] = None

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = Field(None, max_length=1000)
    price: Optional[float] = Field(None, gt=0)
    category: Optional[str] = Field(None, pattern=r'^(букет|композиция|горшечный)$')
    preparation_time: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = None

class ProductResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    price: float
    category: str
    preparation_time: Optional[int]
    image_url: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

class InventoryCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=200)
    quantity: float = Field(..., ge=0)
    unit: str = Field(..., pattern=r'^(шт|м|кг)$')
    min_quantity: Optional[float] = Field(None, ge=0)
    price_per_unit: Optional[float] = Field(None, gt=0)

class InventoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=200)
    quantity: Optional[float] = Field(None, ge=0)
    unit: Optional[str] = Field(None, pattern=r'^(шт|м|кг)$')
    min_quantity: Optional[float] = Field(None, ge=0)
    price_per_unit: Optional[float] = Field(None, gt=0)

class InventoryResponse(BaseModel):
    id: int
    name: str
    quantity: float
    unit: str
    min_quantity: Optional[float]
    price_per_unit: Optional[float]
    created_at: datetime

    class Config:
        from_attributes = True

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: int = Field(..., gt=0)
    price: Optional[float] = Field(None, gt=0)  # If None, use product price

class OrderItemResponse(BaseModel):
    id: int
    product_id: int
    quantity: int
    price: float
    product: ProductResponse

    class Config:
        from_attributes = True

class OrderCreate(BaseModel):
    client_id: int
    recipient_id: int
    executor_id: Optional[int] = None
    delivery_date: datetime
    delivery_address: str = Field(..., min_length=5, max_length=500)
    comment: Optional[str] = Field(None, max_length=1000)
    items: List[OrderItemCreate]

class OrderUpdate(BaseModel):
    recipient_id: Optional[int] = None
    executor_id: Optional[int] = None
    status: Optional[str] = Field(None, pattern=r'^(новый|в работе|готов|доставлен)$')
    delivery_date: Optional[datetime] = None
    delivery_address: Optional[str] = Field(None, min_length=5, max_length=500)
    comment: Optional[str] = Field(None, max_length=1000)

class OrderStatusUpdate(BaseModel):
    status: str = Field(..., pattern=r'^(новый|в работе|готов|доставлен)$')

class OrderResponse(BaseModel):
    id: int
    client_id: int
    recipient_id: int
    executor_id: Optional[int]
    status: str
    delivery_date: datetime
    delivery_address: str
    total_price: Optional[float]
    comment: Optional[str]
    created_at: datetime
    client: ClientResponse
    recipient: ClientResponse
    executor: Optional[dict]  # User data if executor is assigned
    order_items: List[OrderItemResponse]

    class Config:
        from_attributes = True

# Helper functions
def generate_order_number() -> str:
    """Generate unique order number"""
    from datetime import datetime
    import random
    timestamp = datetime.now().strftime("%Y%m%d")
    random_num = random.randint(1000, 9999)
    return f"ORD-{timestamp}-{random_num}"

def calculate_order_total(order_items: List[OrderItemCreate], db: Session) -> float:
    """Calculate total price for order items"""
    total = 0.0
    for item in order_items:
        if item.price:
            total += item.price * item.quantity
        else:
            product = db.query(Product).filter(Product.id == item.product_id).first()
            if product:
                total += product.price * item.quantity
    return total

# Clients API Endpoints
@router.get("/clients", response_model=List[ClientResponse])
async def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    client_type: Optional[str] = Query(None, pattern=r'^(заказчик|получатель|оба)$'),
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all clients with pagination and optional search"""
    query = db.query(Client)

    if client_type:
        query = query.filter(Client.client_type == client_type)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Client.name.like(search_filter)) |
            (Client.phone.like(search_filter)) |
            (Client.email.like(search_filter))
        )

    clients = query.offset(skip).limit(limit).all()
    return clients

@router.get("/clients/{client_id}", response_model=ClientResponse)
async def get_client(
    client_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get client details by ID"""
    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client

@router.post("/clients", response_model=ClientResponse)
async def create_client(
    client: ClientCreate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new client"""
    # Check if phone number already exists
    existing_client = db.query(Client).filter(Client.phone == client.phone).first()
    if existing_client:
        raise HTTPException(
            status_code=400,
            detail="Client with this phone number already exists"
        )

    db_client = Client(**client.dict())
    db.add(db_client)
    db.commit()
    db.refresh(db_client)
    return db_client

@router.put("/clients/{client_id}", response_model=ClientResponse)
async def update_client(
    client_id: int,
    client: ClientUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update client"""
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if phone number already exists (if being updated)
    if client.phone and client.phone != db_client.phone:
        existing_client = db.query(Client).filter(Client.phone == client.phone).first()
        if existing_client:
            raise HTTPException(
                status_code=400,
                detail="Client with this phone number already exists"
            )

    update_data = client.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_client, field, value)

    db.commit()
    db.refresh(db_client)
    return db_client

@router.patch("/clients/{client_id}", response_model=ClientResponse)
async def partial_update_client(
    client_id: int,
    client: ClientUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Partial update client (PATCH method)"""
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if phone number already exists (if being updated)
    if client.phone and client.phone != db_client.phone:
        existing_client = db.query(Client).filter(Client.phone == client.phone).first()
        if existing_client:
            raise HTTPException(
                status_code=400,
                detail="Client with this phone number already exists"
            )

    update_data = client.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    updated_fields = []
    for field, value in update_data.items():
        setattr(db_client, field, value)
        updated_fields.append(field)

    db.commit()
    db.refresh(db_client)

    return db_client

@router.delete("/clients/{client_id}")
async def delete_client(
    client_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete client"""
    db_client = db.query(Client).filter(Client.id == client_id).first()
    if not db_client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Check if client has orders
    orders_count = db.query(Order).filter(
        (Order.client_id == client_id) | (Order.recipient_id == client_id)
    ).count()
    if orders_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete client with existing orders"
        )

    db.delete(db_client)
    db.commit()
    return {"message": "Client deleted successfully"}

# Расширенные endpoints для клиентов с статистикой
@router.get("/clients-extended", response_model=List[ClientWithStatistics])
async def get_clients_with_statistics(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=1000),
    search: Optional[str] = Query(None),
    client_type: Optional[str] = Query(None, pattern=r'^(заказчик|получатель|оба)$'),
    sort_by: str = Query("name", pattern=r'^(name|phone|total_orders|total_spent|last_order_date)$'),
    sort_order: str = Query("asc", pattern=r'^(asc|desc)$'),
    db: Session = Depends(get_db)
):
    """Получить список клиентов с базовой статистикой"""
    from sqlalchemy import func, case

    # Базовый запрос с подзапросом для статистики
    orders_subquery = db.query(
        Order.client_id,
        Order.recipient_id,
        func.count(Order.id).label('order_count'),
        func.sum(Order.total_price).label('total_spent'),
        func.avg(Order.total_price).label('avg_order_value'),
        func.min(Order.created_at).label('first_order'),
        func.max(Order.created_at).label('last_order')
    ).group_by(Order.client_id, Order.recipient_id).subquery()

    # Основной запрос клиентов
    query = db.query(Client).outerjoin(
        orders_subquery,
        (orders_subquery.c.client_id == Client.id) |
        (orders_subquery.c.recipient_id == Client.id)
    )

    # Фильтры
    if client_type:
        query = query.filter(Client.client_type == client_type)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Client.name.like(search_filter)) |
            (Client.phone.like(search_filter)) |
            (Client.email.like(search_filter))
        )

    clients = query.offset(skip).limit(limit).all()

    # Собираем статистику для каждого клиента
    result = []
    for client in clients:
        # Получаем статистику по заказам клиента
        client_orders = db.query(Order).filter(
            (Order.client_id == client.id) | (Order.recipient_id == client.id)
        ).all()

        total_orders = len(client_orders)
        total_spent = sum(order.total_price or 0 for order in client_orders)
        first_order_date = min((order.created_at for order in client_orders), default=None)
        last_order_date = max((order.created_at for order in client_orders), default=None)
        avg_order_value = total_spent / total_orders if total_orders > 0 else 0

        client_stats = ClientWithStatistics(
            id=client.id,
            name=client.name,
            phone=client.phone,
            email=client.email,
            client_type=client.client_type,
            notes=client.notes,
            created_at=client.created_at,
            total_orders=total_orders,
            first_order_date=first_order_date,
            last_order_date=last_order_date,
            total_spent=total_spent,
            average_order_value=avg_order_value
        )
        result.append(client_stats)

    # Сортировка
    if sort_by == "name":
        result.sort(key=lambda x: x.name or "", reverse=(sort_order == "desc"))
    elif sort_by == "total_orders":
        result.sort(key=lambda x: x.total_orders, reverse=(sort_order == "desc"))
    elif sort_by == "total_spent":
        result.sort(key=lambda x: x.total_spent, reverse=(sort_order == "desc"))
    elif sort_by == "last_order_date":
        result.sort(key=lambda x: x.last_order_date or datetime.min, reverse=(sort_order == "desc"))

    return result

@router.get("/clients/{client_id}/statistics", response_model=ClientStatistics)
async def get_client_statistics(
    client_id: int,
    db: Session = Depends(get_db)
):
    """Получить детальную статистику клиента"""
    from sqlalchemy import extract, func

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Получаем все заказы клиента
    orders = db.query(Order).filter(
        (Order.client_id == client_id) | (Order.recipient_id == client_id)
    ).all()

    if not orders:
        return ClientStatistics(
            client_id=client.id,
            client_name=client.name,
            client_phone=client.phone,
            total_orders=0,
            total_spent=0.0,
            average_order_value=0.0,
            first_order_date=None,
            last_order_date=None,
            days_since_first_order=None,
            days_since_last_order=None,
            orders_by_status={},
            favorite_categories=[],
            monthly_spending=[]
        )

    # Основная статистика
    total_orders = len(orders)
    total_spent = sum(order.total_price or 0 for order in orders)
    average_order_value = total_spent / total_orders
    first_order_date = min(order.created_at for order in orders)
    last_order_date = max(order.created_at for order in orders)

    # Расчет дней
    now = datetime.now()
    days_since_first = (now - first_order_date).days
    days_since_last = (now - last_order_date).days

    # Статистика по статусам
    orders_by_status = {}
    for status in ["новый", "в работе", "готов", "доставлен"]:
        count = len([o for o in orders if o.status == status])
        orders_by_status[status] = count

    # Любимые категории продуктов
    category_stats = {}
    for order in orders:
        for item in order.order_items:
            if item.product and item.product.category:
                category = item.product.category
                category_stats[category] = category_stats.get(category, 0) + item.quantity

    favorite_categories = [
        {"category": cat, "total_items": count}
        for cat, count in sorted(category_stats.items(), key=lambda x: x[1], reverse=True)
    ][:5]  # Топ 5 категорий

    # Помесячная статистика
    monthly_stats = {}
    for order in orders:
        month_key = order.created_at.strftime("%Y-%m")
        monthly_stats[month_key] = monthly_stats.get(month_key, 0) + (order.total_price or 0)

    monthly_spending = [
        {"month": month, "amount": amount}
        for month, amount in sorted(monthly_stats.items())
    ]

    return ClientStatistics(
        client_id=client.id,
        client_name=client.name,
        client_phone=client.phone,
        total_orders=total_orders,
        total_spent=total_spent,
        average_order_value=average_order_value,
        first_order_date=first_order_date,
        last_order_date=last_order_date,
        days_since_first_order=days_since_first,
        days_since_last_order=days_since_last,
        orders_by_status=orders_by_status,
        favorite_categories=favorite_categories,
        monthly_spending=monthly_spending
    )

@router.get("/clients/{client_id}/orders", response_model=ClientOrderHistory)
async def get_client_order_history(
    client_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, pattern=r'^(новый|в работе|готов|доставлен)$'),
    db: Session = Depends(get_db)
):
    """Получить историю заказов клиента с пагинацией"""

    client = db.query(Client).filter(Client.id == client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Запрос заказов
    query = db.query(Order).filter(
        (Order.client_id == client_id) | (Order.recipient_id == client_id)
    )

    if status:
        query = query.filter(Order.status == status)

    # Общее количество заказов
    total_orders = query.count()

    # Пагинация
    offset = (page - 1) * page_size
    orders = query.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

    # Преобразуем заказы в summary
    order_summaries = []
    for order in orders:
        # Подсчитаем количество и типы товаров
        items_count = sum(item.quantity for item in order.order_items)

        # Создаем краткое описание товаров
        product_types = {}
        for item in order.order_items:
            if item.product:
                category = item.product.category
                product_types[category] = product_types.get(category, 0) + item.quantity

        items_summary = ", ".join([
            f"{count} {category}" for category, count in product_types.items()
        ]) or "Нет товаров"

        order_summary = OrderSummary(
            id=order.id,
            status=order.status,
            delivery_date=order.delivery_date,
            total_price=order.total_price,
            created_at=order.created_at,
            items_count=items_count,
            items_summary=items_summary
        )
        order_summaries.append(order_summary)

    has_more = (page * page_size) < total_orders

    return ClientOrderHistory(
        client_id=client.id,
        client_name=client.name,
        total_orders=total_orders,
        orders=order_summaries,
        page=page,
        page_size=page_size,
        has_more=has_more
    )

# Products API Endpoints
@router.get("/products", response_model=List[ProductResponse])
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = Query(None, pattern=r'^(букет|композиция|горшечный)$'),
    search: Optional[str] = Query(None),
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all products with filters"""
    query = db.query(Product)

    if category:
        query = query.filter(Product.category == category)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Product.name.like(search_filter)) |
            (Product.description.like(search_filter))
        )

    products = query.offset(skip).limit(limit).all()
    return products

@router.get("/products/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get product details by ID"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@router.post("/products", response_model=ProductResponse)
async def create_product(
    product: ProductCreate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new product"""
    db_product = Product(**product.dict())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product

@router.put("/products/{product_id}", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update product"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)
    return db_product

@router.delete("/products/{product_id}")
async def delete_product(
    product_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete product"""
    db_product = db.query(Product).filter(Product.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Check if product has order items or inventory relations
    order_items_count = db.query(OrderItem).filter(OrderItem.product_id == product_id).count()
    inventory_relations_count = db.query(ProductInventory).filter(ProductInventory.product_id == product_id).count()

    if order_items_count > 0 or inventory_relations_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete product with existing order items or inventory relations"
        )

    db.delete(db_product)
    db.commit()
    return {"message": "Product deleted successfully"}

# Inventory API Endpoints
@router.get("/inventory", response_model=List[InventoryResponse])
async def get_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    low_stock_only: bool = Query(False),
    unit: Optional[str] = Query(None, pattern=r'^(шт|м|кг)$'),
    search: Optional[str] = Query(None),
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all inventory items with filters"""
    query = db.query(Inventory)

    if unit:
        query = query.filter(Inventory.unit == unit)

    if low_stock_only:
        query = query.filter(
            (Inventory.min_quantity.isnot(None)) &
            (Inventory.quantity <= Inventory.min_quantity)
        )

    if search:
        search_filter = f"%{search}%"
        query = query.filter(Inventory.name.like(search_filter))

    inventory_items = query.offset(skip).limit(limit).all()
    return inventory_items

@router.get("/inventory/{inventory_id}", response_model=InventoryResponse)
async def get_inventory_item(
    inventory_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get inventory item details by ID"""
    inventory_item = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not inventory_item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return inventory_item

@router.post("/inventory", response_model=InventoryResponse)
async def create_inventory_item(
    inventory: InventoryCreate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add new inventory item"""
    db_inventory = Inventory(**inventory.dict())
    db.add(db_inventory)
    db.commit()
    db.refresh(db_inventory)
    return db_inventory

@router.put("/inventory/{inventory_id}", response_model=InventoryResponse)
async def update_inventory_item(
    inventory_id: int,
    inventory: InventoryUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update inventory item"""
    db_inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    update_data = inventory.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_inventory, field, value)

    db.commit()
    db.refresh(db_inventory)
    return db_inventory

@router.delete("/inventory/{inventory_id}")
async def delete_inventory_item(
    inventory_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete inventory item"""
    db_inventory = db.query(Inventory).filter(Inventory.id == inventory_id).first()
    if not db_inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Check if inventory item is used in product inventories
    product_inventory_count = db.query(ProductInventory).filter(ProductInventory.inventory_id == inventory_id).count()
    if product_inventory_count > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete inventory item that is used by products"
        )

    db.delete(db_inventory)
    db.commit()
    return {"message": "Inventory item deleted successfully"}

# Orders API Endpoints
@router.get("/orders")  # Temporarily removed response_model for debugging
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = Query(None, pattern=r'^(новый|в работе|готов|доставлен)$'),
    client_id: Optional[int] = Query(None),
    executor_id: Optional[int] = Query(None),
    date_from: Optional[date] = Query(None),
    date_to: Optional[date] = Query(None),
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all orders with filters"""
    query = db.query(Order)

    if status:
        query = query.filter(Order.status == status)

    if client_id:
        query = query.filter(
            (Order.client_id == client_id) | (Order.recipient_id == client_id)
        )

    if executor_id:
        query = query.filter(Order.executor_id == executor_id)

    if date_from:
        query = query.filter(Order.created_at >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.filter(Order.created_at <= datetime.combine(date_to, datetime.max.time()))

    orders = query.order_by(Order.created_at.desc()).offset(skip).limit(limit).all()

    # Convert to response format with nested data
    orders_response = []
    for order in orders:
        # Convert SQLAlchemy objects to dictionaries
        client_dict = None
        if order.client:
            client_dict = {
                "id": order.client.id,
                "name": order.client.name,
                "phone": order.client.phone,
                "address": order.client.address if hasattr(order.client, 'address') else None,
                "email": order.client.email if hasattr(order.client, 'email') else None,
            }

        recipient_dict = None
        if order.recipient:
            recipient_dict = {
                "id": order.recipient.id,
                "name": order.recipient.name,
                "phone": order.recipient.phone,
                "address": order.recipient.address if hasattr(order.recipient, 'address') else None,
                "email": order.recipient.email if hasattr(order.recipient, 'email') else None,
            }

        executor_dict = None
        if order.executor:
            executor_dict = {
                "id": order.executor.id,
                "username": order.executor.username,
                "email": order.executor.email,
                "city": order.executor.city if hasattr(order.executor, 'city') else None,
                "position": order.executor.position if hasattr(order.executor, 'position') else None,
            }

        # Convert order items
        order_items_list = []
        if order.order_items:
            for item in order.order_items:
                item_dict = {
                    "id": item.id,
                    "product_id": item.product_id,
                    "quantity": item.quantity,
                    "price": item.price,
                    "product": {
                        "id": item.product.id,
                        "name": item.product.name,
                        "price": item.product.price
                    } if hasattr(item, 'product') and item.product else None
                }
                order_items_list.append(item_dict)

        order_dict = {
            "id": order.id,
            "client_id": order.client_id,
            "recipient_id": order.recipient_id,
            "executor_id": order.executor_id,
            "status": order.status,
            "delivery_date": order.delivery_date,
            "delivery_address": order.delivery_address,
            "total_price": order.total_price,
            "comment": order.comment,
            "created_at": order.created_at,
            "client": client_dict,
            "recipient": recipient_dict,
            "executor": executor_dict,
            "order_items": order_items_list
        }
        orders_response.append(order_dict)

    return orders_response

@router.get("/orders/{order_id}", response_model=OrderResponse)
async def get_order(
    order_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order details by ID"""
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    return {
        "id": order.id,
        "client_id": order.client_id,
        "recipient_id": order.recipient_id,
        "executor_id": order.executor_id,
        "status": order.status,
        "delivery_date": order.delivery_date,
        "delivery_address": order.delivery_address,
        "total_price": order.total_price,
        "comment": order.comment,
        "created_at": order.created_at,
        "client": {
            "id": order.client.id,
            "name": order.client.name,
            "phone": order.client.phone,
            "address": order.client.address,
            "email": order.client.email,
            "client_type": order.client.client_type,
            "notes": order.client.notes,
            "created_at": order.client.created_at,
        } if order.client else None,
        "recipient": {
            "id": order.recipient.id,
            "name": order.recipient.name,
            "phone": order.recipient.phone,
            "address": order.recipient.address,
            "email": order.recipient.email,
            "client_type": order.recipient.client_type,
            "notes": order.recipient.notes,
            "created_at": order.recipient.created_at,
        } if order.recipient else None,
        "executor": {
            "id": order.executor.id,
            "username": order.executor.username,
            "email": order.executor.email,
            "city": order.executor.city if hasattr(order.executor, 'city') else None,
            "position": order.executor.position if hasattr(order.executor, 'position') else None,
        } if order.executor else None,
        "order_items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "description": item.product.description,
                    "price": item.product.price,
                    "category": item.product.category,
                    "preparation_time": item.product.preparation_time,
                    "image_url": item.product.image_url,
                    "created_at": item.product.created_at
                } if hasattr(item, 'product') and item.product else None
            } for item in order.order_items
        ] if order.order_items else []
    }

@router.post("/orders", response_model=OrderResponse)
async def create_order(
    order: OrderCreate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create new order with items"""
    # Validate client and recipient exist
    client = db.query(Client).filter(Client.id == order.client_id).first()
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    recipient = db.query(Client).filter(Client.id == order.recipient_id).first()
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    # Validate executor if provided
    if order.executor_id:
        executor = db.query(User).filter(User.id == order.executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Executor not found")

    # Calculate total price
    total_price = calculate_order_total(order.items, db)

    # Create order
    order_data = order.dict(exclude={'items'})
    order_data['total_price'] = total_price

    db_order = Order(**order_data)
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Create order items
    for item in order.items:
        # Validate product exists
        product = db.query(Product).filter(Product.id == item.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail=f"Product {item.product_id} not found")

        item_price = item.price if item.price else product.price
        db_order_item = OrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item_price
        )
        db.add(db_order_item)

    db.commit()
    db.refresh(db_order)

    return {
        "id": db_order.id,
        "client_id": db_order.client_id,
        "recipient_id": db_order.recipient_id,
        "executor_id": db_order.executor_id,
        "status": db_order.status,
        "delivery_date": db_order.delivery_date,
        "delivery_address": db_order.delivery_address,
        "total_price": db_order.total_price,
        "comment": db_order.comment,
        "created_at": db_order.created_at,
        "client": {
            "id": db_order.client.id,
            "name": db_order.client.name,
            "phone": db_order.client.phone,
            "address": db_order.client.address,
            "email": db_order.client.email,
            "client_type": db_order.client.client_type,
            "notes": db_order.client.notes,
            "created_at": db_order.client.created_at,
        } if db_order.client else None,
        "recipient": {
            "id": db_order.recipient.id,
            "name": db_order.recipient.name,
            "phone": db_order.recipient.phone,
            "address": db_order.recipient.address,
            "email": db_order.recipient.email,
            "client_type": db_order.recipient.client_type,
            "notes": db_order.recipient.notes,
            "created_at": db_order.recipient.created_at,
        } if db_order.recipient else None,
        "executor": {
            "id": db_order.executor.id,
            "username": db_order.executor.username,
            "email": db_order.executor.email,
            "city": db_order.executor.city if hasattr(db_order.executor, 'city') else None,
            "position": db_order.executor.position if hasattr(db_order.executor, 'position') else None,
        } if db_order.executor else None,
        "order_items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "description": item.product.description,
                    "price": item.product.price,
                    "category": item.product.category,
                    "preparation_time": item.product.preparation_time,
                    "image_url": item.product.image_url,
                    "created_at": item.product.created_at
                } if hasattr(item, 'product') and item.product else None
            } for item in db_order.order_items
        ] if db_order.order_items else []
    }

@router.put("/orders/{order_id}", response_model=OrderResponse)
async def update_order(
    order_id: int,
    order: OrderUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order"""
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Validate recipient if being updated
    if order.recipient_id:
        recipient = db.query(Client).filter(Client.id == order.recipient_id).first()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")

    # Validate executor if being updated
    if order.executor_id:
        executor = db.query(User).filter(User.id == order.executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Executor not found")

    update_data = order.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_order, field, value)

    db.commit()
    db.refresh(db_order)

    return {
        "id": db_order.id,
        "client_id": db_order.client_id,
        "recipient_id": db_order.recipient_id,
        "executor_id": db_order.executor_id,
        "status": db_order.status,
        "delivery_date": db_order.delivery_date,
        "delivery_address": db_order.delivery_address,
        "total_price": db_order.total_price,
        "comment": db_order.comment,
        "created_at": db_order.created_at,
        "client": {
            "id": db_order.client.id,
            "name": db_order.client.name,
            "phone": db_order.client.phone,
            "address": db_order.client.address,
            "email": db_order.client.email,
            "client_type": db_order.client.client_type,
            "notes": db_order.client.notes,
            "created_at": db_order.client.created_at,
        } if db_order.client else None,
        "recipient": {
            "id": db_order.recipient.id,
            "name": db_order.recipient.name,
            "phone": db_order.recipient.phone,
            "address": db_order.recipient.address,
            "email": db_order.recipient.email,
            "client_type": db_order.recipient.client_type,
            "notes": db_order.recipient.notes,
            "created_at": db_order.recipient.created_at,
        } if db_order.recipient else None,
        "executor": {
            "id": db_order.executor.id,
            "username": db_order.executor.username,
            "email": db_order.executor.email,
            "city": db_order.executor.city if hasattr(db_order.executor, 'city') else None,
            "position": db_order.executor.position if hasattr(db_order.executor, 'position') else None,
        } if db_order.executor else None,
        "order_items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "description": item.product.description,
                    "price": item.product.price,
                    "category": item.product.category,
                    "preparation_time": item.product.preparation_time,
                    "image_url": item.product.image_url,
                    "created_at": item.product.created_at
                } if hasattr(item, 'product') and item.product else None
            } for item in db_order.order_items
        ] if db_order.order_items else []
    }

@router.patch("/orders/{order_id}", response_model=OrderResponse)
async def partial_update_order(
    order_id: int,
    order: OrderUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Partial update order (PATCH method)"""
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    update_data = order.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Validate recipient if being updated
    if order.recipient_id:
        recipient = db.query(Client).filter(Client.id == order.recipient_id).first()
        if not recipient:
            raise HTTPException(status_code=404, detail="Recipient not found")

    # Validate executor if being updated
    if order.executor_id:
        executor = db.query(User).filter(User.id == order.executor_id).first()
        if not executor:
            raise HTTPException(status_code=404, detail="Executor not found")

    for field, value in update_data.items():
        setattr(db_order, field, value)

    db.commit()
    db.refresh(db_order)

    return {
        "id": db_order.id,
        "client_id": db_order.client_id,
        "recipient_id": db_order.recipient_id,
        "executor_id": db_order.executor_id,
        "status": db_order.status,
        "delivery_date": db_order.delivery_date,
        "delivery_address": db_order.delivery_address,
        "total_price": db_order.total_price,
        "comment": db_order.comment,
        "created_at": db_order.created_at,
        "client": {
            "id": db_order.client.id,
            "name": db_order.client.name,
            "phone": db_order.client.phone,
            "address": db_order.client.address,
            "email": db_order.client.email,
            "client_type": db_order.client.client_type,
            "notes": db_order.client.notes,
            "created_at": db_order.client.created_at,
        } if db_order.client else None,
        "recipient": {
            "id": db_order.recipient.id,
            "name": db_order.recipient.name,
            "phone": db_order.recipient.phone,
            "address": db_order.recipient.address,
            "email": db_order.recipient.email,
            "client_type": db_order.recipient.client_type,
            "notes": db_order.recipient.notes,
            "created_at": db_order.recipient.created_at,
        } if db_order.recipient else None,
        "executor": {
            "id": db_order.executor.id,
            "username": db_order.executor.username,
            "email": db_order.executor.email,
            "city": db_order.executor.city if hasattr(db_order.executor, 'city') else None,
            "position": db_order.executor.position if hasattr(db_order.executor, 'position') else None,
        } if db_order.executor else None,
        "order_items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "description": item.product.description,
                    "price": item.product.price,
                    "category": item.product.category,
                    "preparation_time": item.product.preparation_time,
                    "image_url": item.product.image_url,
                    "created_at": item.product.created_at
                } if hasattr(item, 'product') and item.product else None
            } for item in db_order.order_items
        ] if db_order.order_items else []
    }

@router.put("/orders/{order_id}/status", response_model=OrderResponse)
async def update_order_status(
    order_id: int,
    status_update: OrderStatusUpdate,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update order status"""
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    db_order.status = status_update.status
    db.commit()
    db.refresh(db_order)

    return {
        "id": db_order.id,
        "client_id": db_order.client_id,
        "recipient_id": db_order.recipient_id,
        "executor_id": db_order.executor_id,
        "status": db_order.status,
        "delivery_date": db_order.delivery_date,
        "delivery_address": db_order.delivery_address,
        "total_price": db_order.total_price,
        "comment": db_order.comment,
        "created_at": db_order.created_at,
        "client": {
            "id": db_order.client.id,
            "name": db_order.client.name,
            "phone": db_order.client.phone,
            "address": db_order.client.address,
            "email": db_order.client.email,
            "client_type": db_order.client.client_type,
            "notes": db_order.client.notes,
            "created_at": db_order.client.created_at,
        } if db_order.client else None,
        "recipient": {
            "id": db_order.recipient.id,
            "name": db_order.recipient.name,
            "phone": db_order.recipient.phone,
            "address": db_order.recipient.address,
            "email": db_order.recipient.email,
            "client_type": db_order.recipient.client_type,
            "notes": db_order.recipient.notes,
            "created_at": db_order.recipient.created_at,
        } if db_order.recipient else None,
        "executor": {
            "id": db_order.executor.id,
            "username": db_order.executor.username,
            "email": db_order.executor.email,
            "city": db_order.executor.city if hasattr(db_order.executor, 'city') else None,
            "position": db_order.executor.position if hasattr(db_order.executor, 'position') else None,
        } if db_order.executor else None,
        "order_items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "price": item.price,
                "product": {
                    "id": item.product.id,
                    "name": item.product.name,
                    "description": item.product.description,
                    "price": item.product.price,
                    "category": item.product.category,
                    "preparation_time": item.product.preparation_time,
                    "image_url": item.product.image_url,
                    "created_at": item.product.created_at
                } if hasattr(item, 'product') and item.product else None
            } for item in db_order.order_items
        ] if db_order.order_items else []
    }

@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete order"""
    db_order = db.query(Order).filter(Order.id == order_id).first()
    if not db_order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Only allow deletion of new orders
    if db_order.status not in ["новый"]:
        raise HTTPException(
            status_code=400,
            detail="Can only delete orders with status 'новый'"
        )

    db.delete(db_order)
    db.commit()
    return {"message": "Order deleted successfully"}

# Additional utility endpoints
@router.get("/stats/dashboard")
async def get_dashboard_stats(
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    today = datetime.now().date()

    # Total counts
    total_clients = db.query(Client).count()
    total_products = db.query(Product).count()
    total_orders = db.query(Order).count()

    # Today's orders
    today_orders = db.query(Order).filter(
        Order.created_at >= datetime.combine(today, datetime.min.time())
    ).count()

    # Low stock items
    low_stock_items = db.query(Inventory).filter(
        (Inventory.min_quantity.isnot(None)) &
        (Inventory.quantity <= Inventory.min_quantity)
    ).count()

    # Revenue this month
    from sqlalchemy import extract, func
    current_month = datetime.now().month
    current_year = datetime.now().year

    monthly_revenue = db.query(func.sum(Order.total_price)).filter(
        extract('month', Order.created_at) == current_month,
        extract('year', Order.created_at) == current_year,
        Order.status != "отменен"
    ).scalar() or 0.0

    # Orders by status
    orders_by_status = {}
    for status in ["новый", "в работе", "готов", "доставлен"]:
        count = db.query(Order).filter(Order.status == status).count()
        orders_by_status[status] = count

    return {
        "total_clients": total_clients,
        "total_products": total_products,
        "total_orders": total_orders,
        "today_orders": today_orders,
        "low_stock_items": low_stock_items,
        "monthly_revenue": monthly_revenue,
        "orders_by_status": orders_by_status
    }

@router.get("/products/{product_id}/inventory")
async def get_product_inventory(
    product_id: int,
    # current_user = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get inventory items needed for a specific product"""
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    inventory_relations = db.query(ProductInventory).filter(
        ProductInventory.product_id == product_id
    ).all()

    result = []
    for relation in inventory_relations:
        inventory_item = relation.inventory
        result.append({
            "inventory_id": inventory_item.id,
            "inventory_name": inventory_item.name,
            "quantity_needed": relation.quantity_needed,
            "available_quantity": inventory_item.quantity,
            "unit": inventory_item.unit,
            "sufficient": inventory_item.quantity >= relation.quantity_needed
        })

    return {
        "product_id": product_id,
        "product_name": product.name,
        "inventory_requirements": result
    }

# Advanced search endpoints

@router.get("/clients/search")
def search_clients(
    query: Optional[str] = Query(None, description="Search in name, phone, email"),
    client_type: Optional[str] = Query(None, description="Filter by client type"),
    has_orders: Optional[bool] = Query(None, description="Filter clients with/without orders"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Advanced client search with filters"""
    query_builder = db.query(Client)

    # Text search
    if query:
        search_term = f"%{query}%"
        query_builder = query_builder.filter(
            or_(
                Client.name.ilike(search_term),
                Client.phone.ilike(search_term),
                Client.email.ilike(search_term)
            )
        )

    # Filter by client type
    if client_type:
        query_builder = query_builder.filter(Client.client_type == client_type)

    # Count total
    total = query_builder.count()

    # Apply pagination
    offset = (page - 1) * page_size
    clients = query_builder.offset(offset).limit(page_size).all()

    return {
        "clients": clients,
        "total": total,
        "page": page,
        "page_size": page_size
    }

@router.get("/orders/search")
def search_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    client_phone: Optional[str] = Query(None, description="Filter by client phone"),
    executor_id: Optional[int] = Query(None, description="Filter by assigned florist"),
    date_from: Optional[date] = Query(None, description="Filter orders from date (YYYY-MM-DD)"),
    date_to: Optional[date] = Query(None, description="Filter orders to date (YYYY-MM-DD)"),
    min_price: Optional[float] = Query(None, description="Minimum order price"),
    max_price: Optional[float] = Query(None, description="Maximum order price"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Advanced order search with filters"""
    query_builder = db.query(Order)

    # Filter by status
    if status:
        query_builder = query_builder.filter(Order.status == status)

    # Filter by client phone
    if client_phone:
        query_builder = query_builder.join(Client, Order.client_id == Client.id).filter(Client.phone.ilike(f"%{client_phone}%"))

    # Filter by executor
    if executor_id:
        query_builder = query_builder.filter(Order.executor_id == executor_id)

    # Filter by date range
    if date_from:
        query_builder = query_builder.filter(Order.delivery_date >= date_from)
    if date_to:
        query_builder = query_builder.filter(Order.delivery_date <= date_to)

    # Filter by price range
    if min_price:
        query_builder = query_builder.filter(Order.total_price >= min_price)
    if max_price:
        query_builder = query_builder.filter(Order.total_price <= max_price)

    # Count total
    total = query_builder.count()

    # Apply pagination and ordering
    offset = (page - 1) * page_size
    orders = query_builder.order_by(Order.created_at.desc()).offset(offset).limit(page_size).all()

    # Format response with full order details
    formatted_orders = []
    for order in orders:
        formatted_orders.append({
            "id": order.id,
            "client_id": order.client_id,
            "recipient_id": order.recipient_id,
            "executor_id": order.executor_id,
            "status": order.status,
            "delivery_date": order.delivery_date,
            "delivery_address": order.delivery_address,
            "total_price": order.total_price,
            "comment": order.comment,
            "created_at": order.created_at,
            "client": {
                "id": order.client.id,
                "name": order.client.name,
                "phone": order.client.phone,
                "client_type": order.client.client_type,
            } if order.client else None,
            "recipient": {
                "id": order.recipient.id,
                "name": order.recipient.name,
                "phone": order.recipient.phone,
            } if order.recipient else None,
            "executor": {
                "id": order.executor.id,
                "username": order.executor.username,
                "position": order.executor.position if hasattr(order.executor, 'position') else None,
            } if order.executor else None,
        })

    return {
        "orders": formatted_orders,
        "total": total,
        "page": page,
        "page_size": page_size
    }

# Endpoint для инициализации тестовых данных клиентов
@router.post("/initialize-sample-clients")
async def initialize_sample_clients(db: Session = Depends(get_db)):
    """Создать тестовых клиентов и заказы для демонстрации статистики"""
    from datetime import timedelta
    import random

    # Проверяем, есть ли уже клиенты
    existing_clients = db.query(Client).count()
    if existing_clients > 0:
        return {"message": "Sample clients already exist", "count": existing_clients}

    # Создаем тестовых клиентов
    sample_clients = [
        {
            "name": "Анна Иванова",
            "phone": "+77011234567",
            "email": "anna@example.com",
            "client_type": "заказчик",
            "notes": "Постоянный клиент, любит розы"
        },
        {
            "name": "Мария Петрова",
            "phone": "+77021234567",
            "email": "maria@example.com",
            "client_type": "заказчик",
            "notes": "Заказывает для офиса"
        },
        {
            "name": None,  # Клиент без имени
            "phone": "+77031234567",
            "email": None,
            "client_type": "заказчик",
            "notes": "Анонимный клиент"
        },
        {
            "name": "Ольга Сидорова",
            "phone": "+77041234567",
            "email": "olga@example.com",
            "client_type": "получатель",
            "notes": "Получает подарки"
        },
        {
            "name": "Елена Козлова",
            "phone": "+77051234567",
            "email": "elena@example.com",
            "client_type": "оба",
            "notes": "VIP клиент"
        },
        {
            "name": "Дарья Новикова",
            "phone": "+77061234567",
            "client_type": "заказчик",
            "notes": "Новый клиент"
        }
    ]

    created_clients = []
    for client_data in sample_clients:
        client = Client(**client_data)
        db.add(client)
        db.flush()  # Получаем ID
        created_clients.append(client)

    # Создаем тестовые продукты, если их нет
    existing_products = db.query(Product).count()
    if existing_products == 0:
        sample_products = [
            {
                "name": "Букет роз",
                "description": "Красивый букет из свежих роз",
                "price": 15000.0,
                "category": "букет"
            },
            {
                "name": "Композиция в корзине",
                "description": "Элегантная композиция в плетеной корзине",
                "price": 25000.0,
                "category": "композиция"
            },
            {
                "name": "Фикус в горшке",
                "description": "Комнатное растение в декоративном горшке",
                "price": 8000.0,
                "category": "горшечный"
            }
        ]

        created_products = []
        for product_data in sample_products:
            product = Product(**product_data)
            db.add(product)
            db.flush()
            created_products.append(product)
    else:
        created_products = db.query(Product).all()

    # Создаем тестовые заказы с разными датами
    base_date = datetime.now() - timedelta(days=90)  # 3 месяца назад
    created_orders = []

    for i, client in enumerate(created_clients):
        # Каждый клиент получает от 1 до 5 заказов
        num_orders = random.randint(1, 5)

        for j in range(num_orders):
            # Случайная дата в последние 90 дней
            days_offset = random.randint(0, 90)
            order_date = base_date + timedelta(days=days_offset)
            delivery_date = order_date + timedelta(days=random.randint(1, 3))

            # Выбираем случайный продукт
            product = random.choice(created_products)
            quantity = random.randint(1, 3)
            total_price = product.price * quantity

            # Статус заказа
            statuses = ["новый", "в работе", "готов", "доставлен"]
            # Старые заказы чаще доставлены
            if days_offset > 30:
                status = random.choice(["готов", "доставлен"])
            else:
                status = random.choice(statuses)

            # Создаем заказ
            order = Order(
                client_id=client.id,
                recipient_id=client.id,  # Упрощаем - клиент и получатель одинаковые
                status=status,
                delivery_date=delivery_date,
                delivery_address=f"Адрес доставки {i+1}",
                total_price=total_price,
                comment=f"Тестовый заказ №{len(created_orders)+1}",
                created_at=order_date
            )
            db.add(order)
            db.flush()

            # Создаем позиции заказа
            order_item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                price=product.price
            )
            db.add(order_item)
            created_orders.append(order)

    db.commit()

    return {
        "message": "Sample data created successfully",
        "clients_created": len(created_clients),
        "products_created": len(created_products) if existing_products == 0 else 0,
        "orders_created": len(created_orders),
        "orders_total_value": sum(order.total_price for order in created_orders)
    }