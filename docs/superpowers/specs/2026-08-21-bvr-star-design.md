# BVR-Star Design Specification

Date: 2026-08-21  
Status: awaiting user review  
Repository target: `https://github.com/Omurok/BVR-Star`

## 1. Purpose

BVR-Star is an open-source, deterministic Vedic astrology calculation engine. It accepts a birth date, birth time, and birthplace, normalizes the civil time and location, calculates a sidereal chart with explicit conventions, and returns traceable JSON for human or language-model interpretation.

The project separates three concerns:

1. Astronomical facts and mathematical transformations produced by code.
2. Versioned Jyotish rules produced by a traceable rule engine.
3. Narrative interpretation produced outside the calculation engine by an AI or human astrologer.

The primary default profile follows the conventions used in the referenced B. V. Raman-style analysis:

- sidereal zodiac;
- Raman ayanamsha;
- geocentric planetary positions;
- mean lunar nodes;
- Parashari whole-sign houses and graha aspects;
- Vimshottari dasha.

The system does not claim that astrological interpretations are scientifically validated. It exposes the calculation convention and evidence for every derived rule so an interpretation can distinguish calculation from inference.

## 2. Goals

Version 1 must provide:

- a reusable Python library;
- a command-line interface that writes machine-readable JSON;
- a FastAPI HTTP service with a published OpenAPI schema;
- a Docker image and Render deployment definition;
- deterministic chart calculations with versioned configuration;
- a compact `llm_context` projection optimized for language-model use;
- Traditional Chinese and English AI prompt templates;
- automated tests, including the agreed 1983 Kaohsiung reference chart;
- public AGPL-3.0 source code at `Omurok/BVR-Star`;
- a public, no-storage calculation API.

## 3. Non-goals for Version 1

Version 1 will not:

- generate a supposedly objective life diagnosis inside the API;
- claim that a predicted event certainly occurred;
- perform birth-time rectification;
- infer a missing birth time from prior conversation data;
- include Shadbala, Ashtakavarga, Jaimini dasha, KP astrology, or Varshaphala;
- provide user accounts, saved charts, billing, or a chart database;
- promise an exhaustive catalog of every yoga found across all classical and modern sources;
- guarantee low-latency availability on Render's free tier.

These features can be added through separately versioned rule modules after the core chart contract is stable.

## 4. Users and Main Flows

### 4.1 AI-assisted reading

An AI receives birth data, calls the public HTTP API or local CLI, receives a complete chart response, and follows a repository prompt to write a report. The AI treats `facts`, `rules`, `warnings`, and `sensitivity` as separate sources and never recalculates a degree from prose.

### 4.2 Local calculation

A user installs the Python package and runs:

```text
bvr-star calculate --input birth.json --output chart.json
```

The same calculation is available as a Python function:

```text
calculate_chart(request: ChartRequest) -> ChartResponse
```

### 4.3 Public API calculation

A client sends a `ChartRequest` to `POST /v1/charts/calculate` and receives the same `ChartResponse` contract used by the Python library and CLI.

## 5. Architecture

The project uses one Python codebase with adapters around a pure calculation core:

```text
Birth input
  -> location resolution
  -> historical civil-time normalization
  -> Julian day and Swiss Ephemeris adapter
  -> sidereal chart core
  -> Jyotish derivation modules
  -> full ChartResponse + compact llm_context
  -> Python / CLI / HTTP adapters
```

The core must not import FastAPI, command-line parsing, Render, or prompt code. Network-dependent geocoding is behind an interface so the calculation core can be tested offline and exact coordinates can bypass geocoding.

### 5.1 Module boundaries

- `models`: validated request, response, warning, provenance, and error models.
- `location`: geocoder interface, provider implementation, coordinate validation, and timezone lookup.
- `time`: IANA timezone handling, ambiguous/nonexistent local time detection, UTC conversion, and Julian day preparation.
- `ephemeris`: the only module that calls Swiss Ephemeris.
- `chart`: signs, houses, ascendant, nakshatra, pada, and planetary placement.
- `varga`: divisional chart calculations under a named rule-set version.
- `dasha`: Vimshottari balance and nested period calculation.
- `rules`: dignity, combustion, conjunction, Parashari aspect, lordship, and yoga evidence.
- `sensitivity`: recalculation at birth-time uncertainty boundaries and structural comparison.
- `llm`: token-efficient projection of calculation output; no narrative predictions.
- `cli`: local command-line adapter.
- `api`: FastAPI routes, HTTP error mapping, rate limiting, and OpenAPI metadata.

Each module has one public boundary and can be tested without reading another module's internals.

## 6. Input Contract

The canonical JSON request is:

