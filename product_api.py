"""
Product API endpoints for enhanced product management
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_

from database import get_db
from product_enhancements import (
    ProductCategory, ProductEnhanced, ProductVariation,
    ProductImage, ProductComposition, ProductPriceTier, ProductReview,
    create_sample_categories, create_sample_enhanced_product
)

router = APIRouter()

# Pydantic models for API

class CategoryCreate(BaseModel):
    name: str
    parent_id: Optional[int] = None
    description: Optional[str] = None
    display_order: int = 0

class CategoryResponse(BaseModel):
    id: int
    name: str
    parent_id: Optional[int]
    description: Optional[str]
    display_order: int
    is_active: bool
    subcategories: List['CategoryResponse'] = []

    class Config:
        from_attributes = True

CategoryResponse.model_rebuild()


class VariationCreate(BaseModel):
    variation_type: str
    variation_value: str
    price_modifier: float = 0
    sku_suffix: Optional[str] = None
    stock_quantity: int = 0
    stem_count: Optional[int] = None


class ImageCreate(BaseModel):
    image_url: str
    image_type: str = 'main'
    display_order: int = 0
    alt_text: Optional[str] = None


class CompositionCreate(BaseModel):
    inventory_id: int
    quantity_needed: float
    unit: Optional[str] = None
    is_optional: bool = False
    notes: Optional[str] = None


class PriceTierCreate(BaseModel):
    min_quantity: int
    price_per_unit: float
    discount_percentage: Optional[float] = None


class ProductCreate(BaseModel):
    sku: str
    name: str
    description: Optional[str] = None
    category_id: Optional[int] = None
    base_price: float
    cost_price: Optional[float] = None
    product_type: str = Field(pattern="^(букет|композиция|горшечный|аксессуар)$")
    main_flowers: Optional[List[str]] = None
    color_scheme: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    height_cm: Optional[int] = None
    width_cm: Optional[int] = None
    weight_grams: Optional[int] = None
    min_preparation_hours: float = 2
    max_storage_days: Optional[int] = None
    care_instructions: Optional[str] = None
    slug: Optional[str] = None


class ProductUpdate(BaseModel):
    sku: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    category_id: Optional[int] = None
    base_price: Optional[float] = None
    cost_price: Optional[float] = None
    product_type: Optional[str] = Field(None, pattern="^(букет|композиция|горшечный|аксессуар)$")
    main_flowers: Optional[List[str]] = None
    color_scheme: Optional[str] = None
    occasion: Optional[str] = None
    season: Optional[str] = None
    height_cm: Optional[int] = None
    width_cm: Optional[int] = None
    weight_grams: Optional[int] = None
    min_preparation_hours: Optional[float] = None
    max_storage_days: Optional[int] = None
    care_instructions: Optional[str] = None
    slug: Optional[str] = None
    is_active: Optional[bool] = None


class ProductDetailResponse(BaseModel):
    id: int
    sku: str
    name: str
    description: Optional[str]
    category_id: Optional[int]
    category_name: Optional[str]
    base_price: float
    cost_price: Optional[float]
    product_type: str
    main_flowers: Optional[List[str]]
    color_scheme: Optional[str]
    occasion: Optional[str]
    season: Optional[str]
    height_cm: Optional[int]
    width_cm: Optional[int]
    weight_grams: Optional[int]
    min_preparation_hours: float
    max_storage_days: Optional[int]
    care_instructions: Optional[str]
    slug: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime
    variations: List[Dict[str, Any]] = []
    images: List[Dict[str, Any]] = []
    price_tiers: List[Dict[str, Any]] = []
    average_rating: Optional[float] = None
    review_count: int = 0


class ProductListResponse(BaseModel):
    products: List[ProductDetailResponse]
    total: int
    page: int
    page_size: int


class ReviewCreate(BaseModel):
    product_id: int
    rating: int = Field(ge=1, le=5)
    review_text: Optional[str] = None


# Category endpoints

@router.post("/categories", response_model=CategoryResponse)
def create_category(category: CategoryCreate, db: Session = Depends(get_db)):
    """Create a new product category"""
    db_category = ProductCategory(**category.dict())
    db.add(db_category)
    db.commit()
    db.refresh(db_category)
    return db_category


@router.get("/categories", response_model=List[CategoryResponse])
def get_categories(
    include_inactive: bool = False,
    db: Session = Depends(get_db)
):
    """Get all product categories with hierarchy"""
    query = db.query(ProductCategory)
    if not include_inactive:
        query = query.filter(ProductCategory.is_active == True)

    categories = query.order_by(ProductCategory.display_order).all()

    # Build hierarchy
    category_dict = {cat.id: cat for cat in categories}
    root_categories = []

    for category in categories:
        if category.parent_id is None:
            root_categories.append(category)

    return root_categories


# Product endpoints

@router.post("/products-enhanced")
def create_enhanced_product(
    product: ProductCreate,
    variations: List[VariationCreate] = [],
    images: List[ImageCreate] = [],
    price_tiers: List[PriceTierCreate] = [],
    db: Session = Depends(get_db)
):
    """Create a new enhanced product with variations and pricing"""

    # Create main product
    db_product = ProductEnhanced(**product.dict())
    db.add(db_product)
    db.flush()

    # Add variations
    for var in variations:
        db_var = ProductVariation(product_id=db_product.id, **var.dict())
        db.add(db_var)

    # Add images
    for img in images:
        db_img = ProductImage(product_id=db_product.id, **img.dict())
        db.add(db_img)

    # Add price tiers
    for tier in price_tiers:
        db_tier = ProductPriceTier(product_id=db_product.id, **tier.dict())
        db.add(db_tier)

    db.commit()
    db.refresh(db_product)

    return {"message": "Product created successfully", "product_id": db_product.id}


@router.get("/products-enhanced/{product_id}", response_model=ProductDetailResponse)
def get_product_details(product_id: int, db: Session = Depends(get_db)):
    """Get detailed product information including variations and pricing"""

    product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Build response
    response_data = {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "category_id": product.category_id,
        "category_name": product.category.name if product.category else None,
        "base_price": product.base_price,
        "cost_price": product.cost_price,
        "product_type": product.product_type,
        "main_flowers": product.main_flowers,
        "color_scheme": product.color_scheme,
        "occasion": product.occasion,
        "season": product.season,
        "height_cm": product.height_cm,
        "width_cm": product.width_cm,
        "weight_grams": product.weight_grams,
        "min_preparation_hours": product.min_preparation_hours,
        "max_storage_days": product.max_storage_days,
        "care_instructions": product.care_instructions,
        "slug": product.slug,
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
        "variations": [],
        "images": [],
        "price_tiers": []
    }

    # Add variations
    for var in product.variations:
        response_data["variations"].append({
            "id": var.id,
            "type": var.variation_type,
            "value": var.variation_value,
            "price_modifier": var.price_modifier,
            "stem_count": var.stem_count,
            "stock_quantity": var.stock_quantity,
            "is_available": var.is_available
        })

    # Add images
    for img in product.images:
        response_data["images"].append({
            "id": img.id,
            "url": img.image_url,
            "type": img.image_type,
            "alt_text": img.alt_text,
            "display_order": img.display_order
        })

    # Add price tiers
    for tier in product.price_tiers:
        response_data["price_tiers"].append({
            "id": tier.id,
            "min_quantity": tier.min_quantity,
            "price_per_unit": tier.price_per_unit,
            "discount_percentage": tier.discount_percentage
        })

    # Calculate average rating
    reviews = db.query(ProductReview).filter(ProductReview.product_id == product_id).all()
    if reviews:
        response_data["average_rating"] = sum(r.rating for r in reviews) / len(reviews)
        response_data["review_count"] = len(reviews)

    return response_data


@router.get("/products-enhanced", response_model=ProductListResponse)
def search_products(
    category_id: Optional[int] = None,
    product_type: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    occasion: Optional[str] = None,
    color_scheme: Optional[str] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("name", pattern="^(name|price|created_at)$"),
    sort_order: str = Query("asc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db)
):
    """Search and filter products with pagination"""

    query = db.query(ProductEnhanced).filter(ProductEnhanced.is_active == True)

    # Apply filters
    if category_id:
        query = query.filter(ProductEnhanced.category_id == category_id)

    if product_type:
        query = query.filter(ProductEnhanced.product_type == product_type)

    if min_price:
        query = query.filter(ProductEnhanced.base_price >= min_price)

    if max_price:
        query = query.filter(ProductEnhanced.base_price <= max_price)

    if occasion:
        query = query.filter(ProductEnhanced.occasion == occasion)

    if color_scheme:
        query = query.filter(ProductEnhanced.color_scheme == color_scheme)

    if search:
        search_term = f"%{search}%"
        query = query.filter(
            or_(
                ProductEnhanced.name.ilike(search_term),
                ProductEnhanced.description.ilike(search_term),
                ProductEnhanced.sku.ilike(search_term)
            )
        )

    # Count total
    total = query.count()

    # Apply sorting
    if sort_by == "name":
        query = query.order_by(ProductEnhanced.name.asc() if sort_order == "asc" else ProductEnhanced.name.desc())
    elif sort_by == "price":
        query = query.order_by(ProductEnhanced.base_price.asc() if sort_order == "asc" else ProductEnhanced.base_price.desc())
    elif sort_by == "created_at":
        query = query.order_by(ProductEnhanced.created_at.asc() if sort_order == "asc" else ProductEnhanced.created_at.desc())

    # Apply pagination
    offset = (page - 1) * page_size
    products = query.offset(offset).limit(page_size).all()

    # Build response
    product_list = []
    for product in products:
        product_data = {
            "id": product.id,
            "sku": product.sku,
            "name": product.name,
            "description": product.description,
            "category_id": product.category_id,
            "category_name": product.category.name if product.category else None,
            "base_price": product.base_price,
            "cost_price": product.cost_price,
            "product_type": product.product_type,
            "main_flowers": product.main_flowers,
            "color_scheme": product.color_scheme,
            "occasion": product.occasion,
            "season": product.season,
            "height_cm": product.height_cm,
            "width_cm": product.width_cm,
            "weight_grams": product.weight_grams,
            "min_preparation_hours": product.min_preparation_hours,
            "max_storage_days": product.max_storage_days,
            "care_instructions": product.care_instructions,
            "slug": product.slug,
            "is_active": product.is_active,
            "created_at": product.created_at,
            "updated_at": product.updated_at,
            "variations": [],
            "images": [],
            "price_tiers": [],
            "average_rating": None,
            "review_count": 0
        }

        # Add first image if exists
        first_image = next((img for img in product.images if img.image_type == 'main'), None)
        if first_image:
            product_data["images"].append({
                "url": first_image.image_url,
                "alt_text": first_image.alt_text
            })

        product_list.append(product_data)

    return {
        "products": product_list,
        "total": total,
        "page": page,
        "page_size": page_size
    }


@router.post("/products/{product_id}/reviews", response_model=dict)
def add_product_review(
    product_id: int,
    review: ReviewCreate,
    client_id: int = 1,  # Temporarily hardcoded
    db: Session = Depends(get_db)
):
    """Add a review for a product"""

    # Check if product exists
    product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    db_review = ProductReview(
        product_id=product_id,
        client_id=client_id,
        rating=review.rating,
        review_text=review.review_text
    )
    db.add(db_review)
    db.commit()

    return {"message": "Review added successfully", "review_id": db_review.id}


@router.get("/products/{product_id}/calculate-price")
def calculate_product_price(
    product_id: int,
    quantity: int = Query(1, ge=1),
    variation_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Calculate final price based on quantity and variations"""

    product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    base_price = product.base_price

    # Apply variation modifier
    if variation_id:
        variation = db.query(ProductVariation).filter(
            and_(
                ProductVariation.id == variation_id,
                ProductVariation.product_id == product_id
            )
        ).first()
        if variation:
            base_price += variation.price_modifier

    # Find applicable price tier
    price_tier = db.query(ProductPriceTier).filter(
        and_(
            ProductPriceTier.product_id == product_id,
            ProductPriceTier.min_quantity <= quantity
        )
    ).order_by(ProductPriceTier.min_quantity.desc()).first()

    if price_tier:
        unit_price = price_tier.price_per_unit
        discount = price_tier.discount_percentage or 0
    else:
        unit_price = base_price
        discount = 0

    total_price = unit_price * quantity
    discount_amount = total_price * (discount / 100) if discount else 0
    final_price = total_price - discount_amount

    return {
        "product_id": product_id,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "discount_percentage": discount,
        "discount_amount": discount_amount,
        "final_price": final_price
    }


