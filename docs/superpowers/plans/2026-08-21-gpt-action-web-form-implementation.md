# BVR-Star GPT Action and Public Web Form Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a one-operation Custom GPT Action and a no-login Traditional Chinese web form so an ordinary ChatGPT user can enter birth date, time, and place and immediately obtain deterministic BVR-Star data for AI interpretation.

**Architecture:** The existing `ChartService` remains the sole calculation engine. A thin Action adapter converts a flat GPT-friendly request into `ChartRequest` and projects `ChartResult` into compact AI context; the same FastAPI app serves a static no-framework form, result view, privacy page, Action schema, and GPT setup assets.

**Tech Stack:** Python 3.11, FastAPI 0.141.1, Pydantic 2.13.4, package resources, semantic HTML, modern CSS, vanilla JavaScript, Render Docker deployment.

**Spec:** `docs/superpowers/specs/2026-08-21-gpt-action-web-form-design.md`

## Global Constraints

- Keep `ChartService` and every astrology calculation formula unchanged.
- The web page must not call OpenAI or require an AI API key.
- Do not add accounts, databases, cookies, analytics, local storage, or session storage.
- Birth data from the form must be sent with same-origin POST, not query parameters.
- The primary form shows only birth date, birth time, and birthplace; coordinates and IANA timezone remain optional advanced fields.
- The public Action schema exposes exactly one operation, `calculateBvrChart`.
- The Action may calculate only after sufficient birth data is available and the GPT must not recalculate returned chart facts.
- Keep Traditional Chinese as the primary interface language and `zh-TW` as the first Action output language.
- Keep the existing POST API, GET compatibility endpoint, CLI, and public schemas backward-compatible.
- Respect the user's prior request not to add a new automated test suite; use only formatting, import, JavaScript syntax, and browser smoke verification.
- Match `docs/superpowers/designs/gpt-action-web-form/form-concept.png` and `result-concept.png`: true near-white background, ink typography, restrained indigo, amber semantic accent, open editorial layout, no mystical zodiac artwork, no gradients, and no card grid.

## File Structure

- Create `src/bvr_star/api/action.py`: flat Action request model, canonical request conversion, compact response projection.
- Modify `src/bvr_star/api/app.py`: Action route and packaged HTML/CSS/JS/YAML routes.
- Create `src/bvr_star/web/index.html`: form and result semantic structure.
- Create `src/bvr_star/web/privacy.html`: public Traditional Chinese privacy policy.
- Create `src/bvr_star/web/app.css`: shared visual system and responsive states.
- Create `src/bvr_star/web/app.js`: form serialization, POST, result rendering, copy, download, errors, cold-start messaging.
- Create `gpt/action-openapi.yaml`: canonical one-operation GPT Action schema.
- Create `gpt/instructions-zh-TW.md`: Custom GPT behavior and full-reading boundaries.
- Create `gpt/conversation-starters.md`: short user-facing starters.
- Create `docs/custom-gpt-setup.md`: non-technical GPT Builder setup and link-sharing guide.
- Modify `pyproject.toml`: include web and GPT assets in the wheel.
- Modify `README.md`: expose the form, Action schema, privacy page, and Custom GPT setup path.

---

### Task 1: GPT-Friendly Action Adapter

**Files:**
- Create: `src/bvr_star/api/action.py`

**Interfaces:**
- Consumes: `BirthInput`, `ChartOptions`, `ChartRequest`, and `ChartResult`.
- Produces: `ActionChartRequest.to_chart_request() -> ChartRequest` and `compact_ai_result(result: ChartResult, extra_warnings: list[str] | None = None) -> dict[str, Any]`.

- [ ] **Step 1: Define the flat validated Action input**

Create `ActionChartRequest` with `extra="forbid"`, fields `birth_date`, `birth_time`, `birth_place`, optional coordinate triple, `time_accuracy_minutes`, optional `reference_date`, and `output_language: Literal["zh-TW"]`. Add a model validator that rejects partial coordinate triples with the exact message `latitude, longitude, and timezone must be supplied together`.

```python
class ActionChartRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    birth_date: dt.date
    birth_time: dt.time | None = None
    birth_place: str = Field(min_length=2, max_length=500)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = Field(default=None, min_length=3, max_length=100)
    time_accuracy_minutes: int = Field(default=0, ge=0, le=720)
    reference_date: dt.date | None = None
    output_language: Literal["zh-TW"] = "zh-TW"
```

