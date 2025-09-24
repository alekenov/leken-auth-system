"""
CRM API с использованием SQLModel
Упрощенная версия без дублирования моделей
"""
from fastapi import APIRouter, HTTPException, Depends, Query, status, Body
from typing import List, Optional
from datetime import datetime, date, timedelta
from sqlmodel import Session, select, func
from sqlalchemy import case
from pydantic import BaseModel
import re

from models_sqlmodel import (
    Client, ClientType,
    Product, ProductCategory,
    Order, OrderStatus, OrderItem, OrderHistory,
    Inventory, ProductInventory,
    User, UserPosition,
    Shop,
    get_session, engine
)
from auth_db import get_current_user

# Create router
router = APIRouter()

# ============= CLIENTS API =============

@router.get("/clients", response_model=List[Client])
async def get_clients(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = None,
    client_type: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Получить список клиентов с фильтрацией"""
    query = select(Client)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Client.name.ilike(search_pattern)) |
            (Client.phone.ilike(search_pattern)) |
            (Client.email.ilike(search_pattern))
        )

    if client_type and client_type in ["заказчик", "получатель", "оба"]:
        query = query.where(Client.client_type == client_type)

    query = query.offset(skip).limit(limit)
    clients = db.exec(query).all()
    return clients


@router.get("/clients/{client_id}", response_model=Client)
async def get_client(client_id: int, db: Session = Depends(get_session)):
    """Получить клиента по ID"""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    return client


@router.post("/clients", response_model=Client)
async def create_client(
    client: Client,
    db: Session = Depends(get_session)
):
    """Создать нового клиента"""
    # Валидация телефона
    if not re.match(r'^\+7\d{10}$', client.phone):
        raise HTTPException(
            status_code=400,
            detail="Phone must be in format +7XXXXXXXXXX"
        )

    # Проверка на дубликат телефона
    existing = db.exec(
        select(Client).where(Client.phone == client.phone)
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Client with this phone already exists"
        )

    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.put("/clients/{client_id}", response_model=Client)
async def update_client(
    client_id: int,
    client_update: Client,
    db: Session = Depends(get_session)
):
    """Обновить клиента"""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Обновляем только переданные поля
    update_data = client_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key != 'id':
            setattr(client, key, value)

    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.patch("/clients/{client_id}", response_model=Client)
async def patch_client(
    client_id: int,
    client_update: dict,
    db: Session = Depends(get_session)
):
    """Частично обновить клиента"""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Применяем только переданные поля
    for key, value in client_update.items():
        if key != 'id' and hasattr(client, key):
            setattr(client, key, value)

    db.add(client)
    db.commit()
    db.refresh(client)
    return client


@router.delete("/clients/{client_id}")
async def delete_client(client_id: int, db: Session = Depends(get_session)):
    """Удалить клиента"""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Проверяем, есть ли заказы
    orders_count = db.exec(
        select(func.count()).select_from(Order)
        .where((Order.client_id == client_id) | (Order.recipient_id == client_id))
    ).one()

    if orders_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete client with {orders_count} orders"
        )

    db.delete(client)
    db.commit()
    return {"message": "Client deleted successfully"}


@router.get("/clients/{client_id}/orders")
async def get_client_orders(
    client_id: int,
    db: Session = Depends(get_session)
):
    """Получить заказы клиента"""
    client = db.get(Client, client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    # Заказы где клиент - заказчик
    as_customer = db.exec(
        select(Order).where(Order.client_id == client_id)
    ).all()

    # Заказы где клиент - получатель
    as_recipient = db.exec(
        select(Order).where(Order.recipient_id == client_id)
    ).all()

    return {
        "client": client,
        "orders_as_customer": as_customer,
        "orders_as_recipient": as_recipient,
        "total_orders": len(as_customer) + len(as_recipient)
    }


@router.get("/customers")
async def get_customers(db: Session = Depends(get_session)):
    """Получить клиентов с статистикой для фронтенда (прямая адаптация без маппинга)"""

    # Подзапрос для статистики заказов по клиентам
    order_stats = select(
        Order.client_id,
        func.count(Order.id).label('total_orders'),
        func.coalesce(func.sum(Order.total_price), 0).label('total_spent'),
        func.max(Order.created_at).label('last_order_date')
    ).group_by(Order.client_id).subquery()

    # Основной запрос с JOIN
    query = select(
        Client.id,
        Client.name,
        Client.phone,
        Client.created_at.label('memberSince'),
        func.coalesce(order_stats.c.total_orders, 0).label('totalOrders'),
        func.coalesce(order_stats.c.total_spent, 0).label('totalSpent'),
        order_stats.c.last_order_date.label('lastOrderDate'),
        Client.notes,
        # Логика определения статуса: VIP (>=50000 ₸), Active (>=1 заказ), Inactive (0 заказов)
        case(
            (order_stats.c.total_spent >= 50000, 'vip'),
            (order_stats.c.total_orders >= 1, 'active'),
            else_='inactive'
        ).label('status')
    ).outerjoin(
        order_stats, Client.id == order_stats.c.client_id
    )

    results = db.exec(query).all()

    # Преобразуем результаты в формат, ожидаемый фронтендом
    customers = []
    for row in results:
        customer = {
            "id": row.id,
            "name": row.name,
            "phone": row.phone,
            "memberSince": row.memberSince.isoformat() if row.memberSince else None,
            "totalOrders": int(row.totalOrders),
            "totalSpent": float(row.totalSpent),
            "lastOrderDate": row.lastOrderDate.isoformat() if row.lastOrderDate else None,
            "status": row.status,
            "notes": row.notes
        }
        customers.append(customer)

    return customers


# ============= PRODUCTS API =============

@router.get("/products", response_model=List[Product], response_model_exclude_none=False)
async def get_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    category: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Получить список продуктов"""
    query = select(Product)

    if category:
        query = query.where(Product.category == category)

    if min_price is not None:
        query = query.where(Product.price >= min_price)

    if max_price is not None:
        query = query.where(Product.price <= max_price)

    if search:
        query = query.where(
            (Product.name.ilike(f"%{search}%")) |
            (Product.description.ilike(f"%{search}%"))
        )

    query = query.offset(skip).limit(limit)
    products = db.exec(query).all()
    return products


@router.get("/products/{product_id}", response_model=Product, response_model_exclude_none=False)
async def get_product(product_id: int, db: Session = Depends(get_session)):
    """Получить продукт по ID"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.post("/products", response_model=Product, response_model_exclude_none=False)
async def create_product(
    product: Product,
    db: Session = Depends(get_session)
):
    """Создать новый продукт"""
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.put("/products/{product_id}", response_model=Product, response_model_exclude_none=False)
async def update_product(
    product_id: int,
    product_update: Product,
    db: Session = Depends(get_session)
):
    """Обновить продукт"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key != 'id':
            setattr(product, key, value)

    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.delete("/products/{product_id}")
async def delete_product(product_id: int, db: Session = Depends(get_session)):
    """Удалить продукт"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db.delete(product)
    db.commit()
    return {"message": "Product deleted successfully"}


# ============= PRODUCT COMPOSITION API =============

@router.get("/products/{product_id}/composition")
async def get_product_composition(
    product_id: int,
    db: Session = Depends(get_session)
):
    """Получить состав продукта"""
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    query = select(ProductInventory).where(ProductInventory.product_id == product_id)
    composition = db.exec(query).all()

    # Формируем ответ с информацией о материалах
    result = []
    for item in composition:
        inventory = db.get(Inventory, item.inventory_id)
        result.append({
            "id": item.id,
            "product_id": item.product_id,
            "inventory_id": item.inventory_id,
            "quantity_needed": item.quantity_needed,
            "inventory": {
                "id": inventory.id,
                "name": inventory.name,
                "unit": inventory.unit,
                "price_per_unit": inventory.price_per_unit,
                "quantity": inventory.quantity
            } if inventory else None
        })

    return result


@router.post("/products/{product_id}/composition", response_model=ProductInventory)
async def add_product_composition(
    product_id: int,
    inventory_id: int,
    quantity_needed: float,
    db: Session = Depends(get_session)
):
    """Добавить компонент в состав продукта"""
    # Проверяем существование продукта
    product = db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Проверяем существование инвентаря
    inventory = db.get(Inventory, inventory_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Проверяем, нет ли уже такой связи
    existing = db.exec(
        select(ProductInventory).where(
            (ProductInventory.product_id == product_id) &
            (ProductInventory.inventory_id == inventory_id)
        )
    ).first()

    if existing:
        # Обновляем количество если связь уже существует
        existing.quantity_needed = quantity_needed
        db.commit()
        db.refresh(existing)
        existing.inventory = inventory
        return existing

    # Создаем новую связь
    composition = ProductInventory(
        product_id=product_id,
        inventory_id=inventory_id,
        quantity_needed=quantity_needed
    )

    db.add(composition)
    db.commit()
    db.refresh(composition)
    composition.inventory = inventory

    return composition


@router.put("/products/{product_id}/composition/{composition_id}", response_model=ProductInventory)
async def update_product_composition(
    product_id: int,
    composition_id: int,
    quantity_needed: float,
    db: Session = Depends(get_session)
):
    """Обновить количество компонента в составе"""
    composition = db.get(ProductInventory, composition_id)
    if not composition or composition.product_id != product_id:
        raise HTTPException(status_code=404, detail="Composition item not found")

    composition.quantity_needed = quantity_needed
    db.commit()
    db.refresh(composition)
    composition.inventory = db.get(Inventory, composition.inventory_id)

    return composition


@router.delete("/products/{product_id}/composition/{composition_id}")
async def delete_product_composition(
    product_id: int,
    composition_id: int,
    db: Session = Depends(get_session)
):
    """Удалить компонент из состава продукта"""
    composition = db.get(ProductInventory, composition_id)
    if not composition or composition.product_id != product_id:
        raise HTTPException(status_code=404, detail="Composition item not found")

    db.delete(composition)
    db.commit()

    return {"message": "Composition item deleted successfully"}


# ============= INVENTORY API =============

@router.get("/inventory", response_model=List[Inventory])
async def get_inventory(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    low_stock: Optional[bool] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_session)
):
    """Получить список складских позиций"""
    query = select(Inventory)

    if low_stock:
        query = query.where(
            (Inventory.min_quantity.isnot(None)) &
            (Inventory.quantity <= Inventory.min_quantity)
        )

    if search:
        query = query.where(Inventory.name.ilike(f"%{search}%"))

    query = query.offset(skip).limit(limit)
    items = db.exec(query).all()
    return items


@router.get("/inventory/{inventory_id}", response_model=Inventory)
async def get_inventory_item(inventory_id: int, db: Session = Depends(get_session)):
    """Получить складскую позицию по ID"""
    item = db.get(Inventory, inventory_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")
    return item


@router.post("/inventory", response_model=Inventory)
async def create_inventory_item(
    item: Inventory,
    db: Session = Depends(get_session)
):
    """Создать новую складскую позицию"""
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/inventory/{inventory_id}", response_model=Inventory)
async def update_inventory_item(
    inventory_id: int,
    item_update: Inventory,
    db: Session = Depends(get_session)
):
    """Обновить складскую позицию"""
    from models_sqlmodel import InventoryTransaction, TransactionType

    item = db.get(Inventory, inventory_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Save old prices for comparison
    old_price = item.price_per_unit
    old_cost_price = item.cost_price if hasattr(item, 'cost_price') else None

    update_data = item_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        if key != 'id':
            setattr(item, key, value)

    # Check if prices changed and create transaction
    new_price = item.price_per_unit
    new_cost_price = item.cost_price if hasattr(item, 'cost_price') else None

    if (old_price != new_price) or (old_cost_price != new_cost_price):
        # Create price change transaction
        comment_parts = []
        if old_price != new_price:
            comment_parts.append(f"Цена: {old_price} → {new_price}")
        if old_cost_price != new_cost_price:
            comment_parts.append(f"Себестоимость: {old_cost_price} → {new_cost_price}")

        transaction = InventoryTransaction(
            inventory_id=inventory_id,
            transaction_type=TransactionType.PRICE_CHANGE,
            quantity=0,  # Price change doesn't affect quantity
            comment=" | ".join(comment_parts),
            reference_type="manual",
            reference_id=None
        )
        db.add(transaction)

    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/inventory/{inventory_id}")
async def delete_inventory_item(inventory_id: int, db: Session = Depends(get_session)):
    """Удалить складскую позицию"""
    item = db.get(Inventory, inventory_id)
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    db.delete(item)
    db.commit()
    return {"message": "Inventory item deleted successfully"}


# ============= ORDERS API =============

@router.get("/orders", response_model=List[Order])
async def get_orders(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: Optional[str] = None,
    client_id: Optional[int] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_session)
):
    """Получить список заказов"""
    query = select(Order)

    if status:
        query = query.where(Order.status == status)

    if client_id:
        query = query.where(
            (Order.client_id == client_id) | (Order.recipient_id == client_id)
        )

    if date_from:
        query = query.where(Order.delivery_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.where(Order.delivery_date <= datetime.combine(date_to, datetime.max.time()))

    query = query.order_by(Order.created_at.desc()).offset(skip).limit(limit)
    orders = db.exec(query).all()
    return orders


@router.get("/orders/{order_id}")
async def get_order(order_id: int, db: Session = Depends(get_session)):
    """Получить заказ по ID с полной информацией"""
    # Получаем заказ
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Загружаем связанные объекты
    client = db.get(Client, order.client_id) if order.client_id else None
    recipient = db.get(Client, order.recipient_id) if order.recipient_id else None
    executor = db.get(User, order.executor_id) if order.executor_id else None
    courier = db.get(User, order.courier_id) if order.courier_id else None

    # Получаем элементы заказа
    order_items = db.exec(select(OrderItem).where(OrderItem.order_id == order.id)).all()

    # Формируем items с продуктами
    items_with_products = []
    for item in order_items:
        product = db.get(Product, item.product_id) if item.product_id else None
        items_with_products.append({
            "id": item.id,
            "order_id": item.order_id,
            "product_id": item.product_id,
            "quantity": item.quantity,
            "price": item.price,
            "product": product.model_dump() if product else None
        })

    # Собираем полный ответ
    response = {
        "id": order.id,
        "client_id": order.client_id,
        "recipient_id": order.recipient_id,
        "executor_id": order.executor_id,
        "courier_id": order.courier_id,
        "status": order.status,
        "delivery_date": order.delivery_date.isoformat() if order.delivery_date else None,
        "delivery_address": order.delivery_address,
        "delivery_time_range": order.delivery_time_range,
        "total_price": order.total_price,
        "comment": order.comment,
        "notes": order.notes,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        # Вложенные объекты
        "client": client.model_dump() if client else None,
        "recipient": recipient.model_dump() if recipient else None,
        "executor": executor.model_dump() if executor else None,
        "courier": courier.model_dump() if courier else None,
        "order_items": items_with_products
    }

    return response


@router.post("/orders", response_model=Order)
async def create_order(
    order: Order,
    db: Session = Depends(get_session)
):
    """Создать новый заказ"""
    # Проверка клиентов
    client = db.get(Client, order.client_id)
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")

    recipient = db.get(Client, order.recipient_id)
    if not recipient:
        raise HTTPException(status_code=404, detail="Recipient not found")

    db.add(order)
    db.commit()
    db.refresh(order)

    # Добавляем историю
    history = OrderHistory(
        order_id=order.id,
        action="created",
        new_status=order.status,
        comment="Заказ создан"
    )
    db.add(history)
    db.commit()

    return order


@router.put("/orders/{order_id}", response_model=Order)
async def update_order(
    order_id: int,
    order_update: Order,
    db: Session = Depends(get_session)
):
    """Обновить заказ"""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    update_data = order_update.model_dump(exclude_unset=True)

    # Валидация статуса, если он обновляется
    if 'status' in update_data:
        valid_statuses = [s.value for s in OrderStatus]
        if update_data['status'] not in valid_statuses:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid status '{update_data['status']}'. Must be one of: {', '.join(valid_statuses)}"
            )

    for key, value in update_data.items():
        if key != 'id':
            setattr(order, key, value)

    db.add(order)
    db.commit()

    # Если изменился статус, добавляем в историю
    if old_status != order.status:
        history = OrderHistory(
            order_id=order_id,
            action="status_changed",
            old_status=old_status,
            new_status=order.status,
            comment=f"Статус изменен с {old_status} на {order.status}"
        )
        db.add(history)
        db.commit()

    db.refresh(order)
    return order


class StatusUpdateRequest(BaseModel):
    new_status: str
    comment: Optional[str] = None

@router.patch("/orders/{order_id}")
async def patch_order(
    order_id: int,
    order_update: dict,
    db: Session = Depends(get_session)
):
    """Частично обновить заказ"""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    # Конвертируем русские даты в datetime
    if 'delivery_date' in order_update:
        delivery_date_str = order_update['delivery_date']
        if delivery_date_str == "Сегодня":
            order_update['delivery_date'] = datetime.now().replace(hour=12, minute=0, second=0, microsecond=0)
        elif delivery_date_str == "Завтра":
            order_update['delivery_date'] = (datetime.now() + timedelta(days=1)).replace(hour=12, minute=0, second=0, microsecond=0)
        elif delivery_date_str == "Послезавтра":
            order_update['delivery_date'] = (datetime.now() + timedelta(days=2)).replace(hour=12, minute=0, second=0, microsecond=0)

    # Применяем только переданные поля
    for key, value in order_update.items():
        if key != 'id' and hasattr(order, key):
            setattr(order, key, value)

    db.add(order)
    db.commit()
    db.refresh(order)

    # Если изменился статус, добавляем в историю
    if 'status' in order_update:
        history = OrderHistory(
            order_id=order_id,
            action="status_changed",
            new_status=order_update['status'],
            comment=f"Статус изменен на {order_update['status']}"
        )
        db.add(history)
        db.commit()

    return order


@router.put("/orders/{order_id}/status")
async def update_order_status(
    order_id: int,
    status_update: StatusUpdateRequest,
    db: Session = Depends(get_session)
):
    """Обновить статус заказа"""
    print(f"🔧 DEBUG: Received status update request for order {order_id}")
    print(f"🔧 DEBUG: Status update data: {status_update}")
    print(f"🔧 DEBUG: Status update new_status: {status_update.new_status}")

    # Используем статус напрямую из SQLModel enum
    status = status_update.new_status

    # Валидация статуса
    valid_statuses = [s.value for s in OrderStatus]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status '{status}'. Must be one of: {', '.join(valid_statuses)}"
        )

    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    old_status = order.status
    order.status = status

    db.add(order)

    # Добавляем запись в историю
    history = OrderHistory(
        order_id=order_id,
        action="status_changed",
        old_status=old_status,
        new_status=status,
        comment=status_update.comment or f"Статус изменен с {old_status} на {status}"
    )
    db.add(history)
    db.commit()
    db.refresh(order)

    return {"message": "Status updated", "order": order}


@router.delete("/orders/{order_id}")
async def delete_order(order_id: int, db: Session = Depends(get_session)):
    """Удалить заказ"""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    db.delete(order)
    db.commit()
    return {"message": "Order deleted successfully"}


# ============= ORDER ITEMS API =============

@router.post("/orders/{order_id}/items", response_model=OrderItem)
async def add_order_item(
    order_id: int,
    item: OrderItem,
    db: Session = Depends(get_session)
):
    """Добавить позицию в заказ"""
    order = db.get(Order, order_id)
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")

    product = db.get(Product, item.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    item.order_id = order_id
    item.price = item.price or product.price

    db.add(item)
    db.commit()

    # Обновляем общую сумму заказа
    total = db.exec(
        select(func.sum(OrderItem.price * OrderItem.quantity))
        .where(OrderItem.order_id == order_id)
    ).one()

    order.total_price = total or 0
    db.add(order)
    db.commit()

    db.refresh(item)
    return item


@router.delete("/orders/{order_id}/items/{item_id}")
async def delete_order_item(
    order_id: int,
    item_id: int,
    db: Session = Depends(get_session)
):
    """Удалить позицию из заказа"""
    item = db.exec(
        select(OrderItem)
        .where(OrderItem.id == item_id, OrderItem.order_id == order_id)
    ).first()

    if not item:
        raise HTTPException(status_code=404, detail="Order item not found")

    db.delete(item)
    db.commit()

    # Обновляем общую сумму заказа
    order = db.get(Order, order_id)
    total = db.exec(
        select(func.sum(OrderItem.price * OrderItem.quantity))
        .where(OrderItem.order_id == order_id)
    ).one()

    order.total_price = total or 0
    db.add(order)
    db.commit()

    return {"message": "Order item deleted successfully"}


# ============= STATISTICS API =============

@router.get("/stats/dashboard")
async def get_dashboard_stats(db: Session = Depends(get_session)):
    """Получить статистику для дашборда"""
    today = datetime.now().date()

    # Общее количество заказов
    total_orders = db.exec(select(func.count()).select_from(Order)).one()

    # Заказы за сегодня
    today_orders = db.exec(
        select(func.count()).select_from(Order)
        .where(func.date(Order.created_at) == today)
    ).one()

    # Общее количество клиентов
    total_clients = db.exec(select(func.count()).select_from(Client)).one()

    # Общее количество продуктов
    total_products = db.exec(select(func.count()).select_from(Product)).one()

    # Статистика по статусам
    status_stats = db.exec(
        select(Order.status, func.count())
        .select_from(Order)
        .group_by(Order.status)
    ).all()

    return {
        "total_orders": total_orders,
        "today_orders": today_orders,
        "total_clients": total_clients,
        "total_products": total_products,
        "orders_by_status": {status: count for status, count in status_stats},
        "low_stock_items": db.exec(
            select(func.count()).select_from(Inventory)
            .where(
                (Inventory.min_quantity.isnot(None)) &
                (Inventory.quantity <= Inventory.min_quantity)
            )
        ).one()
    }


@router.get("/stats/sales")
async def get_sales_stats(
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    db: Session = Depends(get_session)
):
    """Получить статистику продаж"""
    query = select(
        func.date(Order.delivery_date).label("date"),
        func.count(Order.id).label("orders_count"),
        func.sum(Order.total_price).label("total_revenue")
    ).select_from(Order).where(Order.status != OrderStatus.CANCELED)

    if date_from:
        query = query.where(Order.delivery_date >= datetime.combine(date_from, datetime.min.time()))

    if date_to:
        query = query.where(Order.delivery_date <= datetime.combine(date_to, datetime.max.time()))

    query = query.group_by(func.date(Order.delivery_date)).order_by("date")
    sales_data = db.exec(query).all()

    return [
        {
            "date": row[0],
            "orders_count": row[1],
            "total_revenue": row[2] or 0
        }
        for row in sales_data
    ]


# ============= PROFILE API =============

@router.get("/profile/me", response_model=User)
async def get_my_profile(
    db: Session = Depends(get_session)
):
    """Получить профиль текущего пользователя (TEST VERSION - NO AUTH)"""
    # For testing - return first user or create a test user
    user = db.exec(select(User)).first()
    if not user:
        from datetime import datetime
        test_user = User(
            name="Анна Иванова",
            email="anna@example.com",
            phone="+7 (777) 123-45-67",
            position=UserPosition.DIRECTOR,
            bio="Профессиональный флорист с многолетним опытом. Специализируюсь на создании свадебных композиций и эксклюзивных букетов.",
            isActive=True,
            joinedDate=datetime.utcnow(),
            hashed_password="test"
        )
        db.add(test_user)
        db.commit()
        db.refresh(test_user)
        return test_user
    return user


@router.put("/profile/me", response_model=User)
async def update_my_profile(
    profile_data: dict,
    db: Session = Depends(get_session)
):
    """Обновить профиль текущего пользователя (TEST VERSION - NO AUTH)"""
    # For testing - update first user
    user = db.exec(select(User)).first()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    # Обновляем разрешенные поля
    allowed_fields = {"name", "phone", "position", "bio"}
    for field, value in profile_data.items():
        if field in allowed_fields and hasattr(user, field):
            setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/colleagues", response_model=List[User])
async def get_colleagues(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_session)
):
    """Получить список коллег (TEST VERSION - NO AUTH)"""
    # For testing - create some test colleagues if none exist
    colleagues = db.exec(select(User)).all()

    if len(colleagues) <= 1:  # Only main user exists
        from datetime import datetime
        test_colleagues = [
            User(
                name="Мария Петрова",
                email="maria@example.com",
                phone="+7 (777) 234-56-78",
                position=UserPosition.MANAGER,
                isActive=True,
                joinedDate=datetime(2023, 2, 15),
                hashed_password="test"
            ),
            User(
                name="Елена Козлова",
                email="elena@example.com",
                phone="+7 (777) 345-67-89",
                position=UserPosition.SELLER,
                isActive=True,
                joinedDate=datetime(2023, 6, 20),
                hashed_password="test"
            ),
            User(
                name="Дария Сидорова",
                email="daria@example.com",
                phone="+7 (777) 456-78-90",
                position=UserPosition.COURIER,
                isActive=False,
                joinedDate=datetime(2024, 3, 10),
                hashed_password="test"
            )
        ]
        for colleague in test_colleagues:
            db.add(colleague)
        db.commit()
        for colleague in test_colleagues:
            db.refresh(colleague)

    # Return all users except first one (simulating current user)
    query = select(User).offset(skip).limit(limit)
    all_users = db.exec(query).all()
    return all_users[1:] if len(all_users) > 1 else []


@router.post("/colleagues", response_model=User)
async def create_colleague(
    colleague_data: dict,
    db: Session = Depends(get_session)
):
    """Добавить нового коллегу"""
    try:
        # Создаем нового пользователя
        new_colleague = User(
            name=colleague_data.get("name"),
            email=colleague_data.get("email", f"{colleague_data.get('name', 'user').lower().replace(' ', '.')}@example.com"),
            phone=colleague_data.get("phone"),
            position=UserPosition(colleague_data.get("position", "seller")),
            isActive=colleague_data.get("isActive", True),
            joinedDate=datetime.now(),
            hashed_password="temp_password"  # Временный пароль
        )

        db.add(new_colleague)
        db.commit()
        db.refresh(new_colleague)

        return new_colleague

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка создания коллеги: {str(e)}")


@router.put("/colleagues/{colleague_id}", response_model=User)
async def update_colleague(
    colleague_id: int,
    colleague_data: dict,
    db: Session = Depends(get_session)
):
    """Обновить информацию о коллеге"""
    colleague = db.get(User, colleague_id)
    if not colleague:
        raise HTTPException(status_code=404, detail="Коллега не найден")

    try:
        # Обновляем поля
        for field, value in colleague_data.items():
            if hasattr(colleague, field) and field != "id":
                if field == "position" and isinstance(value, str):
                    setattr(colleague, field, UserPosition(value))
                else:
                    setattr(colleague, field, value)

        db.commit()
        db.refresh(colleague)

        return colleague

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка обновления коллеги: {str(e)}")


@router.delete("/colleagues/{colleague_id}")
async def delete_colleague(
    colleague_id: int,
    db: Session = Depends(get_session)
):
    """Удалить коллегу"""
    colleague = db.get(User, colleague_id)
    if not colleague:
        raise HTTPException(status_code=404, detail="Коллега не найден")

    try:
        db.delete(colleague)
        db.commit()
        return {"message": "Коллега успешно удален"}

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка удаления коллеги: {str(e)}")


# ============= SHOP API =============

@router.get("/shop", response_model=Shop)
async def get_shop_info(db: Session = Depends(get_session)):
    """Получить информацию о магазине"""
    shop = db.exec(select(Shop)).first()
    if not shop:
        # Если магазина нет, создаем дефолтный
        shop = Shop(
            name="Цветочная мастерская",
            address="г. Алматы",
            phone="+7 (727) 123-45-67",
            workingHours="Пн-Вс: 09:00 - 21:00",
            description=""
        )
        db.add(shop)
        db.commit()
        db.refresh(shop)
    return shop


@router.put("/shop", response_model=Shop)
async def update_shop_info(
    shop_data: dict,
    db: Session = Depends(get_session)
):
    """Обновить информацию о магазине"""
    shop = db.exec(select(Shop)).first()
    if not shop:
        # Создаем новую запись если её нет
        shop = Shop(**shop_data)
        db.add(shop)
    else:
        # Обновляем существующую
        for field, value in shop_data.items():
            if hasattr(shop, field):
                setattr(shop, field, value)
        db.add(shop)

    db.commit()
    db.refresh(shop)
    return shop


# ============= USERS API =============

@router.get("/users")
async def get_users(
    position: Optional[str] = None,
    city: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_session)
):
    """Получить список пользователей для фронтенда"""
    query = select(User)

    if position:
        # Преобразуем фронтенд позиции в бэкенд энумы
        position_map = {
            'Флорист': ['director', 'manager', 'seller'],  # Флористы - это директор, менеджер, продавец
            'Курьер': ['courier']  # Курьеры
        }
        if position in position_map:
            query = query.where(User.position.in_(position_map[position]))

    query = query.offset(skip).limit(limit)
    users = db.exec(query).all()

    # Преобразуем в формат, ожидаемый фронтендом
    def map_position_to_frontend(position: UserPosition) -> str:
        position_map = {
            UserPosition.DIRECTOR: 'Флорист',
            UserPosition.MANAGER: 'Флорист',
            UserPosition.SELLER: 'Флорист',
            UserPosition.COURIER: 'Курьер'
        }
        return position_map.get(position, 'Флорист')

    frontend_users = [
        {
            "id": user.id,
            "username": user.name,  # Маппим name -> username для фронтенда
            "position": map_position_to_frontend(user.position),
            "email": user.email,
            "phone": user.phone,
            "isActive": user.isActive
        }
        for user in users
    ]

    return {"users": frontend_users}


# ============= INVENTORY AUDIT API =============

@router.post("/inventory/audit/start")
async def start_inventory_audit(db: Session = Depends(get_session)):
    """Начать новую инвентаризацию"""
    from models_sqlmodel import InventoryAudit, InventoryAuditItem, Inventory

    # Создаем новую инвентаризацию
    audit = InventoryAudit(
        status="in_progress",
        created_by_id=1  # TODO: получить из текущего пользователя
    )
    db.add(audit)
    db.commit()
    db.refresh(audit)

    # Получаем все позиции склада
    inventory_items = db.exec(select(Inventory)).all()

    # Создаем позиции для инвентаризации
    for item in inventory_items:
        audit_item = InventoryAuditItem(
            audit_id=audit.id,
            inventory_id=item.id,
            system_quantity=item.quantity,
            actual_quantity=None,
            difference=None
        )
        db.add(audit_item)

    db.commit()

    # Возвращаем инвентаризацию с позициями
    db.refresh(audit)
    audit_data = {
        "id": audit.id,
        "status": audit.status,
        "created_at": audit.created_at.isoformat(),
        "items": []
    }

    # Загружаем позиции с информацией о товарах
    audit_items = db.exec(
        select(InventoryAuditItem)
        .where(InventoryAuditItem.audit_id == audit.id)
    ).all()

    for audit_item in audit_items:
        inv_item = db.get(Inventory, audit_item.inventory_id)
        audit_data["items"].append({
            "id": audit_item.id,
            "inventory_id": audit_item.inventory_id,
            "name": inv_item.name,
            "unit": inv_item.unit,
            "system_quantity": audit_item.system_quantity,
            "actual_quantity": audit_item.actual_quantity,
            "difference": audit_item.difference,
            "category": "flowers" if "роз" in inv_item.name.lower() or "тюльпан" in inv_item.name.lower() else
                       "greenery" if "эвкалипт" in inv_item.name.lower() else "accessories"
        })

    return audit_data


@router.get("/inventory/audit/current")
async def get_current_audit(db: Session = Depends(get_session)):
    """Получить текущую инвентаризацию"""
    from models_sqlmodel import InventoryAudit, InventoryAuditItem, Inventory

    # Ищем незавершенную инвентаризацию
    audit = db.exec(
        select(InventoryAudit)
        .where(InventoryAudit.status == "in_progress")
        .order_by(InventoryAudit.created_at.desc())
    ).first()

    if not audit:
        return None

    # Загружаем позиции
    audit_items = db.exec(
        select(InventoryAuditItem)
        .where(InventoryAuditItem.audit_id == audit.id)
    ).all()

    items_data = []
    for audit_item in audit_items:
        inv_item = db.get(Inventory, audit_item.inventory_id)
        items_data.append({
            "id": audit_item.id,
            "inventory_id": audit_item.inventory_id,
            "name": inv_item.name,
            "unit": inv_item.unit,
            "system_quantity": audit_item.system_quantity,
            "actual_quantity": audit_item.actual_quantity,
            "difference": audit_item.difference,
            "category": "flowers" if any(flower in inv_item.name.lower() for flower in ["роз", "тюльпан", "лил", "хризантем", "гипсофил"]) else
                       "greenery" if "эвкалипт" in inv_item.name.lower() else "accessories"
        })

    return {
        "id": audit.id,
        "status": audit.status,
        "created_at": audit.created_at.isoformat(),
        "items": items_data
    }


@router.post("/inventory/audit/{audit_id}/items")
async def save_audit_items(
    audit_id: int,
    items: list[dict],
    db: Session = Depends(get_session)
):
    """Сохранить результаты подсчета"""
    from models_sqlmodel import InventoryAudit, InventoryAuditItem

    audit = db.get(InventoryAudit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    if audit.status != "in_progress":
        raise HTTPException(status_code=400, detail="Audit is not in progress")

    # Обновляем позиции
    for item_data in items:
        audit_item = db.exec(
            select(InventoryAuditItem)
            .where(InventoryAuditItem.audit_id == audit_id)
            .where(InventoryAuditItem.inventory_id == item_data["inventory_id"])
        ).first()

        if audit_item and item_data.get("actual_quantity") is not None:
            audit_item.actual_quantity = item_data["actual_quantity"]
            audit_item.difference = item_data["actual_quantity"] - audit_item.system_quantity
            db.add(audit_item)

    db.commit()

    return {"message": "Items updated successfully"}


@router.post("/inventory/audit/{audit_id}/complete")
async def complete_audit(audit_id: int, db: Session = Depends(get_session)):
    """Завершить инвентаризацию и применить корректировки"""
    from models_sqlmodel import InventoryAudit, InventoryAuditItem, Inventory
    from datetime import datetime

    audit = db.get(InventoryAudit, audit_id)
    if not audit:
        raise HTTPException(status_code=404, detail="Audit not found")

    if audit.status != "in_progress":
        raise HTTPException(status_code=400, detail="Audit is not in progress")

    # Получаем все позиции с расхождениями
    audit_items = db.exec(
        select(InventoryAuditItem)
        .where(InventoryAuditItem.audit_id == audit_id)
        .where(InventoryAuditItem.actual_quantity != None)
        .where(InventoryAuditItem.difference != 0)
    ).all()

    # Применяем корректировки и создаем записи в истории
    from models_sqlmodel import InventoryTransaction, TransactionType

    for audit_item in audit_items:
        inventory = db.get(Inventory, audit_item.inventory_id)
        if inventory and audit_item.actual_quantity is not None:
            # Создаем запись в истории операций
            transaction = InventoryTransaction(
                inventory_id=audit_item.inventory_id,
                transaction_type=TransactionType.AUDIT,
                quantity=audit_item.difference,  # Разница (может быть отрицательной)
                comment=f"Корректировка по инвентаризации: {audit_item.system_quantity} → {audit_item.actual_quantity} {inventory.unit}",
                reference_type="audit",
                reference_id=audit_id,
                created_by_id=1  # TODO: получить из текущего пользователя
            )
            db.add(transaction)

            # Обновляем количество
            inventory.quantity = audit_item.actual_quantity
            db.add(inventory)

    # Завершаем инвентаризацию
    audit.status = "completed"
    audit.completed_at = datetime.utcnow()
    db.add(audit)

    db.commit()

    return {
        "message": "Audit completed successfully",
        "adjustments_count": len(audit_items)
    }


# ============= INVENTORY TRANSACTIONS API =============

@router.get("/inventory/{item_id}/transactions")
async def get_inventory_transactions(
    item_id: int,
    db: Session = Depends(get_session)
):
    """Получить историю операций по товару"""
    from models_sqlmodel import InventoryTransaction, Inventory

    # Проверяем существование товара
    inventory = db.get(Inventory, item_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    # Получаем транзакции
    transactions = db.exec(
        select(InventoryTransaction)
        .where(InventoryTransaction.inventory_id == item_id)
        .order_by(InventoryTransaction.created_at.desc())
    ).all()

    # Форматируем для фронтенда
    return [{
        "id": t.id,
        "type": t.transaction_type,
        "quantity": t.quantity,
        "comment": t.comment,
        "date": t.created_at.isoformat(),
        "referenceType": t.reference_type,
        "referenceId": t.reference_id
    } for t in transactions]


@router.post("/inventory/{item_id}/write-off")
async def write_off_inventory(
    item_id: int,
    quantity: float = Body(...),
    comment: str = Body(...),
    db: Session = Depends(get_session)
):
    """Списать товар со склада"""
    from models_sqlmodel import InventoryTransaction, Inventory, TransactionType

    # Проверяем товар
    inventory = db.get(Inventory, item_id)
    if not inventory:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if quantity > inventory.quantity:
        raise HTTPException(status_code=400, detail="Insufficient quantity")

    # Создаем транзакцию списания
    transaction = InventoryTransaction(
        inventory_id=item_id,
        transaction_type=TransactionType.WASTE,
        quantity=-quantity,  # Отрицательное значение для списания
        comment=comment,
        reference_type="manual",
        created_by_id=1  # TODO: из авторизации
    )

    # Обновляем остаток
    inventory.quantity -= quantity

    db.add(transaction)
    db.add(inventory)
    db.commit()
    db.refresh(transaction)

    return {
        "message": "Write-off successful",
        "new_quantity": inventory.quantity,
        "transaction_id": transaction.id
    }