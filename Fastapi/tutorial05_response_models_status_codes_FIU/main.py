from typing import TypedDict
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Response, status
from pydantic import BaseModel, Field

app = FastAPI(title="Response Models and Status Codes")


class ProductCreate(BaseModel):
    """Validate the JSON a client sends when creating a product."""

    name: str = Field(min_length=1)
    price: float = Field(gt=0)


class ProductResponse(BaseModel):
    """Define the fields that clients receive in successful responses."""

    id: UUID
    name: str
    price: float


class StoredProduct(TypedDict):
    """Represent a record with one extra field used internally."""

    id: UUID
    name: str
    price: float
    internal_note: str


products: dict[UUID, StoredProduct] = {}


@app.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_product(product: ProductCreate, response: Response) -> StoredProduct:
    """Create a product and tell the client where to retrieve it."""
    product_id = uuid4()
    record: StoredProduct = {
        "id": product_id,
        "name": product.name,
        "price": product.price,
        "internal_note": "Pending catalog review",
    }
    products[product_id] = record
    # Customize the header while FastAPI builds the JSON response.
    response.headers["Location"] = f"/products/{product_id}"
    return record


@app.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: UUID) -> StoredProduct:
    """Return a product or raise 404 for an unknown UUID."""
    product = products.get(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return product


@app.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_product(product_id: UUID) -> Response:
    """Delete a product and send an empty 204 response."""
    if products.pop(product_id, None) is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