- [ ] **Step 2: Convert Action input into the canonical request**

Implement `to_chart_request()` so only a complete coordinate triple is forwarded, and construct `ChartOptions` without `reference_date` when the caller omitted it so the canonical default remains active.

```python
def to_chart_request(self) -> ChartRequest:
    birth = BirthInput(
        date=self.birth_date,
        time=self.birth_time,
        place=self.birth_place,
        latitude=self.latitude,
        longitude=self.longitude,
        timezone=self.timezone,
        time_accuracy_minutes=self.time_accuracy_minutes,
    )
    option_values: dict[str, Any] = {"output_language": self.output_language}
    if self.reference_date is not None:
        option_values["reference_date"] = self.reference_date
    return ChartRequest(birth=birth, options=ChartOptions(**option_values))
```

- [ ] **Step 3: Centralize compact AI output**

Implement `compact_ai_result()` by model-dumping only `schema_version`, `mode`, `provenance`, `location`, `time`, and `llm_context`, merging extra warnings before calculation warnings, and appending the two data-handling explanations from the specification.

```python
return {
    "schema_version": data["schema_version"],
    "mode": data["mode"],
    "provenance": data["provenance"],
    "location": data["location"],
    "time": data["time"],
    "llm_context": data["llm_context"],
    "warnings": [*(extra_warnings or []), *data["warnings"]],
    "data_handling": {
        "application_storage": "BVR-Star does not persist this request or response.",
        "interpretation": "The API calculates chart data only; interpretation is produced by the user's chosen AI model.",
    },
}
```

- [ ] **Step 4: Run static checks and commit**

Run `uv run ruff check src/bvr_star/api/action.py` and `uv run python -m compileall -q src/bvr_star/api/action.py`. Commit with `feat: add Custom GPT action adapter`.

---

### Task 2: Public Action and Packaged Asset Routes

**Files:**
- Modify: `src/bvr_star/api/app.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `ActionChartRequest`, `compact_ai_result()`, existing `_allow()`, `ChartService`, and package resources.
- Produces: `POST /v1/actions/calculate`, `GET /`, `GET /privacy`, `GET /assets/app.css`, `GET /assets/app.js`, and `GET /gpt/action-openapi.yaml`.

- [ ] **Step 1: Refactor the GET compatibility projection**

Replace the hand-built dictionary in `calculate_ai_context()` with:

```python
return compact_ai_result(result, extra_warnings=["GET_QUERY_CONTAINS_BIRTH_DATA"])
```

This keeps its existing route, parameters, calculation, and privacy warning while sharing the same projection as the Action.

- [ ] **Step 2: Add the Action POST route**

Add a `POST /v1/actions/calculate` route tagged `actions`, reuse the `chart` rate bucket, call `payload.to_chart_request()`, run `service.calculate` in the thread pool, and return `compact_ai_result(result)`.

```python
@app.post("/v1/actions/calculate", tags=["actions"], operation_id="calculateBvrChart")
async def calculate_action_chart(payload: ActionChartRequest, request: Request):
    client = request.client.host if request.client else "unknown"
    if not _allow(client, "chart", int(os.getenv("BVR_CHART_RATE", "30"))):
        return _error("RATE_LIMIT_EXCEEDED", "Chart rate limit exceeded.", status=429)
    result = await run_in_threadpool(service.calculate, payload.to_chart_request())
    return compact_ai_result(result)
```

- [ ] **Step 3: Add package-resource response helpers and routes**

Use `importlib.resources.files("bvr_star")` to read UTF-8 assets, and return them with `HTMLResponse` or `Response` and exact media types. Do not mount a filesystem-relative directory.

```python
def _asset_text(*parts: str) -> str:
    return resources.files("bvr_star").joinpath(*parts).read_text(encoding="utf-8")
