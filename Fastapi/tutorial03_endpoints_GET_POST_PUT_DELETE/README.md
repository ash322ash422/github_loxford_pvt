# FastAPI Tutorial 2 — Inventory API

A small inventory API for learning FastAPI with Python 3.11 or later. The app starts with three items. It stores changes in memory, so restarting the server resets the inventory.

## What you'll learn

- Build CRUD routes with `GET`, `POST`, `PUT`, and `DELETE`.
- Use Pydantic models, field descriptions, and enums to define request and response data.
- Validate integer and UUID path parameters, optional query parameters, and JSON bodies.
- Use `HTTPException` for application errors and inspect FastAPI's automatic `422` validation responses.
- Test status codes, response bodies, and inventory changes with pytest and FastAPI's `TestClient`.

## Run locally

Open PowerShell in `tutorial2`. Create a fresh virtual environment and use its Python executable for each command.

```powershell
python -m venv .venv-fastapi
.\.venv-fastapi\Scripts\python.exe -m pip install -r requirements.txt
.\.venv-fastapi\Scripts\python.exe -m uvicorn main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs) to try the API. Uvicorn's `--reload` option restarts the app when the source changes. Press Ctrl+C to stop the server.

## Inventory and UUID endpoints

| Method | Path | Inputs and behavior | Status codes |
| --- | --- | --- | --- |
| GET | `/` | List all items keyed by ID. JSON object keys are strings. | `200` |
| POST | `/` | Create an item from a JSON body with `id`, `name`, `price`, `count`, and `category`. | `200` created, `400` duplicate ID, `422` invalid body |
| GET | `/items/{item_id}` | Retrieve one item by integer ID. | `200`, `404` missing item, `422` invalid ID |
| GET | `/items/` | Filter by optional `name`, `price`, `count`, and `category`. Returns the query and matching items. | `200`, `422` invalid query |
| PUT | `/update/{item_id}` | Update one or more query fields. ID must be nonnegative, name must be 1–12 characters, price must be positive, and count must be nonnegative. | `200`, `400` no fields, `404` missing item, `422` invalid input |
| DELETE | `/delete/{item_id}` | Delete one item by integer ID and return the deleted item. | `200`, `404` missing item, `422` invalid ID |
| GET | `/validate-uuid/{value}` | Parse a UUID path parameter and return it as a lowercase, hyphenated string. | `200`, `422` invalid UUID |

Filters combine with AND. The `name`, `price`, and `category` filters use exact matches. The `count` filter excludes that stock count, so `/items/?count=50` returns items whose count differs from 50. Valid categories are `tools` and `consumables`.

Try `/validate-uuid/550E8400-E29B-41D4-A716-446655440000` in Swagger UI, then try `/validate-uuid/invalid` to see FastAPI report the invalid path parameter.

### FastAPI documentation endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/docs` | Interactive Swagger UI |
| GET | `/redoc` | ReDoc API reference |
| GET | `/openapi.json` | Machine-readable OpenAPI schema |
| GET | `/docs/oauth2-redirect` | Swagger UI's OAuth redirect helper |

## Run the tests

From `tutorial2`, run the following in PowerShell. `TestClient` sends requests directly to the app, so the tests run independently of Uvicorn.

```powershell
.\.venv-fastapi\Scripts\python.exe -m pytest -v
```
### or

```powershell
.\.venv-fastapi\Scripts\python.exe -m pytest -q
```

Each test starts with a fresh inventory copy. The suite covers each route and checks invalid input, missing items, duplicate IDs, and state changes after writes.

[FastAPI testing guide](https://fastapi.tiangolo.com/tutorial/testing/)