```json
{
  "birth": {
    "date": "1983-06-15",
    "time": "03:58:00",
    "place": "Taiwan, Kaohsiung City, Lingya District",
    "latitude": null,
    "longitude": null,
    "timezone": null,
    "fold": null,
    "time_accuracy_minutes": 1
  },
  "settings": {
    "profile": "bvr_raman_v1",
    "ayanamsha": "raman",
    "node_type": "mean",
    "house_system": "whole_sign",
    "aspect_system": "parasari",
    "dasha_system": "vimshottari"
  },
  "options": {
    "include": ["full", "llm_context"],
    "dasha_depth": 3,
    "reference_date": "2026-08-21",
    "output_language": "zh-TW"
  }
}
```

Validation rules:

- `date` is required.
- Version 1 accepts civil dates from 1900-01-01 through 2099-12-31 and returns `DATE_OUT_OF_RANGE` otherwise.
- `time` may be absent only for date-range mode.
- A complete calculation requires either `place`, or all of `latitude`, `longitude`, and `timezone`.
- Explicit coordinates and timezone take precedence over the address, and the response records that choice.
- Latitude must be between -90 and 90; longitude must be between -180 and 180.
- `time_accuracy_minutes` is zero or greater and is used only when a birth time is supplied.
- `fold` is absent for ordinary local times and is `0` or `1` only when selecting one side of an overlapping daylight-saving transition.
- `reference_date` defaults to the request date in UTC and selects the active dasha paths included in `llm_context`; it never changes the natal chart.
- Unknown calculation settings are rejected rather than silently defaulted.

## 7. Location and Time Normalization

### 7.1 Address mode

The default low-volume provider is OpenStreetMap Nominatim with an identifying user-agent, request throttling of at most one geocoding request per second per service instance, and a bounded cache. The provider is replaceable through configuration.

If an address resolves to materially different candidate locations, the API returns `LOCATION_AMBIGUOUS` and the candidates. The client resubmits explicit coordinates and timezone or a more specific address. The service does not hide a low-confidence location choice.

### 7.2 Coordinate mode

The service derives an IANA timezone identifier from the coordinates unless the request supplies one. Historical UTC offset and daylight-saving behavior come from the IANA tz database through Python `zoneinfo` and the pinned `tzdata` package.

### 7.3 Civil-time edge cases

- A nonexistent local time returns `LOCAL_TIME_NONEXISTENT`.
- An overlapping local time returns `LOCAL_TIME_AMBIGUOUS` and requires an explicit `fold` choice in a follow-up request.
- The response records local time, IANA timezone, UTC offset, UTC instant, Julian day, location source, and data versions.

### 7.4 Missing birth time

When `time` is absent, the response mode is `date_range`. The engine calculates the start and end of the local civil day, reports planetary longitude ranges and any sign or nakshatra transitions, and omits ascendant, houses, divisional ascendants, dasha balance, and other time-sensitive conclusions. It does not invent a noon birth time.

## 8. Calculation Conventions

Every response contains the resolved convention profile. The `bvr_raman_v1` profile fixes:

- Swiss Ephemeris sidereal flag;
- Raman ayanamsha (`SE_SIDM_RAMAN`);
- geocentric ecliptic longitude of date;
- mean lunar node for Rahu, with Ketu exactly opposite;
- whole-sign houses from the sidereal ascendant sign;
- traditional Parashari graha aspects;
- Vimshottari dasha using 365.25 days per dasha year;
- divisional formulas registered as `parasari_shodashavarga_v1`.

The response records actual Swiss Ephemeris return flags. A fallback from Swiss ephemeris files to another calculation source is never silent: provenance reports the source and a warning is returned. The Docker deployment contains the pinned ephemeris data needed by supported dates.

### 8.1 Calculated bodies and angles

Version 1 calculates:

- Sun, Moon, Mercury, Venus, Mars, Jupiter, and Saturn;
- mean Rahu and derived Ketu;
- ascendant and MC when time is known.

For each body, the response includes sidereal longitude, sign, sign degree, nakshatra, pada, longitude speed, retrograde state, house, and provenance.

### 8.2 Divisional charts

Version 1 includes D1 and the traditional Shodashavarga set:

- D2, D3, D4, D7, D9, D10, D12;
- D16, D20, D24, D27, D30;
- D40, D45, D60.

Each varga response records the formula rule-set ID, planetary placements, divisional ascendant when time is known, sign lords, and boundary distance. A time-accuracy interval that crosses a divisional boundary creates a sensitivity warning rather than one unqualified placement.

### 8.3 Vimshottari dasha