```

Map `web/index.html`, `web/privacy.html`, `web/app.css`, `web/app.js`, and `gpt_assets/action-openapi.yaml` to the six public routes listed above.

- [ ] **Step 4: Include all assets in built wheels**

Add exact Hatch force includes:

```toml
"src/bvr_star/web" = "bvr_star/web"
"gpt" = "bvr_star/gpt_assets"
```

- [ ] **Step 5: Run static checks and commit**

Run `uv run ruff check src/bvr_star/api/app.py src/bvr_star/api/action.py`, `uv run python -m compileall -q src/bvr_star`, and `uv run python -c 'from bvr_star.api.app import app; print(sorted(route.path for route in app.routes))'`. Confirm the new six routes appear. Commit with `feat: expose GPT Action and public assets`.

---

### Task 3: Custom GPT Asset Package

**Files:**
- Create: `gpt/action-openapi.yaml`
- Create: `gpt/instructions-zh-TW.md`
- Create: `gpt/conversation-starters.md`
- Create: `docs/custom-gpt-setup.md`

**Interfaces:**
- Consumes: `POST https://bvr-star.onrender.com/v1/actions/calculate` and `GET https://bvr-star.onrender.com/privacy`.
- Produces: a directly importable GPT Builder Action schema and copy-ready Traditional Chinese configuration.

- [ ] **Step 1: Write the minimal Action OpenAPI schema**

Use OpenAPI `3.1.0`, one HTTPS server, one path, one operationId, no authentication section, a required JSON body with `birth_date` and `birth_place`, and typed optional fields. Describe `birth_time` as optional date-range mode and require the coordinate triple together in field descriptions. Define compact success and structured error responses without enumerating the dynamic `llm_context` internals.

```yaml
openapi: 3.1.0
info:
  title: BVR-Star Chart Action
  version: 1.0.0
servers:
  - url: https://bvr-star.onrender.com
paths:
  /v1/actions/calculate:
    post:
      operationId: calculateBvrChart
```

- [ ] **Step 2: Write GPT Builder instructions**

The instruction must collect the three ordinary-language birth fields, automatically call the Action when ready, retry once only for 503/timeout, never claim success without JSON, and use only returned facts. Require the eight requested report dimensions and evidence-linked past-event verification windows, while clearly labeling astrology as traditional interpretation rather than objective diagnosis.

- [ ] **Step 3: Write conversation starters and setup guide**

Provide four starters, including `幫我算印度星盤，我會提供出生日期、時間與地點。`. The setup guide must explain copying instructions, importing `https://bvr-star.onrender.com/gpt/action-openapi.yaml`, selecting no authentication, setting the privacy URL, performing one known-data check, and choosing `知道連結者可用`. State that the final share action requires the owner's confirmation.

- [ ] **Step 4: Verify asset consistency and commit**

Search for the endpoint and operation ID with `rg -n 'v1/actions/calculate|calculateBvrChart' gpt docs/custom-gpt-setup.md`. Confirm there is exactly one Action operation. Commit with `docs: add Custom GPT configuration package`.

---

### Task 4: Initial Form and Result Markup

**Files:**
- Create: `src/bvr_star/web/index.html`
- Create: `src/bvr_star/web/privacy.html`

**Interfaces:**
- Consumes: `/assets/app.css`, `/assets/app.js`, `/v1/charts/calculate`, `/v1/prompts/full-reading`, and the approved concept images.
- Produces: semantic DOM IDs used by `app.js`: `chartForm`, `birthDate`, `birthTime`, `birthPlace`, `advancedSettings`, `timeAccuracy`, `latitude`, `longitude`, `timezone`, `referenceDate`, `submitButton`, `formStatus`, `resultSection`, `summaryList`, `warningList`, `technicalJson`, `copyButton`, `downloadButton`, `resetButton`, and `copyStatus`.

- [ ] **Step 1: Build the initial form structure**

Match the approved first-screen copy and hierarchy. Use a quiet header, editorial intro, a single form, native `<details>` for advanced fields, a three-step explainer, and the disclaimer footer. Include no login, account, cookie, horoscope wheel, badge, or secondary primary CTA.

- [ ] **Step 2: Build the result state in the same page**

Keep `resultSection` hidden initially. Add the approved heading, a `<dl>` summary rather than a card grid, copy/download/reset actions, a calculation warning band, `<details>` technical JSON, and next-step copy. The form and result states must be independently focusable through their headings.

- [ ] **Step 3: Build the privacy policy**

