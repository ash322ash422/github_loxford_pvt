# FastAPI lesson — Response models and status codes

**Class time** 15–20 minutes  
**Example** Create, retrieve, and delete a stationery product. The catalog starts empty and resets when the server restarts.

## 1. Start the app

Run these commands in PowerShell from this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs). Expand an endpoint and click **Try it out**.

## 2. Read the response contract

`ProductCreate` validates what the client sends. `ProductResponse` defines what the client receives on a successful create or read. Both handlers return a Python dictionary containing an `internal_note`. FastAPI uses `response_model=ProductResponse` to validate and filter the returned data, then serializes it as JSON. The output contains `id`, `name`, and `price`. The UUID becomes a string in JSON.

The decorator's `status_code` sets the normal success code and documents it in OpenAPI. The create handler also sets the `Location` header on the injected `Response` object, so FastAPI still applies the response model to the returned dictionary.

| Method | Path | Success | Errors to try |
| --- | --- | --- | --- |
| POST | `/products` | `201 Created`, product JSON, and a `Location` header | `422` for invalid body values |
| GET | `/products/{product_id}` | `200 OK` and product JSON | `404` for an unknown UUID, `422` for a malformed UUID |
| DELETE | `/products/{product_id}` | `204 No Content` with an empty body | `404` for an unknown UUID, `422` for a malformed UUID |

## 3. Demo in Swagger UI

1. **Create a product.** Send this JSON to `POST /products`.

   ```json
   {"name": "Notebook", "price": 49.5}
   ```

   Expect **201**. Under **Response headers**, find `Location: /products/<generated-id>`. Ask students to compare the response body with the dictionary returned by the handler and identify which field FastAPI filtered out.

2. **Retrieve it.** Copy the generated ID into `GET /products/{product_id}`. Expect **200** and the same product JSON.
3. **Delete it.** Use the same ID in `DELETE /products/{product_id}`. Expect **204** and an empty response body.
4. **Retrieve the deleted product.** Repeat the GET. The UUID is still valid, but the record is gone, so expect **404** with `{"detail": "Product not found"}`.
5. **Send invalid input.** Use `not-a-uuid` in the GET or send `{"name": "Notebook", "price": 0}` in the POST. Expect **422**. The `detail` list identifies the invalid field.

## 4. Student exercise

Add a `Cache-Control: no-store` header to successful GET responses. Use the same injected `Response` pattern as the create handler. Create another product, retrieve it, and confirm the header appears alongside the filtered JSON.

For full control over a JSON response, FastAPI also supports returning `JSONResponse` directly. That bypasses automatic response-model validation and filtering, so the handler is responsible for what it exposes.

[Response models](https://fastapi.tiangolo.com/tutorial/response-model/) · [Status codes](https://fastapi.tiangolo.com/tutorial/response-status-code/) · [Response headers](https://fastapi.tiangolo.com/advanced/response-headers/) · [Direct responses](https://fastapi.tiangolo.com/advanced/response-directly/)
