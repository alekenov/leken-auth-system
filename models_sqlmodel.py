"""
SQLModel Models for CRM Florist System
Миграция с SQLAlchemy на SQLModel для упрощения кода
"""
from typing import Optional, List
from datetime import datetime
from sqlmodel import Field, SQLModel, Relationship, Session, create_engine, select
from enum import Enum


# Enums
class ClientType(str, Enum):
    CUSTOMER = "заказчик"
    RECIPIENT = "получатель"
    BOTH = "оба"


class OrderStatus(str, Enum):
    NEW = "NEW"
    IN_WORK = "IN_WORK"
    READY = "READY"
    DELIVERED = "DELIVERED"
    PAID = "PAID"
    COLLECTED = "COLLECTED"
    CANCELED = "CANCELED"


class ProductCategory(str, Enum):
    BOUQUET = "букет"
    COMPOSITION = "композиция"
    POTTED = "горшечный"


class UserPosition(str, Enum):
    DIRECTOR = "director"
    MANAGER = "manager"
    SELLER = "seller"
    COURIER = "courier"


# Base Models
class User(SQLModel, table=True):
    """Модель пользователя системы (флорист/сотрудник)"""
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)  # Изменено с username на name для frontend
    email: str = Field(unique=True, index=True)
    hashed_password: str
    joinedDate: datetime = Field(default_factory=datetime.utcnow)  # Изменено с created_at

    # Profile fields для FloristProfile
    phone: Optional[str] = None
    position: UserPosition = Field(default=UserPosition.SELLER)  # Enum вместо строки
    bio: Optional[str] = None  # Добавлено для профиля
    isActive: bool = Field(default=True)  # Добавлено для Colleague

    # Убрано: city, address (будут в Shop модели)

    # Relationships
    executed_orders: List["Order"] = Relationship(
        back_populates="executor",
        sa_relationship_kwargs={"foreign_keys": "[Order.executor_id]"}
    )


class Client(SQLModel, table=True):
    """Модель клиента (заказчик/получатель)"""
    __tablename__ = "clients"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: Optional[str] = None  # Имя опционально
    phone: str = Field(index=True)  # +7XXXXXXXXXX format
    email: Optional[str] = None
    address: Optional[str] = None
    client_type: ClientType = Field(default=ClientType.BOTH)
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships - using string annotations for forward references
    orders_as_client: List["Order"] = Relationship(
        back_populates="client",
        sa_relationship_kwargs={
            "foreign_keys": "Order.client_id",
            "overlaps": "orders_as_recipient,recipient"
        }
    )
    orders_as_recipient: List["Order"] = Relationship(
        back_populates="recipient",
        sa_relationship_kwargs={
            "foreign_keys": "Order.recipient_id",
            "overlaps": "orders_as_client,client"
        }
    )


class Product(SQLModel, table=True):
    """Модель товара/продукта"""
    __tablename__ = "products"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    description: Optional[str] = None
    price: float
    category: ProductCategory
    preparation_time: Optional[int] = None  # в минутах
    image_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # НОВЫЕ поля для соответствия Frontend
    is_available: bool = Field(default=True)  # Флаг доступности товара
    product_type: str = Field(default="catalog")  # "catalog" | "custom"
    images: Optional[str] = None  # JSON массив URL дополнительных изображений
    production_time: Optional[str] = None  # Время производства (например: "2-3 дня")
    width: Optional[str] = None  # Ширина букета (например: "30 см")
    height: Optional[str] = None  # Высота букета (например: "40 см")
    colors: Optional[str] = None  # JSON массив доступных цветов
    catalog_width: Optional[str] = None  # Ширина в каталоге
    catalog_height: Optional[str] = None  # Высота в каталоге
    ingredients: Optional[str] = None  # JSON массив состава/ингредиентов

    # Relationships
    order_items: List["OrderItem"] = Relationship(back_populates="product")
    product_inventories: List["ProductInventory"] = Relationship(back_populates="product")

    class Config:
        # Включаем все поля в JSON-ответ
        json_schema_extra = {
            "example": {
                "name": "Букет роз",
                "description": "Красивый букет роз",
                "price": 15000,
                "category": "букет",
                "is_available": True,
                "product_type": "catalog",
                "colors": '["красный", "белый", "розовый"]'
            }
        }


class Inventory(SQLModel, table=True):
    """Модель складского учета"""
    __tablename__ = "inventory"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    quantity: float
    unit: str  # 'шт', 'м', 'кг'
    min_quantity: Optional[float] = None  # для предупреждений о низком запасе
    price_per_unit: Optional[float] = None  # розничная цена за единицу
    cost_price: Optional[float] = None  # себестоимость за единицу
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    product_inventories: List["ProductInventory"] = Relationship(back_populates="inventory")