State the application-storage boundary, POST behavior, Render/infrastructure logs, Nominatim geocoding, third-party AI policy boundary, no AI generation on BVR-Star, and astrology disclaimer. Link back to `/`, GitHub, and `/docs`.

- [ ] **Step 4: Run HTML presence checks and commit**

Use `rg -n` to confirm every required ID exists once, every navigation URL is correct, and no script references an external CDN. Commit with `feat: add public form and privacy markup`.

---

### Task 5: Visual System and Responsive Layout

**Files:**
- Create: `src/bvr_star/web/app.css`

**Interfaces:**
- Consumes: semantic class names and IDs from Task 4.
- Produces: accessible desktop and mobile presentation faithful to `form-concept.png` and `result-concept.png`.

- [ ] **Step 1: Define design tokens and typography**

Define true-white and near-white surfaces, ink `#07142f`, indigo `#102a6b`, amber `#c98a00`, blue-gray borders, green success, semantic error, 8px spacing increments, 12/16px radii, editorial serif headings, and system sans-serif control text. Set form controls and buttons to at least `16px`.

- [ ] **Step 2: Implement the open desktop layout**

Use a two-column first viewport with a single vertical rule and a purposeful form surface, not nested cards. Implement the result as ruled definition rows and one action rail. Recreate orbital linework with subtle CSS borders and pseudo-elements only as low-contrast structural decoration.

- [ ] **Step 3: Implement interaction and accessibility states**

Add visible `:focus-visible`, hover, disabled, loading, success, warning, and error states. Respect `prefers-reduced-motion`. Ensure long location strings and JSON never force horizontal page overflow.

- [ ] **Step 4: Implement responsive behavior**

At `max-width: 760px`, collapse to one column, simplify the header links, place labels above controls, stack action buttons full-width, and keep 20px page gutters. Preserve the heading and primary form within the first mobile viewport without clipping.

- [ ] **Step 5: Check CSS and commit**

Run a brace-balance check, search for prohibited gradients with `rg -n 'gradient' src/bvr_star/web/app.css`, and confirm every color token meets its named semantic role. Commit with `style: implement BVR-Star public form design`.

---

### Task 6: Form Calculation, Copy, and Download Behavior

**Files:**
- Create: `src/bvr_star/web/app.js`

**Interfaces:**
- Consumes: DOM IDs from Task 4 and canonical `POST /v1/charts/calculate` JSON.
- Produces: `buildPayload()`, `renderResult(data)`, `copyForAi()`, `downloadJson()`, `showError()`, and reset behavior. Holds the current response only in a module variable until page unload.

- [ ] **Step 1: Serialize the form without persistent storage**

Build the canonical request with `birth`, `settings.profile = "bvr_raman_v1"`, and `options.include = ["full", "llm_context"]`. Add coordinates only when all three advanced location fields exist; otherwise show `經緯度與 IANA 時區必須一起填寫。` before any request.

- [ ] **Step 2: Submit with cold-start feedback**

Disable the button, set `aria-busy`, show `正在計算…`, and after 12 seconds change the status to the approved Render wake message. Use a 120-second `AbortController` timeout. On success, replace the form with the result and focus its heading; on failure, restore the form and show the translated error.

- [ ] **Step 3: Render complete and date-range summaries**

For complete mode, render resolved location, local datetime, timezone, ascendant, Moon, and the first active dasha lord. For date-range mode, omit ascendant and dasha and explicitly say time-sensitive fields were not calculated. Render API warnings as list items and place pretty JSON only inside the closed technical disclosure.

- [ ] **Step 4: Copy an AI-ready prompt**

Copy Traditional Chinese instructions plus `location`, `time`, `provenance`, `llm_context`, and `warnings`. The text must request personality, family, career, relationships, wealth, appearance, health, life stages, and past-event verification windows; prohibit recalculation and certainty claims. Announce success through `copyStatus` with `aria-live="polite"`.

- [ ] **Step 5: Download and reset**

Download the complete in-memory response with a Blob named `bvr-star-YYYY-MM-DD.json`, then revoke the object URL. Reset must clear the in-memory response, form fields, JSON output, warnings, copy message, and result visibility without touching browser storage.

- [ ] **Step 6: Run JavaScript syntax checks and commit**

