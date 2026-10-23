from fastapi import Depends, FastAPI, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.models import Product
from app.schemas.product import ProductResponse

from app.schemas.product import (
    ProductCreate,
    ProductPatch,
    ProductResponse,
    ProductUpdate,
)

from app.routers.auth import router as auth_router

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="E-commerce marketplace backend",
    version="0.1.0",
    debug=settings.DEBUG,
)
app.include_router(auth_router)

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/products/", response_model=list[ProductResponse])
def get_products(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    statement = select(Product).offset(skip).limit(limit)
    products = db.scalars(statement).all()
    return products


@app.post("/products/", response_model=ProductResponse, status_code=201)
def create_product(
    product_data: ProductCreate,
    db: Session = Depends(get_db),
):
    product = Product(**product_data.model_dump())

    try:
        db.add(product)
        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to create product",
        )

    return product


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    statement = select(Product).where(Product.id == product_id)
    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    return product


@app.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: int,
    product_data: ProductUpdate,
    db: Session = Depends(get_db),
):
    statement = select(Product).where(Product.id == product_id)
    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    try:
        product.name = product_data.name
        product.description = product_data.description
        product.price = product_data.price

        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update product",
        )

    return product


@app.patch("/products/{product_id}", response_model=ProductResponse)
def patch_product(
    product_id: int,
    product_data: ProductPatch,
    db: Session = Depends(get_db),
):
    statement = select(Product).where(Product.id == product_id)
    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    try:
        update_data = product_data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            setattr(product, field, value)

        db.commit()
        db.refresh(product)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to update product",
        )

    return product


@app.delete("/products/{product_id}", status_code=204)
def delete_product(
    product_id: int,
    db: Session = Depends(get_db),
):
    statement = select(Product).where(Product.id == product_id)
    product = db.scalar(statement)

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    try:
        db.delete(product)
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Failed to delete product",
        )