class Order(SQLModel, table=True):
    """Модель заказа"""
    __tablename__ = "orders"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_id: int = Field(foreign_key="clients.id")
    recipient_id: int = Field(foreign_key="clients.id")
    executor_id: Optional[int] = Field(default=None, foreign_key="users.id")
    courier_id: Optional[int] = Field(default=None, foreign_key="users.id")
    status: OrderStatus = Field(default=OrderStatus.NEW)
    delivery_date: datetime
    delivery_address: str
    delivery_time_range: Optional[str] = None  # Время доставки, например "10:00-12:00"
    total_price: Optional[float] = None
    comment: Optional[str] = None
    notes: Optional[str] = None  # Текст открытки
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    client: Optional[Client] = Relationship(
        back_populates="orders_as_client",
        sa_relationship_kwargs={"foreign_keys": "[Order.client_id]"}
    )
    recipient: Optional[Client] = Relationship(
        back_populates="orders_as_recipient",
        sa_relationship_kwargs={"foreign_keys": "[Order.recipient_id]"}
    )
    executor: Optional[User] = Relationship(
        back_populates="executed_orders",
        sa_relationship_kwargs={"foreign_keys": "[Order.executor_id]"}
    )
    courier: Optional[User] = Relationship(
        sa_relationship_kwargs={"foreign_keys": "[Order.courier_id]"}
    )
    order_items: List["OrderItem"] = Relationship(back_populates="order")
    history_entries: List["OrderHistory"] = Relationship(back_populates="order")


class OrderItem(SQLModel, table=True):
    """Модель позиции заказа"""
    __tablename__ = "order_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    product_id: int = Field(foreign_key="products.id")
    quantity: int = Field(default=1)
    price: float

    # Relationships
    order: Optional[Order] = Relationship(back_populates="order_items")
    product: Optional[Product] = Relationship(back_populates="order_items")


class ProductInventory(SQLModel, table=True):
    """Связь продукта с материалами на складе"""
    __tablename__ = "product_inventory"

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id")
    inventory_id: int = Field(foreign_key="inventory.id")
    quantity_needed: float

    # Relationships
    product: Optional[Product] = Relationship(back_populates="product_inventories")
    inventory: Optional[Inventory] = Relationship(back_populates="product_inventories")


class OrderHistory(SQLModel, table=True):
    """История изменений заказа"""
    __tablename__ = "order_history"

    id: Optional[int] = Field(default=None, primary_key=True)
    order_id: int = Field(foreign_key="orders.id")
    action: str  # "status_changed", "created", "edited", etc.
    old_status: Optional[str] = None
    new_status: Optional[str] = None
    comment: Optional[str] = None
    changed_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    order: Optional[Order] = Relationship(back_populates="history_entries")
    changed_by: Optional[User] = Relationship()


class Shop(SQLModel, table=True):
    """Модель информации о магазине/цветочной мастерской"""
    __tablename__ = "shop"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str  # Название магазина
    address: str  # Адрес магазина
    phone: str  # Телефон магазина
    workingHours: str  # Часы работы
    description: Optional[str] = None  # Описание магазина


class InventoryAudit(SQLModel, table=True):
    """Модель инвентаризации склада"""
    __tablename__ = "inventory_audit"

    id: Optional[int] = Field(default=None, primary_key=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    created_by_id: Optional[int] = Field(default=None, foreign_key="users.id")
    status: str = "in_progress"  # 'in_progress', 'completed', 'cancelled'
    notes: Optional[str] = None  # Примечания к инвентаризации

    # Relationships
    created_by: Optional[User] = Relationship()
    audit_items: List["InventoryAuditItem"] = Relationship(back_populates="audit")


class InventoryAuditItem(SQLModel, table=True):
    """Позиции инвентаризации"""
    __tablename__ = "inventory_audit_items"

    id: Optional[int] = Field(default=None, primary_key=True)
    audit_id: int = Field(foreign_key="inventory_audit.id")
    inventory_id: int = Field(foreign_key="inventory.id")
    system_quantity: float  # Учетное количество на момент инвентаризации
    actual_quantity: Optional[float] = None  # Фактическое количество
    difference: Optional[float] = None  # Разница (вычисляется автоматически)
    reason: Optional[str] = None  # Причина расхождения

    # Relationships
    audit: Optional[InventoryAudit] = Relationship(back_populates="audit_items")
    inventory_item: Optional[Inventory] = Relationship()


class TransactionType(str, Enum):
    """Типы операций со складом"""
    SUPPLY = "supply"  # Поставка
    CONSUMPTION = "consumption"  # Расход на заказ
    WASTE = "waste"  # Списание
    ADJUSTMENT = "adjustment"  # Корректировка
    AUDIT = "audit"  # Корректировка по результатам инвентаризации
    PRICE_CHANGE = "price_change"  # Изменение цены


class InventoryTransaction(SQLModel, table=True):
    """История операций со складом"""
    __tablename__ = "inventory_transactions"

    id: Optional[int] = Field(default=None, primary_key=True)
    inventory_id: int = Field(foreign_key="inventory.id", index=True)
    transaction_type: TransactionType
    quantity: float  # Положительное для прихода, отрицательное для расхода
    comment: Optional[str] = None
    reference_type: Optional[str] = None  # 'order', 'audit', 'manual'
    reference_id: Optional[int] = None  # ID связанного объекта
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by_id: Optional[int] = Field(default=None, foreign_key="users.id")

    # Relationships
    inventory_item: Optional[Inventory] = Relationship()
    created_by: Optional[User] = Relationship()


# Database setup
DATABASE_URL = "sqlite:///./leken_sqlmodel.db"

engine = create_engine(DATABASE_URL, echo=False, connect_args={"check_same_thread": False})


def create_db_and_tables():
    """Создание всех таблиц в базе данных"""
    SQLModel.metadata.create_all(engine)


def get_session():
    """Получение сессии для работы с БД"""
    with Session(engine) as session:
        yield session