The engine derives the birth mahadasha from the Moon's nakshatra, calculates the remaining birth balance, and expands periods to the requested depth. Version 1 accepts depths 1 through 3: mahadasha, antardasha, and pratyantardasha. Each period includes its lord, UTC and local calendar boundaries, parent path, and calculation convention.

### 8.4 Rule evidence

Version 1 derives:

- sign and house lordship;
- own sign, exaltation, debilitation, moolatrikona, and configurable friendship dignity;
- direct and retrograde state;
- combustion by a versioned threshold table;
- conjunctions with exact angular separation;
- Parashari aspects with source, target, aspect type, and degree evidence;
- common named yogas through versioned rule IDs, initially including Parivartana, Gaja Kesari, Budha Aditya, Chandra Mangala, Neecha Bhanga, common Dhana/Raja patterns, and Viparita Raja patterns.

Every derived rule includes `rule_id`, input evidence, result, strength qualifiers, source note, and rule-set version. The API does not convert a triggered rule directly into a guaranteed life event.

## 9. Output Contract

The response has stable top-level sections:

```json
{
  "schema_version": "1.0.0",
  "request_id": "uuid",
  "status": "complete",
  "normalized_birth": {},
  "settings": {},
  "provenance": {},
  "angles": {},
  "houses": [],
  "planets": {},
  "vargas": {},
  "dashas": {},
  "rules": [],
  "sensitivity": {},
  "warnings": [],
  "llm_context": {}
}
```

`llm_context` is generated from the same typed response, not by a second calculation. It includes:

- compact placements and lordships;
- strongest exact conjunctions and aspects;
- dignity and combustion qualifiers;
- important varga confirmations and contradictions;
- active dasha periods for a caller-supplied reference date;
- sensitivity and uncertainty statements;
- evidence IDs that point back to the full response.

Numbers remain numeric. Human-readable labels are additional fields and never replace exact values.

## 10. HTTP API

The public API is versioned under `/v1`:

- `GET /health`: process and ephemeris readiness.
- `GET /v1/config`: supported profiles, settings, versions, and limits.
- `POST /v1/locations/resolve`: low-volume address resolution.
- `POST /v1/charts/calculate`: complete or date-range calculation.
- `GET /v1/prompts/full-reading?language=zh-TW`: versioned AI prompt template.
- `GET /docs`: interactive FastAPI documentation.
- `GET /openapi.json`: machine-readable tool schema.

Successful chart calculations return HTTP 200. Validation and ambiguity errors use HTTP 422 with a stable structured error body. Rate limits use HTTP 429. Provider or ephemeris readiness failures use HTTP 503. Unexpected errors return an opaque request ID and do not expose stack traces.

The request body limit is 16 KiB. Version 1 has no authentication, accepts no file uploads, and performs no arbitrary URL fetches. Default in-memory per-IP limits are 30 chart calculations per minute and 5 address resolutions per minute on a single free-tier instance. Limit values are exposed by `/v1/config` and may be reduced through deployment configuration.

## 11. CLI and Python API

The CLI provides:

```text
bvr-star calculate --input INPUT.json [--output OUTPUT.json]
bvr-star resolve-location "ADDRESS"
bvr-star config
bvr-star prompt --language zh-TW
bvr-star serve --host 127.0.0.1 --port 8000
```

JSON is written to standard output unless `--output` is provided. Diagnostics go to standard error, so an AI can parse standard output without stripping log text. Errors use nonzero exit codes and the same stable error model as HTTP.

The Python API accepts and returns the canonical typed models. Adapters do not maintain separate calculation result types.

## 12. AI Prompt Package

The repository includes concise prompts in `prompts/zh-TW/` and `prompts/en/`. The Traditional Chinese full-reading prompt instructs an AI to:

1. Collect birth date, local birth time, birthplace, and stated time accuracy.
2. Call the public API or local CLI before interpreting.
3. Use calculated fields and evidence IDs as the only chart source.
4. Separate `計算事實`, `傳統占星規則`, and `綜合解讀`.
5. Cover personality, family, career, relationships, wealth, appearance, and health as traditional interpretations.
6. Present past-event material as dated hypotheses for user verification.
7. Surface all time, location, varga, and rule warnings near affected claims.
8. Refer to the person as `命主` unless the user assigns another role.
9. Treat medical, financial, and relationship material as reflective guidance rather than diagnosis or certainty.

The prompt contains positive ordered steps and completion criteria. Calculation conventions live in the API response and calculation documentation as the single source of truth; the prompt points to those fields instead of duplicating tables that can become stale.

README examples include:

- a copyable Chinese prompt using the public endpoint;
- a local CLI prompt for Codex or another coding agent;
- a curl example;
- a Python example;
- instructions for importing `openapi.json` into an AI tool/action system.

## 13. Privacy, Safety, and Operations

