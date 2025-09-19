from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

DATABASE_URL = "sqlite:///./leken.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Профильные данные
    city = Column(String, nullable=True)  # Алматы или Астана
    position = Column(String, nullable=True)  # Менеджер или Флорист
    address = Column(String, nullable=True)  # Любое текстовое поле
    phone = Column(String, nullable=True)  # +7 + 10 цифр

class Item(Base):
    __tablename__ = "items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


# CRM Models for Florist Business

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=True)  # Имя теперь опционально
    phone = Column(String, nullable=False)  # +7XXXXXXXXXX format
    email = Column(String, nullable=True)
    address = Column(String, nullable=True)
    client_type = Column(String, nullable=False)  # 'заказчик', 'получатель', 'оба'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    orders_as_client = relationship("Order", foreign_keys="Order.client_id", back_populates="client")
    orders_as_recipient = relationship("Order", foreign_keys="Order.recipient_id", back_populates="recipient")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    price = Column(Float, nullable=False)
    category = Column(String, nullable=False)  # 'букет', 'композиция', 'горшечный'
    preparation_time = Column(Integer, nullable=True)  # minutes
    image_url = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    order_items = relationship("OrderItem", back_populates="product")
    product_inventories = relationship("ProductInventory", back_populates="product")


class Inventory(Base):
    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False)  # 'шт', 'м', 'кг'
    min_quantity = Column(Float, nullable=True)  # for low stock warnings
    price_per_unit = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    product_inventories = relationship("ProductInventory", back_populates="inventory")


class Order(Base):
    __tablename__ = "orders"

    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    recipient_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    executor_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, nullable=False, default="новый")  # 'новый', 'в работе', 'готов', 'доставлен'
    delivery_date = Column(DateTime, nullable=False)
    delivery_address = Column(String, nullable=False)
    total_price = Column(Float, nullable=True)
    comment = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    client = relationship("Client", foreign_keys=[client_id], back_populates="orders_as_client")
    recipient = relationship("Client", foreign_keys=[recipient_id], back_populates="orders_as_recipient")
    executor = relationship("User")
    order_items = relationship("OrderItem", back_populates="order")


class OrderItem(Base):
    __tablename__ = "order_items"

    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)

    # Relationships
    order = relationship("Order", back_populates="order_items")
    product = relationship("Product", back_populates="order_items")


class ProductInventory(Base):
    __tablename__ = "product_inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    quantity_needed = Column(Float, nullable=False)

    # Relationships
    product = relationship("Product", back_populates="product_inventories")
    inventory = relationship("Inventory", back_populates="product_inventories")

def create_tables():
    # Import enhanced product models to ensure they're registered with Base
    from product_enhancements import (
        ProductCategory, ProductEnhanced, ProductVariation,
        ProductImage, ProductComposition, ProductPriceTier, ProductReview
    )

    # Create all tables including enhanced product tables
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()