@router.put("/products-enhanced/{product_id}", response_model=ProductDetailResponse)
def update_enhanced_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Update enhanced product (PUT method - complete replacement)"""
    db_product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    # Validate category if being updated
    if product.category_id:
        category = db.query(ProductCategory).filter(ProductCategory.id == product.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    # Check if SKU already exists (if being updated)
    if product.sku and product.sku != db_product.sku:
        existing_product = db.query(ProductEnhanced).filter(ProductEnhanced.sku == product.sku).first()
        if existing_product:
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")

    update_data = product.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)

    return get_product_details(product_id, db)


@router.patch("/products-enhanced/{product_id}", response_model=ProductDetailResponse)
def partial_update_enhanced_product(
    product_id: int,
    product: ProductUpdate,
    db: Session = Depends(get_db)
):
    """Partial update enhanced product (PATCH method)"""
    db_product = db.query(ProductEnhanced).filter(ProductEnhanced.id == product_id).first()
    if not db_product:
        raise HTTPException(status_code=404, detail="Product not found")

    update_data = product.dict(exclude_unset=True)
    if not update_data:
        raise HTTPException(status_code=400, detail="No fields provided for update")

    # Validate category if being updated
    if product.category_id:
        category = db.query(ProductCategory).filter(ProductCategory.id == product.category_id).first()
        if not category:
            raise HTTPException(status_code=404, detail="Category not found")

    # Check if SKU already exists (if being updated)
    if product.sku and product.sku != db_product.sku:
        existing_product = db.query(ProductEnhanced).filter(ProductEnhanced.sku == product.sku).first()
        if existing_product:
            raise HTTPException(status_code=400, detail="Product with this SKU already exists")

    for field, value in update_data.items():
        setattr(db_product, field, value)

    db.commit()
    db.refresh(db_product)

    return get_product_details(product_id, db)


# Initialize sample data endpoint
@router.post("/products-initialize-samples")
def initialize_sample_data(db: Session = Depends(get_db)):
    """Create sample categories and products"""

    # Check if categories already exist
    existing_categories = db.query(ProductCategory).count()
    if existing_categories == 0:
        create_sample_categories(db)

    # Check if enhanced products exist
    existing_products = db.query(ProductEnhanced).count()
    if existing_products == 0:
        create_sample_enhanced_product(db)

    return {
        "message": "Sample data initialized",
        "categories_created": existing_categories == 0,
        "products_created": existing_products == 0
    }