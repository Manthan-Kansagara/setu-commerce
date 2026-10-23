from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dependencies import get_db
from app.models import Product
from app.schemas.product import ProductResponse
from app.schemas.product import ProductCreate, ProductResponse

app = FastAPI(
    title=f"{settings.APP_NAME} API",
    description="E-commerce marketplace backend",
    version="0.1.0",
    debug=settings.DEBUG,
)

@app.get("/")
def root():
    return {"message": f"Welcome to {settings.APP_NAME} API"}


@app.get("/health")
def health_check():
    return {"status": "healthy"}


@app.get("/products/", response_model=list[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    statement = select(Product)
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