Run `node --check src/bvr_star/web/app.js` and `rg -n 'localStorage|sessionStorage|document.cookie' src/bvr_star/web`. The search must return no storage usage. Commit with `feat: make public chart form interactive`.

---

### Task 7: Documentation, Browser Verification, and Deployment Handoff

**Files:**
- Modify: `README.md`
- Modify: `docs/api-and-ai-integration.md`
- Update: `docs/superpowers/plans/2026-08-21-gpt-action-web-form-implementation.md`

**Interfaces:**
- Consumes: every route and asset from Tasks 1-6.
- Produces: public usage links, verified local UI, a deployable commit, and the setup inputs needed for the ChatGPT GPT Builder.

- [ ] **Step 1: Update public documentation**

Put the three fastest paths first: web form `/`, Action schema `/gpt/action-openapi.yaml`, and Custom GPT setup guide. Explain that the form calculates only, does not retain application data, and leaves interpretation to the user's model. Keep the existing full API and GET fallback documentation.

- [ ] **Step 2: Run repository checks without adding a test suite**

Run:

```text
uv run ruff check src/bvr_star
uv run python -m compileall -q src/bvr_star
node --check src/bvr_star/web/app.js
uv build
```

Inspect the built wheel and confirm it contains `bvr_star/web/*` and `bvr_star/gpt_assets/*`.

- [ ] **Step 3: Verify the running local app in the in-app browser**

Start the API locally, open `/`, fill one complete known birth case, exercise calculate, copy, technical disclosure, download, and reset, then verify `/privacy` and `/gpt/action-openapi.yaml`. Check desktop and a 390px-wide mobile viewport. Do not publish or share the GPT in this step.

- [ ] **Step 4: Perform concept fidelity QA**

Capture the desktop form and result states. Use `view_image` on both approved concepts and both current screenshots in the same QA pass. Record at least five checks: exact copy, two-column/open layout, typography, true-white/indigo/amber palette, ruled result summary, action hierarchy, mobile collapse, and absence of mystical decorative art. Fix all material mismatches before continuing.

- [ ] **Step 5: Commit and push the deployable implementation**

Commit documentation and any QA fixes with `docs: publish GPT Action and form usage`, then push `main` so the connected Render service deploys automatically. Verify public `/health`, `/`, `/privacy`, Action schema, and Action calculation after deployment.

- [ ] **Step 6: Prepare the Custom GPT draft**

Use `docs/custom-gpt-setup.md`, import the public Action schema, paste the instructions and starters, and validate the known birth case. Stop immediately before changing GPT visibility to `知道連結者可用`; ask the user for action-time confirmation before publishing the share link.

## Execution Record and Fidelity Ledger

Implemented inline on `main` after the user explicitly approved the design and requested direct implementation. No new automated test suite was added; the approved static, package, endpoint, and browser checks were used.

- Copy and hierarchy: all approved headings, field labels, actions, privacy copy, and disclaimers are present; no hero eyebrow, login, pricing, testimonials, or unsupported claims were added.
- Layout: the desktop form uses the approved two-column open composition; the result uses a ruled definition list rather than a card grid; 390 px mobile collapses both into one column.
- Typography: editorial Traditional Chinese serif headings and deliberate 16 px-or-larger control typography match the concept hierarchy without browser-default control text.
- Palette and decoration: true white, ink, indigo, blue-gray rules, green success, and amber warnings match the concept; no gradients, glow, horoscope wheels, crystals, or mystical clip art are present.
- Action hierarchy: `開始計算` and `複製給 AI` are the only solid primary actions; JSON download is outlined and reset remains a text action.
- Interaction: complete calculation, compact Action calculation, copy-to-clipboard, JSON download feedback, technical disclosure, reset, cold-start messaging, privacy page, desktop layout, and mobile layout were exercised in the browser.
- Material fixes during QA: reduced the desktop heading to preserve the approved two-line break; prevented mobile brand wrapping; corrected reset focus; removed a skip-link overlay that the browser focused over the brand; delayed Blob URL revocation and added visible download feedback; added a source-tree fallback for the packaged Action YAML.
- Above-the-fold copy diff: no unapproved visible copy remains. The implementation uses simpler code-native linework than the concept illustration, which is an intentional no-external-asset interpretation consistent with the approved design constraints.
