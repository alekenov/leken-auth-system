"""
Enhanced Product System for Florist CRM
Includes product variations, attributes, and composition tracking
"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Boolean, Date, JSON
from sqlalchemy.orm import relationship
from datetime import datetime

# Import Base and engine from main database module
from database import Base, engine, SessionLocal

# Enhanced Product Models

class ProductCategory(Base):
    """Hierarchical product categories"""
    __tablename__ = "product_categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    parent_id = Column(Integer, ForeignKey("product_categories.id"), nullable=True)
    description = Column(Text)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Self-referential relationship for hierarchy
    parent = relationship("ProductCategory", remote_side=[id], backref="subcategories")
    products = relationship("ProductEnhanced", back_populates="category")


class ProductEnhanced(Base):
    """Enhanced product model with detailed attributes"""
    __tablename__ = "products_enhanced"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String, unique=True, index=True)  # Stock keeping unit
    name = Column(String, nullable=False)
    description = Column(Text)
    category_id = Column(Integer, ForeignKey("product_categories.id"))

    # Pricing
    base_price = Column(Float, nullable=False)
    cost_price = Column(Float)  # Cost to make/buy

    # Product type specific fields
    product_type = Column(String, nullable=False)  # 'букет', 'композиция', 'горшечный', 'аксессуар'

    # Flower specific attributes
    main_flowers = Column(JSON)  # List of main flowers used
    color_scheme = Column(String)  # 'красный', 'белый', 'микс', etc
    occasion = Column(String)  # 'день рождения', 'свадьба', 'романтика', etc
    season = Column(String)  # 'всесезонный', 'весенний', 'летний', etc

    # Physical attributes
    height_cm = Column(Integer)
    width_cm = Column(Integer)
    weight_grams = Column(Integer)

    # Availability and stock
    is_active = Column(Boolean, default=True)
    is_seasonal = Column(Boolean, default=False)
    min_preparation_hours = Column(Float, default=2)
    max_storage_days = Column(Integer)  # How long can be stored

    # Care instructions
    care_instructions = Column(Text)

    # SEO and display
    meta_title = Column(String)
    meta_description = Column(Text)
    slug = Column(String, unique=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    category = relationship("ProductCategory", back_populates="products")
    variations = relationship("ProductVariation", back_populates="product")
    images = relationship("ProductImage", back_populates="product")
    compositions = relationship("ProductComposition", back_populates="product")
    price_tiers = relationship("ProductPriceTier", back_populates="product")


class ProductVariation(Base):
    """Product variations (size, color options, etc)"""
    __tablename__ = "product_variations"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_enhanced.id"), nullable=False)
    variation_type = Column(String, nullable=False)  # 'размер', 'цвет', 'упаковка'
    variation_value = Column(String, nullable=False)  # 'большой', 'красный', 'премиум'
    price_modifier = Column(Float, default=0)  # Add/subtract from base price
    sku_suffix = Column(String)
    stock_quantity = Column(Integer, default=0)
    is_available = Column(Boolean, default=True)

    # Size specific
    stem_count = Column(Integer)  # Number of flowers in bouquet

    product = relationship("ProductEnhanced", back_populates="variations")


class ProductImage(Base):
    """Multiple images per product"""
    __tablename__ = "product_images"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_enhanced.id"), nullable=False)
    image_url = Column(String, nullable=False)
    image_type = Column(String, default='main')  # 'main', 'gallery', 'thumbnail'
    display_order = Column(Integer, default=0)
    alt_text = Column(String)

    product = relationship("ProductEnhanced", back_populates="images")


class ProductComposition(Base):
    """Track what materials/flowers make up a product"""
    __tablename__ = "product_compositions"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_enhanced.id"), nullable=False)
    inventory_id = Column(Integer, ForeignKey("inventory.id"), nullable=False)
    quantity_needed = Column(Float, nullable=False)
    unit = Column(String)  # Override inventory unit if needed
    is_optional = Column(Boolean, default=False)
    notes = Column(Text)

    product = relationship("ProductEnhanced", back_populates="compositions")
    inventory_item = relationship("Inventory")


class ProductPriceTier(Base):
    """Quantity-based pricing tiers"""
    __tablename__ = "product_price_tiers"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_enhanced.id"), nullable=False)
    min_quantity = Column(Integer, nullable=False)
    price_per_unit = Column(Float, nullable=False)
    discount_percentage = Column(Float)

    product = relationship("ProductEnhanced", back_populates="price_tiers")


class ProductReview(Base):
    """Customer reviews for products"""
    __tablename__ = "product_reviews"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products_enhanced.id"), nullable=False)
    order_id = Column(Integer, ForeignKey("orders.id"))
    client_id = Column(Integer, ForeignKey("clients.id"))
    rating = Column(Integer, nullable=False)  # 1-5
    review_text = Column(Text)
    is_verified = Column(Boolean, default=False)  # Verified purchase
    created_at = Column(DateTime, default=datetime.utcnow)

    product = relationship("ProductEnhanced")
    order = relationship("Order")
    client = relationship("Client")


# Sample data creation functions

def create_sample_categories(session):
    """Create sample product categories"""
    categories = [
        {"name": "Букеты", "description": "Готовые букеты различных размеров"},
        {"name": "Композиции", "description": "Флористические композиции в корзинах и коробках"},
        {"name": "Горшечные растения", "description": "Комнатные растения в горшках"},
        {"name": "Свадебные", "description": "Букеты и оформление для свадеб"},
        {"name": "Траурные", "description": "Венки и траурные композиции"},
        {"name": "Подарки и аксессуары", "description": "Открытки, вазы, упаковка"},
    ]

    for cat_data in categories:
        category = ProductCategory(**cat_data)
        session.add(category)

    session.commit()


def create_sample_enhanced_product(session):
    """Create a sample enhanced product with variations"""

    # Get or create category
    category = session.query(ProductCategory).filter_by(name="Букеты").first()

    product = ProductEnhanced(
        sku="BUQ-001",
        name="Букет 'Нежность' - Розы и Эустома",
        description="Изысканный букет из розовых роз и белой эустомы, оформленный в стильную крафт-бумагу",
        category_id=category.id if category else None,
        base_price=15000,  # 15,000 тенге
        cost_price=8000,
        product_type="букет",
        main_flowers=["розы", "эустома", "зелень"],
        color_scheme="розовый-белый",
        occasion="день рождения",
        season="всесезонный",
        height_cm=50,
        width_cm=35,
        weight_grams=800,
        min_preparation_hours=2,
        max_storage_days=3,
        care_instructions="Подрезать стебли под углом, менять воду каждые 2 дня, держать вдали от прямых солнечных лучей",
        slug="buket-nezhnost-rozy-eustoma"
    )
    session.add(product)
    session.flush()  # Get product ID

    # Add variations (sizes)
    variations = [
        {"variation_type": "размер", "variation_value": "Маленький", "price_modifier": -3000, "stem_count": 15, "sku_suffix": "S"},
        {"variation_type": "размер", "variation_value": "Средний", "price_modifier": 0, "stem_count": 25, "sku_suffix": "M"},
        {"variation_type": "размер", "variation_value": "Большой", "price_modifier": 5000, "stem_count": 35, "sku_suffix": "L"},
        {"variation_type": "упаковка", "variation_value": "Премиум коробка", "price_modifier": 3000, "sku_suffix": "BOX"},
    ]

    for var_data in variations:
        var_data["product_id"] = product.id
        variation = ProductVariation(**var_data)
        session.add(variation)

    # Add price tiers
    tiers = [
        {"min_quantity": 1, "price_per_unit": 15000, "discount_percentage": 0},
        {"min_quantity": 5, "price_per_unit": 14250, "discount_percentage": 5},
        {"min_quantity": 10, "price_per_unit": 13500, "discount_percentage": 10},
    ]

    for tier_data in tiers:
        tier_data["product_id"] = product.id
        tier = ProductPriceTier(**tier_data)
        session.add(tier)

    session.commit()
    return product