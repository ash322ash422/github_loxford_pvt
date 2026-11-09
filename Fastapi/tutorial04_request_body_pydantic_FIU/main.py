from fastapi import FastAPI
from pydantic import BaseModel, Field

app = FastAPI(title="Request Body and Pydantic")


class ProductRequest(BaseModel):
    """Describe the JSON object expected from the client."""

    name: str = Field(min_length=1)
    price: float = Field(gt=0)
    quantity: int = Field(default=1, ge=1)
    description: str | None = None


@app.post("/products/preview")
def preview_product(product: ProductRequest) -> ProductRequest:
    """Return the validated product with any defaults filled in."""
    return product