- The API does not persist requests or responses.
- Application logs contain request IDs, status, latency, and error category, not request bodies or birth data.
- The public API returns astrology calculations and rule evidence, not medical or financial diagnoses.
- CORS permits public non-credentialed use; the service does not accept cookies.
- Geocoder calls use strict throttling and a replaceable provider.
- Dependency versions and downloaded ephemeris artifacts are pinned and checksum-verified.
- `/health` verifies that the required ephemeris source is ready before reporting healthy.

## 14. Repository and Documentation

The intended repository layout is:

```text
src/bvr_star/
tests/
prompts/zh-TW/
prompts/en/
docs/
examples/
scripts/
Dockerfile
render.yaml
openapi.json
pyproject.toml
README.md
LICENSE
SECURITY.md
CONTRIBUTING.md
```

Documentation includes:

- quick start and public API URL;
- calculation conventions and supported date range;
- request and response schemas;
- rule and evidence catalog;
- address, timezone, and birth-time accuracy behavior;
- AI integration guide;
- deployment and self-hosting guide;
- Swiss Ephemeris and third-party license notices.

The project uses AGPL-3.0 because Swiss Ephemeris is offered under AGPL or a professional license. A closed-source deployment must obtain and comply with the appropriate Swiss Ephemeris professional license.

## 15. Deployment

The first public deployment uses a Docker-based Render web service connected to `Omurok/BVR-Star`. `render.yaml` requests the free plan, binds the application to `0.0.0.0:$PORT`, checks `/health`, and performs automatic deployment from the main branch.

The expected service name is `bvr-star`; the actual `onrender.com` URL is recorded in README and prompt files only after Render assigns it. The design does not assume that a particular subdomain is available.

The free service may sleep after inactivity and have a cold start. README and API integration guidance state this constraint. Moving to an always-on paid instance is a separate billing decision.

Deployment requires the user's Render account to connect the public GitHub repository. If the current environment lacks an authenticated Render session, the implementation stops at the smallest required authorization step and asks the user to complete it.

## 16. Testing Strategy

Implementation follows red-green-refactor. Every nontrivial public function begins with a failing behavior test.

Test groups include:

- literal unit fixtures for signs, nakshatras, padas, wraparound, vargas, aspects, combustion, and dasha boundaries;
- time tests for historical offsets, nonexistent times, overlapping times, and UTC conversion;
- offline location tests using recorded complete provider responses rather than live mocks with partial shapes;
- ephemeris adapter tests against pinned official `swetest` fixtures;
- a golden reference chart for 1983-06-15 03:58:00, Asia/Taipei, Lingya District coordinates;
- sensitivity tests that cross an ascendant or divisional boundary;
- CLI integration tests that parse standard output as the canonical schema;
- API tests for success, partial charts, ambiguity, validation, throttling, and unavailable dependencies;
- Docker smoke tests that start the image, wait for readiness, and call `/health` and `/v1/charts/calculate`.

Expected astronomical values are literal fixtures captured from the pinned official tool, not values recomputed by helpers under test. Tolerances are documented per field. The previously discussed chart is a regression target, not the sole astronomical oracle.

GitHub Actions must run tests, static analysis, packaging, and Docker build on pushes and pull requests.

## 17. Acceptance Criteria

Version 1 is accepted only when all of the following are evidenced:

1. One canonical request produces schema-valid, deterministic output through Python, CLI, and HTTP.
2. The reference chart agrees with pinned `swetest` fixtures within documented tolerances.
3. Raman ayanamsha, mean nodes, whole-sign houses, nakshatra/pada, the listed vargas, three dasha depths, rule evidence, and sensitivity output are covered by tests.
4. Missing-time mode contains ranges and excludes time-sensitive fields without inventing a birth time.
5. Ambiguous address and civil-time inputs produce actionable structured errors.
6. The AI prompt calls the calculation interface first and can produce a report without recalculating chart values.
7. The Docker image starts from a clean build and passes live health and chart smoke tests.
8. GitHub Actions passes on the public `Omurok/BVR-Star` repository.
9. The public Render URL returns a healthy response and a successful reference calculation.
10. README records the live URL, cold-start limitation, calculation profile, privacy behavior, and licensing.

## 18. External References

- Swiss Ephemeris programming interface: <https://www.astro.com/swisseph/swephprg.htm>
- Swiss Ephemeris licensing: <https://www.astro.com/swisseph/sweph_e.htm>
- IANA time zone database: <https://www.iana.org/time-zones/tz-link>
- Nominatim usage policy: <https://operations.osmfoundation.org/policies/nominatim/>
- Render web services: <https://render.com/docs/web-services>
- Render free-service limitations: <https://render.com/docs/free>
