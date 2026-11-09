"""Run: python -m uvicorn main2:app --reload

Open http://127.0.0.1:8000/docs and try both dashboard routes.
Each route loads the same two pieces of data from simulated services.
"""

import asyncio
from time import perf_counter

from fastapi import FastAPI

app = FastAPI(title="FastAPI Async Demo")


async def fetch_attendance() -> int:
    """Simulate waiting one second for an attendance service."""
    await asyncio.sleep(1)
    return 24


async def fetch_submissions() -> int:
    """Simulate waiting one second for an assignment service."""
    await asyncio.sleep(1)
    return 18


@app.get("/dashboard/sequential")
async def dashboard_sequential() -> dict[str, int | float]:
    """Wait for each service in turn. Expect about two seconds."""
    started = perf_counter()
    students_present = await fetch_attendance()
    assignments_submitted = await fetch_submissions()
    return {
        "students_present": students_present,
        "assignments_submitted": assignments_submitted,
        "elapsed_seconds": round(perf_counter() - started, 2),
    }


@app.get("/dashboard/concurrent")
async def dashboard_concurrent() -> dict[str, int | float]:
    """Overlap two independent service calls. Expect about one second."""
    started = perf_counter()

    # Why async helps here: both calls spend most of their time waiting for I/O.
    # gather starts them together. Each await lets the event loop run other work
    # while a service is pending, including serving other incoming requests.
    students_present, assignments_submitted = await asyncio.gather(
        fetch_attendance(), fetch_submissions()
    )
    return {
        "students_present": students_present,
        "assignments_submitted": assignments_submitted,
        "elapsed_seconds": round(perf_counter() - started, 2),
    }
