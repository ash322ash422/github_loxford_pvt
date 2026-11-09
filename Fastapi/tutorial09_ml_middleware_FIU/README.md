# FastAPI classroom project — Middleware, exceptions, and CORS for an ML API

**Class time** 25–30 minutes. The API predicts the sentiment of a course review. It uses a keyword rule as a stand-in for an ML model. Version `v1` works and version `v2` simulates a temporary model outage.

## 1. What is middleware?

**Middleware is shared code that sits around your API routes.** It can inspect or modify an incoming request, pass it along, and inspect or modify the response on its way back. It can also respond early, as CORS middleware does for a browser preflight.

In this app, the timing middleware starts a timer and assigns a request ID before calling `await call_next(request)`. That call hands control to FastAPI for routing, validation, and prediction. When the response comes back, the middleware adds `X-Request-ID` and `X-Process-Time-Ms`. This gives every prediction request the same tracing behavior without putting timing code in each endpoint.

**Teaching prompt** Ask students which lines run before the prediction and which run after it. The timer measures the app's request handling up to the response object, including validation and routing. Measuring the model alone would require a timer around the prediction function.

| Component | Responsibility in this app |
| --- | --- |
| Timing middleware | Wraps prediction requests and adds tracing headers to success and handled error responses |
| Prediction route | Receives input validated by FastAPI and invokes the sentiment model stand-in |
| Custom exception handler | Turns `ModelUnavailableError` into a structured `503` response |
| CORS middleware | Applies the browser origin policy and handles preflight requests |

## 2. Start the API on Windows

Open PowerShell in this folder with Python 3.11 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Open [Swagger UI](http://127.0.0.1:8000/docs), expand `POST /predict`, and click **Try it out**. Send this body.

```json
{"text": "I love this course", "model_version": "v1"}
```

| Try | Expected response |
| --- | --- |
| Use the body above | `200 OK` with label `positive` and model version `v1` |
| Change the version to `v2` | `503 Service Unavailable` with `error: model_unavailable` and a request ID |
| Set `text` to an empty string | `422` from FastAPI's input validation |

Check the response headers for each request. On a `503`, the request ID in the JSON body matches the header. The model function raises a Python exception. The registered handler decides how to represent that failure in HTTP, and the timing middleware still sees the resulting response.

## 3. See CORS in a browser

An **origin** is the combination of scheme, host, and port. A page at `http://127.0.0.1:5500` and an API at `http://127.0.0.1:8000` have different origins. CORS tells the browser which origins can read cross-origin responses and whether requests that require a preflight can proceed. Authentication controls who can use an API separately from CORS.

1. Leave Uvicorn running. In a second PowerShell window in this folder, run `python -m http.server 5500 --bind 127.0.0.1`.
2. Open [the allowed client page](http://127.0.0.1:5500/client.html). Open browser DevTools → **Network**, then click **Predict**. On the first JSON POST, look for the browser's `OPTIONS` preflight followed by the actual `POST`. The page can read the two custom headers because the API lists them in `expose_headers`.
3. Select model `v2` and click **Predict** again. The allowed page can read the `503` response and its request ID.
4. In another terminal, run `python -m http.server 5501 --bind 127.0.0.1`. Open [the disallowed client page](http://127.0.0.1:5501/client.html) and click **Predict**. For this JSON request, the browser rejects the preflight and skips the POST. Inspect the `OPTIONS` response in DevTools.
5. Compare the results. Swagger UI is served by the API itself on port `8000`, so testing from Swagger uses the same origin. Use the exact `127.0.0.1` addresses above because CORS matches the host as well as the port.

CORS is the outer middleware in this example. It can answer a preflight before the timing middleware or prediction route runs.

## Student exercise

Allow the page on port `5501` by adding its full origin to `allow_origins`. Save the file, wait for Uvicorn to reload, then retry the prediction and explain what changed in the Network tab.

[FastAPI middleware](https://fastapi.tiangolo.com/tutorial/middleware/) · [Exception handlers](https://fastapi.tiangolo.com/tutorial/handling-errors/) · [CORS](https://fastapi.tiangolo.com/tutorial/cors/)
