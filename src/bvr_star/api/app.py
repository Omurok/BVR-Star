"""Public, stateless BVR-Star HTTP API."""

from __future__ import annotations

import os
import time
import uuid
from collections import defaultdict, deque
from datetime import date
from datetime import time as civil_time
from threading import Lock
from typing import Annotated

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from starlette.concurrency import run_in_threadpool

from bvr_star.config import public_config
from bvr_star.location.nominatim import NominatimGeocoder
from bvr_star.location.resolve import resolve_location
from bvr_star.models.errors import BVRStarError
from bvr_star.models.request import BirthInput, ChartOptions, ChartRequest
from bvr_star.prompting import render_prompt
from bvr_star.service import ChartService
from bvr_star.version import __version__

app = FastAPI(
    title="BVR-Star API", version=__version__,
    description="Raman sidereal Jyotish calculation API for AI-assisted, evidence-linked readings.",
    contact={"name": "BVR-Star", "url": "https://github.com/Omurok/BVR-Star"},
    license_info={"name": "AGPL-3.0-only", "identifier": "AGPL-3.0-only"},
)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["GET", "POST"],
    allow_headers=["Content-Type", "Accept"], allow_credentials=False,
)
service = ChartService()
geocoder = NominatimGeocoder()
_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_bucket_lock = Lock()


def _error(code: str, message: str, details=None, status: int = 422, request_id: str | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details or {}, "request_id": request_id}})


def _allow(client: str, kind: str, limit: int) -> bool:
    now = time.monotonic()
    key = (client, kind)
    with _bucket_lock:
        bucket = _buckets[key]
        while bucket and bucket[0] <= now - 60:
            bucket.popleft()
        if len(bucket) >= limit:
            return False
        bucket.append(now)
    return True


@app.middleware("http")
async def request_safety(request: Request, call_next):
    request_id = uuid.uuid4().hex
    declared = request.headers.get("content-length")
    maximum = int(os.getenv("BVR_MAX_BODY_BYTES", "16384"))
    if declared and int(declared) > maximum:
        return _error("REQUEST_TOO_LARGE", "Request body exceeds 16 KiB.", status=413, request_id=request_id)
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["Cache-Control"] = "no-store"
    return response


@app.exception_handler(BVRStarError)
async def bvr_error_handler(request: Request, exc: BVRStarError):
    status = 503 if exc.code in {"GEOCODER_UNAVAILABLE", "EPHEMERIS_UNAVAILABLE"} else 422
    return _error(exc.code, exc.message, exc.details, status, request.headers.get("X-Request-ID"))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return _error("INPUT_VALIDATION_ERROR", "The request does not match the public schema.", {"errors": exc.errors()}, 422)


@app.get("/health", tags=["service"])
def health():
    ready = service.ephemeris.files_ready()
    content = {"status": "ok" if ready else "not_ready", "version": __version__, "ephemeris_files_ready": ready}
    return JSONResponse(status_code=200 if ready else 503, content=content)


@app.get("/v1/config", tags=["service"])
def config():
    return public_config()


@app.post("/v1/locations/resolve", tags=["locations"])
async def resolve_birth_location(birth: BirthInput, request: Request):
    client = request.client.host if request.client else "unknown"
    if not _allow(client, "geocode", int(os.getenv("BVR_GEOCODE_RATE", "5"))):
        return _error("RATE_LIMIT_EXCEEDED", "Location rate limit exceeded.", status=429)
    return await run_in_threadpool(resolve_location, birth, geocoder)


@app.post("/v1/charts/calculate", tags=["charts"])
async def calculate_chart(payload: ChartRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    if not _allow(client, "chart", int(os.getenv("BVR_CHART_RATE", "30"))):
        return _error("RATE_LIMIT_EXCEEDED", "Chart rate limit exceeded.", status=429)
    result = await run_in_threadpool(service.calculate, payload)
    return result.model_dump(mode="json")


@app.get(
    "/v1/charts/ai-context",
    tags=["charts"],
    summary="Calculate an AI-readable chart through a GET-only web tool",
    description=(
        "Compatibility endpoint for AI web readers that cannot send HTTP POST. "
        "Birth data appears in the URL and may be retained by browsers or network infrastructure; "
        "use the POST endpoint when privacy matters."
    ),
)
async def calculate_ai_context(
    request: Request,
    birth_date: Annotated[
        date,
        Query(description="Local civil birth date in YYYY-MM-DD format."),
    ],
    birth_time: Annotated[
        civil_time | None,
        Query(description="Local civil birth time in HH:MM or HH:MM:SS format. Omit for date-range mode."),
    ] = None,
    place: Annotated[
        str | None,
        Query(
            min_length=2,
            max_length=500,
            description="Precise birthplace, preferably district, city, and country.",
        ),
    ] = None,
    latitude: Annotated[float | None, Query(ge=-90, le=90)] = None,
    longitude: Annotated[float | None, Query(ge=-180, le=180)] = None,
    timezone: Annotated[
        str | None,
        Query(description="IANA timezone; required together with latitude and longitude."),
    ] = None,
    time_accuracy_minutes: Annotated[int, Query(ge=0, le=720)] = 0,
    reference_date: Annotated[
        date | None,
        Query(description="Date used to select active dashas; defaults to the service date."),
    ] = None,
):
    client = request.client.host if request.client else "unknown"
    if not _allow(client, "chart", int(os.getenv("BVR_CHART_RATE", "30"))):
        return _error("RATE_LIMIT_EXCEEDED", "Chart rate limit exceeded.", status=429)
    birth = BirthInput(
        date=birth_date,
        time=birth_time,
        place=place,
        latitude=latitude,
        longitude=longitude,
        timezone=timezone,
        time_accuracy_minutes=time_accuracy_minutes,
    )
    options = (
        ChartOptions(reference_date=reference_date)
        if reference_date is not None
        else ChartOptions()
    )
    payload = ChartRequest(birth=birth, options=options)
    result = await run_in_threadpool(service.calculate, payload)
    data = result.model_dump(mode="json")
    return {
        "schema_version": data["schema_version"],
        "mode": data["mode"],
        "provenance": data["provenance"],
        "location": data["location"],
        "time": data["time"],
        "llm_context": data["llm_context"],
        "warnings": [
            "GET_QUERY_CONTAINS_BIRTH_DATA",
            *data["warnings"],
        ],
        "data_handling": {
            "application_storage": "BVR-Star does not persist the request or response.",
            "url_privacy": (
                "GET query parameters can remain in browser history and network infrastructure logs. "
                "Use POST /v1/charts/calculate when privacy matters."
            ),
        },
    }


@app.get("/v1/prompts/full-reading", response_class=PlainTextResponse, tags=["prompts"])
def full_reading_prompt(language: str = Query(default="zh-TW", pattern="^(zh-TW|en)$")):
    return render_prompt(language)
