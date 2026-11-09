# FastAPI lesson — JSON request bodies and Pydantic

**Class time** 15–20 minutes  
**Example** Preview a stationery product submitted as JSON.

## 1. Start the app

Run these commands in PowerShell from this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs), expand `POST /products/preview`, and click **Try it out**. This endpoint echoes the validated product and does not save it.

## 2. Explain the request flow

The **request body** is the data the client sends in the HTTP request. Here it is a JSON object with the content type `application/json`.

In `preview_product(product: ProductRequest)`, the type hint tells FastAPI to read the JSON body into a Pydantic model. Pydantic checks the field types and constraints and fills in missing defaults. The route receives a Python object, so the name is available as `product.name`. If validation fails, FastAPI returns **422** before calling the route.

| Field | Python declaration | Can omit? | Accepts JSON `null`? | Validation |
| --- | --- | --- | --- | --- |
| `name` | `str = Field(min_length=1)` | No | No | At least one character |
| `price` | `float = Field(gt=0)` | No | No | Greater than zero |
| `quantity` | `int = Field(default=1, ge=1)` | Yes, defaults to `1` | No | Integer of at least one |
| `description` | `str \| None = None` | Yes, defaults to `None` | Yes | Text or `null` |

**Omission and `null` are separate rules.** A default lets the client omit a field. The type hint controls whether the client can explicitly send `null`. In Pydantic v2, `description: str | None` without a default is required and accepts `null`. In Python, `Optional[str]` means the same thing as `str | None`.

## 3. Demo in Swagger UI

Start with the smallest valid request.

```json
{"name": "Notebook", "price": 49.5}
```

Expect **200 OK**. The response shows both defaults.

```json
{"name": "Notebook", "price": 49.5, "quantity": 1, "description": null}
```

Ask students to predict each result before clicking **Execute**.

| Change to the original body | Expected result |
| --- | --- |
| Add `"quantity": 3` | 200, quantity is 3 |
| Add `"description": null` | 200, description is null |
| Add `"quantity": null` | 422, quantity must be an integer |
| Set `"price": 0` | 422, price must be greater than zero |
| Remove `name` | 422, name is required |
| Add `"quantity": "two"` | 422, quantity cannot be parsed as an integer |
| Add `"quantity": "3"` | 200, Pydantic converts the string to an integer by default |

On a **422** response, inspect `detail[0].loc`. For an invalid price it points to `["body", "price"]`.

## 4. Student exercise

Add `discount_percent` as an integer that defaults to `0` and allows values from `0` to `100` inclusive. Try an omitted value, `20`, and `101`. The first two should return 200, and the last should return 422.

[FastAPI request body guide](https://fastapi.tiangolo.com/tutorial/body/) · [Pydantic field defaults](https://docs.pydantic.dev/latest/concepts/fields/#default-values)
