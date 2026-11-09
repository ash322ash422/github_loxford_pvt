# Run from tutorial2: python -m pytest -v
from collections.abc import Iterator
from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

import main


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> Iterator[TestClient]:
    """Provide a test client with a fresh inventory for each test."""
    # Give each test its own inventory, including copies of the mutable items.
    monkeypatch.setattr(main, "items", deepcopy(main.items))
    with TestClient(main.app) as test_client:
        yield test_client


@pytest.fixture
def new_item() -> dict[str, str | int | float]:
    """Provide a valid JSON payload for tests that submit a new item."""
    return {
        "id": 4,
        "name": "Screwdriver",
        "price": 3.99,
        "count": 10,
        "category": "tools",
    }


def test_list_items(client: TestClient):
    """Check that GET / returns the three starter items keyed by ID."""
    response = client.get("/")

    assert response.status_code == 200
    inventory = response.json()["items"]
    assert set(inventory) == {"0", "1", "2"}
    assert inventory["0"]["name"] == "Drills"


def test_get_item(client: TestClient):
    """Check that looking up a known ID returns the item's full data."""
    response = client.get("/items/1")

    assert response.status_code == 200
    assert response.json() == {
        "id": 1,
        "name": "Saw",
        "price": 3.99,
        "count": 20,
        "category": "tools",
    }


@pytest.mark.parametrize(
    ("method", "path"),
    [("GET", "/items/99"), ("PUT", "/update/99"), ("DELETE", "/delete/99")],
)
def test_missing_item_returns_404(client: TestClient, method: str, path: str):
    """Check that reading, updating, or deleting a missing item returns 404."""
    response = client.request(method, path)

    assert response.status_code == 404
    assert response.json() == {"detail": "Item with item_id=99 does not exist."}


@pytest.mark.parametrize(
    ("params", "expected_ids"),
    [
        ({}, [0, 1, 2]),
        ({"name": "Drills"}, [0]),
        ({"price": 2.99}, [0, 2]),
        ({"count": 50}, [0, 1]),
        ({"category": "tools"}, [0, 1]),
        ({"category": "tools", "price": 3.99}, [1]),
        ({"name": "Unknown"}, []),
    ],
)
def test_filter_items(
    client: TestClient, params: dict[str, str | int | float], expected_ids: list[int]
):
    """Check the returned items and echoed query for each filter combination."""
    response = client.get("/items/", params=params)

    assert response.status_code == 200
    assert sorted(item["id"] for item in response.json()["selection"]) == expected_ids
    assert response.json()["query"] == dict.fromkeys(
        ("name", "price", "count", "category")
    ) | params


def test_create_item(client: TestClient, new_item: dict):
    """Create an item and confirm it can be retrieved by ID."""
    response = client.post("/", json=new_item)

    assert response.status_code == 200
    assert response.json() == {"added": new_item}
    assert client.get("/items/4").json() == new_item


def test_duplicate_id_does_not_overwrite_item(client: TestClient, new_item: dict):
    """Check that reusing an ID returns 400 and preserves the original item."""
    original_item = client.get("/items/0").json()
    response = client.post("/", json={**new_item, "id": 0})

    assert response.status_code == 400
    assert response.json() == {"detail": "Item with item.id=0 already exists."}
    assert client.get("/items/0").json() == original_item


@pytest.mark.parametrize(
    ("field", "value"),
    [("name", None), ("id", "invalid"), ("category", "invalid")],
)
def test_create_rejects_invalid_body(
    client: TestClient, new_item: dict, field: str, value: str | None
):
    """Check that invalid JSON field values return 422 without adding an item."""
    response = client.post("/", json={**new_item, field: value})

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", field]
    assert set(client.get("/").json()["items"]) == {"0", "1", "2"}


def test_update_item_preserves_omitted_fields(client: TestClient):
    """Update price and count, then confirm omitted fields keep their values."""
    original_item = client.get("/items/0").json()
    response = client.put("/update/0", params={"count": 0, "price": 4.5})

    expected_item = {**original_item, "count": 0, "price": 4.5}
    assert response.status_code == 200
    assert response.json() == {"updated": expected_item}
    assert client.get("/items/0").json() == expected_item


def test_update_name(client: TestClient):
    """Check that sending only the name successfully renames an item."""
    response = client.put("/update/0", params={"name": "Hand Drill"})

    assert response.status_code == 200
    assert response.json()["updated"]["name"] == "Hand Drill"


def test_update_requires_at_least_one_change(client: TestClient):
    """Check that updating an item without any query fields returns 400."""
    response = client.put("/update/0")

    assert response.status_code == 400
    assert response.json() == {"detail": "No parameters provided for update."}


def test_delete_item(client: TestClient):
    """Delete an item, check the returned data, and verify its ID now returns 404."""
    original_item = client.get("/items/0").json()
    response = client.delete("/delete/0")

    assert response.status_code == 200
    assert response.json() == {"deleted": original_item}
    assert client.get("/items/0").status_code == 404


def test_uuid_path_is_parsed_and_normalized(client: TestClient):
    """Check that an uppercase UUID in the URL is returned in lowercase."""
    value = "550e8400-e29b-41d4-a716-446655440000"

    response = client.get(f"/validate-uuid/{value.upper()}")

    assert response.status_code == 200
    assert response.json() == {"uuid": value}


@pytest.mark.parametrize(
    ("method", "url", "location"),
    [
        ("GET", "/items/invalid", ["path", "item_id"]),
        ("GET", "/items/?category=invalid", ["query", "category"]),
        ("PUT", "/update/-1?count=2", ["path", "item_id"]),
        ("PUT", "/update/0?name=", ["query", "name"]),
        ("PUT", "/update/0?name=TooLongForAPI", ["query", "name"]),
        ("PUT", "/update/0?price=0", ["query", "price"]),
        ("PUT", "/update/0?count=-1", ["query", "count"]),
        ("DELETE", "/delete/invalid", ["path", "item_id"]),
        ("GET", "/validate-uuid/invalid", ["path", "value"]),
    ],
)
def test_request_validation(
    client: TestClient, method: str, url: str, location: list[str]
):
    """Check that invalid path and query values return 422 and identify the field."""
    response = client.request(method, url)

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == location


def test_openapi_exposes_uuid_format(client: TestClient):
    """Check that the OpenAPI schema marks the path parameter as a UUID."""
    response = client.get("/openapi.json")

    assert response.status_code == 200
    route = response.json()["paths"]["/validate-uuid/{value}"]["get"]
    assert route["parameters"][0]["schema"]["format"] == "uuid"


@pytest.mark.parametrize(("url", "title"), [("/docs", "Swagger UI"), ("/redoc", "ReDoc")])
def test_documentation_pages(client: TestClient, url: str, title: str):
    """Check that Swagger UI and ReDoc each return the expected HTML page."""
    response = client.get(url)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert title in response.text


def test_swagger_oauth_redirect_page(client: TestClient):
    """Check that Swagger UI's OAuth redirect helper serves HTML."""
    response = client.get("/docs/oauth2-redirect")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
