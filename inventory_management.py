"""
Inventory Management System - связь товаров со складом
Управление составом букетов и автоматическое списание со склада
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from datetime import datetime

from database import get_db, Inventory
from product_enhancements import ProductComposition, ProductEnhanced

router = APIRouter()

# Pydantic models

class InventoryItemCreate(BaseModel):
    name: str  # "Роза красная", "Эустома белая", "Крафт-бумага"
    quantity: float
    unit: str  # "шт", "м", "упак"
    min_quantity: float = 0
    price_per_unit: Optional[float] = None

class InventoryUpdate(BaseModel):
    name: Optional[str] = None
    quantity: Optional[float] = None
    min_quantity: Optional[float] = None
    price_per_unit: Optional[float] = None

class ProductCompositionSet(BaseModel):
    inventory_id: int
    quantity_needed: float
    unit: Optional[str] = None
    is_optional: bool = False
    notes: Optional[str] = None

class InventoryStatus(BaseModel):
    id: int
    name: str
    current_quantity: float
    min_quantity: float
    unit: str
    is_low_stock: bool
    price_per_unit: Optional[float]

class ProductAvailability(BaseModel):
    product_id: int
    product_name: str
    can_make: int  # Сколько букетов можно сделать
    limiting_material: Optional[str]  # Какой материал ограничивает
    materials_status: List[dict]

# Inventory endpoints

@router.post("/inventory/items")
def create_inventory_item(item: InventoryItemCreate, db: Session = Depends(get_db)):
    """Добавить новый материал/цветок на склад"""
    db_item = Inventory(**item.dict())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return {"message": "Inventory item created", "id": db_item.id}

@router.get("/inventory/items", response_model=List[InventoryStatus])
def get_inventory_items(
    only_low_stock: bool = False,
    db: Session = Depends(get_db)
):
    """Получить список всех материалов на складе"""
    query = db.query(Inventory)

    items = query.all()
    result = []

    for item in items:
        is_low = item.quantity <= (item.min_quantity or 0)
        if only_low_stock and not is_low:
            continue

        result.append(InventoryStatus(
            id=item.id,
            name=item.name,
            current_quantity=item.quantity,
            min_quantity=item.min_quantity or 0,
            unit=item.unit,
            is_low_stock=is_low,
            price_per_unit=item.price_per_unit
        ))

    return result

@router.put("/inventory/items/{item_id}/update")
def update_inventory_item(
    item_id: int,
    update_data: InventoryUpdate,
    db: Session = Depends(get_db)
):
    """Обновить количество или параметры материала"""
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    if update_data.name is not None:
        item.name = update_data.name
    if update_data.quantity is not None:
        item.quantity = update_data.quantity
    if update_data.min_quantity is not None:
        item.min_quantity = update_data.min_quantity
    if update_data.price_per_unit is not None:
        item.price_per_unit = update_data.price_per_unit

    db.commit()
    return {"message": "Inventory updated"}

@router.patch("/inventory/items/{item_id}")
def partial_update_inventory_item(
    item_id: int,
    update_data: InventoryUpdate,
    db: Session = Depends(get_db)
):
    """Частичное обновление материала (PATCH метод)"""
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    updated_fields = []
    if update_data.name is not None:
        item.name = update_data.name
        updated_fields.append("name")
    if update_data.quantity is not None:
        item.quantity = update_data.quantity
        updated_fields.append("quantity")
    if update_data.min_quantity is not None:
        item.min_quantity = update_data.min_quantity
        updated_fields.append("min_quantity")
    if update_data.price_per_unit is not None:
        item.price_per_unit = update_data.price_per_unit
        updated_fields.append("price_per_unit")

    if not updated_fields:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    db.commit()
    return {
        "message": "Inventory item partially updated",
        "updated_fields": updated_fields,
        "item_id": item_id
    }

@router.post("/inventory/items/{item_id}/add-stock")
def add_stock(
    item_id: int,
    quantity: float,
    db: Session = Depends(get_db)
):
    """Добавить поступление на склад"""
    item = db.query(Inventory).filter(Inventory.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Inventory item not found")

    item.quantity += quantity
    db.commit()

    return {
        "message": f"Added {quantity} {item.unit} to {item.name}",
        "new_quantity": item.quantity
    }

# Product composition management

@router.post("/products/{product_id}/composition")
def set_product_composition(
    product_id: int,
    materials: List[ProductCompositionSet],
    db: Session = Depends(get_db)
):
    """Установить состав продукта (какие цветы/материалы нужны)"""

    # Проверяем существование продукта
    product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Удаляем старый состав
    db.query(ProductComposition).filter(
        ProductComposition.product_id == product_id
    ).delete()

    # Добавляем новый состав
    for material in materials:
        # Проверяем существование материала на складе
        inv_item = db.query(Inventory).filter(Inventory.id == material.inventory_id).first()
        if not inv_item:
            raise HTTPException(
                status_code=404,
                detail=f"Inventory item {material.inventory_id} not found"
            )

        composition = ProductComposition(
            product_id=product_id,
            inventory_id=material.inventory_id,
            quantity_needed=material.quantity_needed,
            unit=material.unit or inv_item.unit,
            is_optional=material.is_optional,
            notes=material.notes
        )
        db.add(composition)

    db.commit()
    return {"message": "Product composition updated"}

@router.get("/products/{product_id}/composition")
def get_product_composition(product_id: int, db: Session = Depends(get_db)):
    """Получить состав продукта"""

    compositions = db.query(ProductComposition).filter(
        ProductComposition.product_id == product_id
    ).all()

    result = []
    for comp in compositions:
        inv_item = comp.inventory_item
        result.append({
            "inventory_id": comp.inventory_id,
            "material_name": inv_item.name,
            "quantity_needed": comp.quantity_needed,
            "unit": comp.unit or inv_item.unit,
            "is_optional": comp.is_optional,
            "notes": comp.notes,
            "current_stock": inv_item.quantity,
            "cost": (comp.quantity_needed * inv_item.price_per_unit) if inv_item.price_per_unit else None
        })

    return result

@router.get("/products/{product_id}/availability")
def check_product_availability(
    product_id: int,
    quantity_requested: int = 1,
    db: Session = Depends(get_db)
):
    """Проверить, можно ли сделать продукт из имеющихся материалов"""

    product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    compositions = db.query(ProductComposition).filter(
        and_(
            ProductComposition.product_id == product_id,
            ProductComposition.is_optional == False  # Только обязательные материалы
        )
    ).all()

    if not compositions:
        return {
            "product_id": product_id,
            "product_name": product.name,
            "can_make": 999,  # Если нет состава, считаем неограниченным
            "limiting_material": None,
            "materials_status": []
        }

    materials_status = []
    min_possible = float('inf')
    limiting_material = None

    for comp in compositions:
        inv_item = comp.inventory_item
        can_make_from_this = int(inv_item.quantity / comp.quantity_needed)

        materials_status.append({
            "material": inv_item.name,
            "needed_per_unit": comp.quantity_needed,
            "available": inv_item.quantity,
            "unit": comp.unit or inv_item.unit,
            "can_make": can_make_from_this,
            "is_limiting": can_make_from_this < quantity_requested
        })

        if can_make_from_this < min_possible:
            min_possible = can_make_from_this
            limiting_material = inv_item.name

    return ProductAvailability(
        product_id=product_id,
        product_name=product.name,
        can_make=min_possible,
        limiting_material=limiting_material if min_possible < quantity_requested else None,
        materials_status=materials_status
    )

@router.post("/products/{product_id}/deduct-materials")
def deduct_materials_for_product(
    product_id: int,
    quantity: int = 1,
    force: bool = False,
    db: Session = Depends(get_db)
):
    """Списать материалы со склада для производства продукта"""

    # Сначала проверяем доступность
    if not force:
        availability = check_product_availability(product_id, quantity, db)
        if availability.can_make < quantity:
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно материалов. Можно сделать только {availability.can_make} шт. Ограничивает: {availability.limiting_material}"
            )

    # Списываем материалы
    compositions = db.query(ProductComposition).filter(
        ProductComposition.product_id == product_id
    ).all()

    deducted = []
    for comp in compositions:
        if comp.is_optional:
            continue

        inv_item = comp.inventory_item
        amount_to_deduct = comp.quantity_needed * quantity

        if not force and inv_item.quantity < amount_to_deduct:
            db.rollback()
            raise HTTPException(
                status_code=400,
                detail=f"Недостаточно {inv_item.name}: нужно {amount_to_deduct} {inv_item.unit}, есть {inv_item.quantity}"
            )

        inv_item.quantity -= amount_to_deduct
        deducted.append({
            "material": inv_item.name,
            "deducted": amount_to_deduct,
            "unit": inv_item.unit,
            "remaining": inv_item.quantity
        })

    db.commit()

    return {
        "message": f"Materials deducted for {quantity} units of product",
        "deducted_materials": deducted
    }

# Initialize sample inventory
@router.post("/inventory/initialize-samples")
def initialize_sample_inventory(db: Session = Depends(get_db)):
    """Создать примеры материалов на складе"""

    # Проверяем, есть ли уже материалы
    existing = db.query(Inventory).count()
    if existing > 0:
        return {"message": "Inventory already has items", "count": existing}

    # Цветы
    flowers = [
        {"name": "Роза красная", "quantity": 100, "unit": "шт", "min_quantity": 20, "price_per_unit": 300},
        {"name": "Роза розовая", "quantity": 80, "unit": "шт", "min_quantity": 20, "price_per_unit": 300},
        {"name": "Роза белая", "quantity": 60, "unit": "шт", "min_quantity": 15, "price_per_unit": 320},
        {"name": "Эустома белая", "quantity": 40, "unit": "шт", "min_quantity": 10, "price_per_unit": 250},
        {"name": "Эустома розовая", "quantity": 35, "unit": "шт", "min_quantity": 10, "price_per_unit": 250},
        {"name": "Хризантема белая", "quantity": 50, "unit": "шт", "min_quantity": 15, "price_per_unit": 200},
        {"name": "Гербера красная", "quantity": 30, "unit": "шт", "min_quantity": 10, "price_per_unit": 280},
        {"name": "Тюльпан", "quantity": 0, "unit": "шт", "min_quantity": 30, "price_per_unit": 150},  # Сезонный
        {"name": "Пион", "quantity": 0, "unit": "шт", "min_quantity": 20, "price_per_unit": 500},  # Сезонный
        {"name": "Гипсофила", "quantity": 20, "unit": "веток", "min_quantity": 10, "price_per_unit": 150},
        {"name": "Эвкалипт", "quantity": 25, "unit": "веток", "min_quantity": 10, "price_per_unit": 180},
        {"name": "Рускус", "quantity": 30, "unit": "веток", "min_quantity": 10, "price_per_unit": 120},
    ]

    # Упаковка и декор
    packaging = [
        {"name": "Крафт-бумага", "quantity": 50, "unit": "м", "min_quantity": 10, "price_per_unit": 200},
        {"name": "Пленка прозрачная", "quantity": 30, "unit": "м", "min_quantity": 10, "price_per_unit": 150},
        {"name": "Лента атласная", "quantity": 100, "unit": "м", "min_quantity": 20, "price_per_unit": 50},
        {"name": "Коробка малая", "quantity": 15, "unit": "шт", "min_quantity": 5, "price_per_unit": 500},
        {"name": "Коробка средняя", "quantity": 10, "unit": "шт", "min_quantity": 5, "price_per_unit": 700},
        {"name": "Коробка большая", "quantity": 5, "unit": "шт", "min_quantity": 3, "price_per_unit": 1000},
        {"name": "Оазис (флористическая губка)", "quantity": 20, "unit": "шт", "min_quantity": 5, "price_per_unit": 300},
        {"name": "Корзина плетеная малая", "quantity": 8, "unit": "шт", "min_quantity": 3, "price_per_unit": 1500},
        {"name": "Корзина плетеная большая", "quantity": 5, "unit": "шт", "min_quantity": 2, "price_per_unit": 2500},
    ]

    # Добавляем все в базу
    for item_data in flowers + packaging:
        item = Inventory(**item_data)
        db.add(item)

    db.commit()

    # Теперь создаем состав для примера продукта
    product = db.query(ProductEnhanced).filter(ProductEnhanced.sku == "BUQ-001").first()
    if product:
        # Состав букета "Нежность"
        rosa_pink = db.query(Inventory).filter(Inventory.name == "Роза розовая").first()
        eustoma = db.query(Inventory).filter(Inventory.name == "Эустома белая").first()
        eucalyptus = db.query(Inventory).filter(Inventory.name == "Эвкалипт").first()
        kraft = db.query(Inventory).filter(Inventory.name == "Крафт-бумага").first()
        ribbon = db.query(Inventory).filter(Inventory.name == "Лента атласная").first()

        if all([rosa_pink, eustoma, eucalyptus, kraft, ribbon]):
            compositions = [
                ProductComposition(product_id=product.id, inventory_id=rosa_pink.id, quantity_needed=15, is_optional=False),
                ProductComposition(product_id=product.id, inventory_id=eustoma.id, quantity_needed=10, is_optional=False),
                ProductComposition(product_id=product.id, inventory_id=eucalyptus.id, quantity_needed=3, is_optional=False),
                ProductComposition(product_id=product.id, inventory_id=kraft.id, quantity_needed=0.5, is_optional=False),
                ProductComposition(product_id=product.id, inventory_id=ribbon.id, quantity_needed=0.3, is_optional=False),
            ]
            for comp in compositions:
                db.add(comp)
            db.commit()

    return {
        "message": "Sample inventory created",
        "flowers_count": len(flowers),
        "packaging_count": len(packaging)
    }