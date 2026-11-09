# FastAPI classroom project — Student CRUD API

**Class time** 25–30 minutes. Students build a small Student API and run the same requests in Swagger UI and Postman.

## Run on Windows

Open PowerShell in this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

## Build the app in class

1. **Define the data.** `StudentInput` validates `name`, `age`, and `course`. The `Student` response model adds the server-generated `id`.
2. **Store records in memory.** Use a dictionary keyed by integer ID. Start with two students and generate subsequent IDs starting at 3. A server restart restores the two starter records.
3. **Connect HTTP methods to dictionary operations.** Create inserts a record, read looks it up, update replaces it, and delete removes it. The lookup helper raises `404` for a missing ID.

| Operation | Method and path | Success | Errors to try |
| --- | --- | --- | --- |
| Create | `POST /students` | `201 Created` with student JSON | `422` invalid body |
| Read all | `GET /students` | `200 OK` with a JSON array | |
| Read one | `GET /students/{student_id}` | `200 OK` with student JSON | `404` missing ID, `422` invalid ID type |
| Update | `PUT /students/{student_id}` | `200 OK` with the replacement record | `404` missing ID, `422` invalid input |
| Delete | `DELETE /students/{student_id}` | `204 No Content` with an empty body | `404` missing ID, `422` invalid ID type |

`PUT` requires all three editable fields and keeps the existing ID.

## Test in Swagger UI

Open [Swagger UI](http://127.0.0.1:8000/docs). For each operation, expand the route, click **Try it out**, then **Execute**.

1. **List students.** On a fresh run, `GET /students` returns the two starter records.
2. **Create.** Send the JSON below to `POST /students`. Expect `201` and copy the returned ID.
3. **Read.** Use that ID in `GET /students/{student_id}`. Expect `200` and the same record.
4. **Update.** Send the same JSON to `PUT /students/{student_id}` with the course changed to `"FastAPI Advanced"`. Expect `200` and the same ID. Repeat the GET to confirm the change.
5. **Delete.** Send `DELETE /students/{student_id}`. Expect `204` and an empty body. Repeat the GET to see `404`.
6. **Try invalid data.** Repeat the POST with `"age": 10`. Expect `422`. Ask students to find the invalid field in `detail[0].loc`.

```json
{"name": "Neha Singh", "age": 21, "course": "FastAPI"}
```

## Repeat in Postman

With Uvicorn running, open Postman and use **Import** to select `Student_CRUD.postman_collection.json`. The collection uses `http://127.0.0.1:8000` as its base URL. Send requests in order. The create request saves the returned ID as `student_id` for the read, update, and delete requests.

To build a request yourself, choose the HTTP method, enter the full URL, and select **Body → raw → JSON** for POST or PUT. Paste the sample payload, click **Send**, and check the response status and body.

## Student exercise

Add a required `grade_level` integer between 1 and 12. Update the two starter records and try one valid and one invalid POST. Then check that GET returns the new field.

[FastAPI interactive docs](https://fastapi.tiangolo.com/tutorial/first-steps/#interactive-api-docs) · [Postman request bodies](https://learning.postman.com/docs/use/send-requests/create-requests/parameters/)
