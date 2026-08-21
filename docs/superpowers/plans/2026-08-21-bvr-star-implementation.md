# BVR-Star 實作計畫

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**目標：** 建立可重複驗算的 Raman 印度星盤 Python 核心、CLI、FastAPI、AI Prompt、Docker 映像及公開 Render API，並發布至 `Omurok/BVR-Star`。

**架構：** 單一 Python 計算核心先將地址與民用時間標準化，再透過唯一的 Swiss Ephemeris 介面取得天文資料，最後以純函式完成 D1、分盤、大運、規則證據、敏感度與 `llm_context`。CLI 與 HTTP 只作為同一個 `ChartService` 的介面；公開部署不保存出生資料。

**技術組合：** CPython 3.11、uv、Pydantic 2.13.4、pyswisseph 2.10.3.2、tzdata 2026.3、timezonefinder 8.2.5、geopy 2.5.0、Typer 0.27.1、FastAPI 0.141.1、Uvicorn 0.52.4、pytest、Ruff、mypy、Docker、GitHub Actions、Render。

**規格：** `docs/superpowers/specs/2026-08-21-bvr-star-design.md`

## 全域限制

- 專案執行版本固定為 CPython `>=3.11,<3.12`；本機由 uv 安裝，不使用系統 Python 3.14。
- 預設設定檔固定為 `bvr_raman_v1`：恆星黃道、Raman Ayanāṃśa、平均交點、整宮制、Parāśari 相位、365.25 日 Vimshottari 年。
- 支援出生日期固定為 1900-01-01 至 2099-12-31。
- 同一個 `ChartRequest` 必須經 Python、CLI 與 HTTP 取得同一份 `ChartResponse`。
- 計算核心不得依賴 FastAPI、Typer、Render 或 Prompt 文件。
- 所有非平凡公開函式遵循 Red-Green-Refactor；先執行失敗測試，再寫最小實作。
- 測試預期值使用人工常值或固定版本官方 `swetest` 輸出，不以受測函式計算期望值。
- API 不保存請求、回應或出生資料；日誌不記錄 Request Body。
- 原始碼與網路服務使用 AGPL-3.0；第三方資料與套件授權記錄於 `THIRD_PARTY_NOTICES.md`。
- 星曆檔固定從官方 `aloistr/swisseph` 儲存庫下載並驗證 SHA-256：`sepl_18.se1` 為 `ca1393ceab3a44fbc895887cf789c68819ae6a1cbc9b22225872dbe4ccd99a66`，`semo_18.se1` 為 `1ca07bd67c24374d77226180c20a4f9996cba013697894810518e7eb582ca4f7`。

---

## 第一階段：確定性計算核心

### Task 1：專案骨架、錯誤與標準輸入模型

**檔案：**

- 建立：`.python-version`
- 建立：`.gitignore`
- 建立：`pyproject.toml`
- 建立：`src/bvr_star/__init__.py`
- 建立：`src/bvr_star/version.py`
- 建立：`src/bvr_star/models/__init__.py`
- 建立：`src/bvr_star/models/request.py`
- 建立：`src/bvr_star/models/errors.py`
- 測試：`tests/models/test_request.py`
- 測試：`tests/models/test_errors.py`

**介面：**

- 產生：`BirthInput`、`ChartSettings`、`ChartOptions`、`ChartRequest`。
- 產生：`BVRStarError(code: str, message: str, details: dict)`。
- 後續任務只接受上述 Pydantic 模型，不接受未驗證的任意字典。

- [ ] **Step 1：建立只含工具與相依套件的專案設定**

`pyproject.toml` 指定：

```toml
[project]
name = "bvr-star"
version = "0.1.0"
requires-python = ">=3.11,<3.12"
dependencies = [
  "pydantic==2.13.4",
  "pyswisseph==2.10.3.2",
  "tzdata==2026.3",
  "timezonefinder==8.2.5",
  "geopy==2.5.0",
  "typer==0.27.1",
  "fastapi==0.141.1",
  "uvicorn[standard]==0.52.4",
]

[dependency-groups]
dev = ["httpx", "mypy", "pytest", "pytest-cov", "ruff"]

[project.scripts]
bvr-star = "bvr_star.cli:app"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/bvr_star"]

[tool.hatch.build.targets.wheel.force-include]
"prompts" = "bvr_star/prompt_templates"

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-ra --strict-markers"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
strict = true
```

`.python-version` 寫入 `3.11`；`.gitignore` 排除 `.venv/`、`__pycache__/`、`.pytest_cache/`、`.mypy_cache/`、`.ruff_cache/`、`dist/` 與 `ephe/`。

- [ ] **Step 2：同步 Python 3.11 與鎖定檔**

執行：`uv python install 3.11 && uv sync --all-groups`

預期：建立 `.venv` 與 `uv.lock`，`uv run python --version` 顯示 Python 3.11.x。

- [ ] **Step 3：先寫請求驗證失敗測試**

```python
from datetime import date, time

import pytest
from pydantic import ValidationError

from bvr_star.models.request import BirthInput, ChartRequest


def test_complete_birth_requires_place_or_coordinates_and_timezone() -> None:
    with pytest.raises(ValidationError, match="place or latitude"):
        ChartRequest(birth=BirthInput(date=date(1983, 6, 15), time=time(3, 58)))


def test_partial_coordinates_are_rejected() -> None:
    with pytest.raises(ValidationError, match="latitude, longitude, and timezone"):
        BirthInput(
            date=date(1983, 6, 15),
            time=time(3, 58),
            latitude=22.6265,
            longitude=120.312,
        )


def test_date_outside_supported_range_is_rejected() -> None:
    with pytest.raises(ValidationError, match="1900-01-01"):
        BirthInput(date=date(1899, 12, 31), place="Kaohsiung, Taiwan")
```

- [ ] **Step 4：執行測試確認為 Red**

執行：`uv run pytest tests/models/test_request.py -v`

預期：因 `bvr_star.models.request` 尚不存在而 FAIL；錯誤原因是待建功能，不是測試語法錯誤。

- [ ] **Step 5：實作最小請求模型與穩定錯誤類型**

`BirthInput` 使用下列公開欄位與驗證：

```python
class BirthInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    date: date
    time: time | None = None
    place: str | None = None
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    timezone: str | None = None
    fold: Literal[0, 1] | None = None
    time_accuracy_minutes: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_location(self) -> "BirthInput":
        coordinates = (self.latitude, self.longitude, self.timezone)
        if any(value is not None for value in coordinates) and not all(
            value is not None for value in coordinates
        ):
            raise ValueError("latitude, longitude, and timezone must be supplied together")
        if self.place is None and not all(value is not None for value in coordinates):
            raise ValueError("place or latitude, longitude, and timezone is required")
        if not date(1900, 1, 1) <= self.date <= date(2099, 12, 31):
            raise ValueError("date must be between 1900-01-01 and 2099-12-31")
        return self
```

`ChartSettings` 的欄位全部使用 `Literal`，預設值固定為規格中的 `bvr_raman_v1`；`ChartOptions` 固定支援 `dasha_depth` 1 至 3、`reference_date` 與 `output_language`；`ChartRequest` 組合三者。

`BVRStarError` 保存 `code`、`message` 與 `details`，`to_dict()` 回傳：

```python
{"error": {"code": self.code, "message": self.message, "details": self.details}}
```

- [ ] **Step 6：執行模型測試與全套靜態檢查**

執行：`uv run pytest tests/models -v && uv run ruff check . && uv run mypy src`

預期：所有模型測試 PASS，Ruff 與 mypy 均為 exit 0。

- [ ] **Step 7：提交基礎模型**

```bash
git add .python-version .gitignore pyproject.toml uv.lock src tests/models
git commit -m "feat: establish canonical request models"
```

### Task 2：歷史時區與民用時間標準化

**檔案：**

- 建立：`src/bvr_star/models/time.py`
- 建立：`src/bvr_star/timekeeping/__init__.py`
- 建立：`src/bvr_star/timekeeping/normalize.py`
- 測試：`tests/timekeeping/test_normalize.py`

**介面：**

- 消耗：`BirthInput`。
- 產生：`NormalizedInstant`、`NormalizedDateRange`。
- 產生：`normalize_birth_time(birth: BirthInput, timezone_name: str) -> NormalizedInstant | NormalizedDateRange`。

- [ ] **Step 1：寫出台灣 UTC 轉換及日期範圍失敗測試**

```python
from datetime import date, datetime, time, timezone

from bvr_star.models.request import BirthInput
from bvr_star.timekeeping.normalize import normalize_birth_time


def test_taipei_birth_is_converted_to_expected_utc_instant() -> None:
    birth = BirthInput(
        date=date(1983, 6, 15),
        time=time(3, 58),
        latitude=22.6265,
        longitude=120.312,
        timezone="Asia/Taipei",
    )
    result = normalize_birth_time(birth, "Asia/Taipei")
    assert result.utc_datetime == datetime(1983, 6, 14, 19, 58, tzinfo=timezone.utc)
    assert result.utc_offset_seconds == 8 * 3600


def test_missing_time_returns_half_open_local_day_range() -> None:
    birth = BirthInput(date=date(1983, 6, 15), place="Kaohsiung, Taiwan")
    result = normalize_birth_time(birth, "Asia/Taipei")
    assert result.start_utc.isoformat() == "1983-06-14T16:00:00+00:00"
    assert result.end_utc.isoformat() == "1983-06-15T16:00:00+00:00"
```

- [ ] **Step 2：執行測試確認缺少標準化函式**

執行：`uv run pytest tests/timekeeping/test_normalize.py -v`

預期：FAIL，指出 `normalize_birth_time` 或其模組不存在。

- [ ] **Step 3：實作普通時間與日期範圍**

建立不可變 Pydantic 模型。普通時間先建立無時區 `datetime`，再以 `ZoneInfo(timezone_name)` 產生兩個 fold 候選，透過 UTC 往返驗證候選。日期範圍使用當地 00:00 至次日 00:00 的半開區間，不使用 23:59:59。

- [ ] **Step 4：補上 DST 重疊與不存在時間的失敗測試**

```python
import pytest

from bvr_star.models.errors import BVRStarError


def test_ambiguous_new_york_time_requires_fold() -> None:
    birth = BirthInput(
        date=date(2021, 11, 7),
        time=time(1, 30),
        place="New York, USA",
    )
    with pytest.raises(BVRStarError) as error:
        normalize_birth_time(birth, "America/New_York")
    assert error.value.code == "LOCAL_TIME_AMBIGUOUS"


def test_nonexistent_new_york_time_is_rejected() -> None:
    birth = BirthInput(
        date=date(2021, 3, 14),
        time=time(2, 30),
        place="New York, USA",
    )
    with pytest.raises(BVRStarError) as error:
        normalize_birth_time(birth, "America/New_York")
    assert error.value.code == "LOCAL_TIME_NONEXISTENT"
```

- [ ] **Step 5：執行新測試確認 DST 分支為 Red**

執行：`uv run pytest tests/timekeeping/test_normalize.py -v`

預期：新增的兩個 DST 測試 FAIL，普通台灣時間與日期範圍測試仍 PASS。

- [ ] **Step 6：完成 fold、重疊與不存在時間判定**

兩個 fold 候選都不能往返原始無時區時間時拋出 `LOCAL_TIME_NONEXISTENT`；兩者都有效且 UTC offset 不同、但輸入未指定 fold 時拋出 `LOCAL_TIME_AMBIGUOUS`；輸入指定 fold 時採用該候選。錯誤 `details` 必須包含 `timezone` 與原始 `local_datetime`。

- [ ] **Step 7：驗證並提交民用時間模組**

執行：`uv run pytest tests/timekeeping -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS。

```bash
git add src/bvr_star/models/time.py src/bvr_star/timekeeping tests/timekeeping
git commit -m "feat: normalize historical civil time"
```

### Task 3：地點解析、時區查找與地址歧義

**檔案：**

- 建立：`src/bvr_star/models/location.py`
- 建立：`src/bvr_star/location/__init__.py`
- 建立：`src/bvr_star/location/contracts.py`
- 建立：`src/bvr_star/location/resolve.py`
- 建立：`src/bvr_star/location/nominatim.py`
- 測試：`tests/location/test_resolve.py`
- 測試資料：`tests/fixtures/nominatim/lingya.json`

**介面：**

- 產生：`LocationCandidate`、`ResolvedLocation`。
- 產生：`Geocoder.search(query: str) -> list[LocationCandidate]` Protocol。
- 產生：`resolve_location(birth: BirthInput, geocoder: Geocoder | None) -> ResolvedLocation`。

- [ ] **Step 1：寫出直接座標優先與台北時區失敗測試**

```python
def test_explicit_coordinates_and_timezone_bypass_geocoder() -> None:
    birth = BirthInput(
        date=date(1983, 6, 15),
        time=time(3, 58),
        place="ignored address",
        latitude=22.6265,
        longitude=120.312,
        timezone="Asia/Taipei",
    )
    result = resolve_location(birth, geocoder=None)
    assert result.source == "explicit"
    assert result.timezone == "Asia/Taipei"
    assert result.latitude == 22.6265
```

- [ ] **Step 2：執行確認地點模組為 Red**

執行：`uv run pytest tests/location/test_resolve.py -v`

預期：FAIL，因 `resolve_location` 尚不存在。

- [ ] **Step 3：實作直接座標及 timezonefinder 查找**

`resolve_location` 在三個明確欄位存在時直接回傳。若只有地址候選座標沒有時區，使用 `TimezoneFinder(in_memory=True).timezone_at(lng=..., lat=...)`；找不到時區時拋出 `TIMEZONE_NOT_FOUND`。

- [ ] **Step 4：寫出唯一地址與歧義地址失敗測試**

測試使用實作 `Geocoder` Protocol 的 `FixtureGeocoder`，回傳完整 `LocationCandidate`，不對 geopy 內部方法做 Mock：

```python
def test_unique_address_candidate_is_selected() -> None:
    geocoder = FixtureGeocoder([lingya_candidate])
    birth = BirthInput(date=date(1983, 6, 15), time=time(3, 58), place="高雄市苓雅區")
    result = resolve_location(birth, geocoder)
    assert result.source == "geocoder"
    assert result.timezone == "Asia/Taipei"


def test_close_ranked_different_candidates_are_reported() -> None:
    geocoder = FixtureGeocoder([
        candidate("Springfield, Illinois", 39.80, -89.64, 0.70),
        candidate("Springfield, Missouri", 37.21, -93.29, 0.68),
    ])
    with pytest.raises(BVRStarError) as error:
        resolve_location(
            BirthInput(date=date(2000, 1, 1), time=time(12), place="Springfield, USA"),
            geocoder,
        )
    assert error.value.code == "LOCATION_AMBIGUOUS"
    assert len(error.value.details["candidates"]) == 2
```

- [ ] **Step 5：實作候選選擇與 Nominatim 介面**

單一候選直接使用。多個候選時，只有第一名 `rank` 至少比第二名高 `0.05` 才自動選擇，否則回傳前五名。`NominatimGeocoder` 固定 `user_agent="BVR-Star/0.1 (+https://github.com/Omurok/BVR-Star)"`、`exactly_one=False`、`limit=5`、`addressdetails=True`，並使用 geopy `RateLimiter(min_delay_seconds=1.0)`。

- [ ] **Step 6：驗證並提交地點模組**

執行：`uv run pytest tests/location -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS，測試過程不發出網路請求。

```bash
git add src/bvr_star/models/location.py src/bvr_star/location tests/location tests/fixtures/nominatim
git commit -m "feat: resolve birth locations deterministically"
```

### Task 4：Swiss Ephemeris Raman 介面與官方基準資料

**檔案：**

- 建立：`src/bvr_star/models/ephemeris.py`
- 建立：`src/bvr_star/ephemeris/__init__.py`
- 建立：`src/bvr_star/ephemeris/constants.py`
- 建立：`src/bvr_star/ephemeris/swiss.py`
- 建立：`scripts/fetch_ephemeris.py`
- 建立：`scripts/capture_reference_fixture.py`
- 測試：`tests/ephemeris/test_swiss.py`
- 測試資料：`tests/fixtures/swisseph/1983-06-15T03-58-asia-taipei.json`

**介面：**

- 產生：`BodyPosition`、`AnglePosition`、`EphemerisSnapshot`。
- 產生：`SwissEphemeris.calculate(instant: NormalizedInstant, location: ResolvedLocation) -> EphemerisSnapshot`。
- 產生：`SwissEphemeris.calculate_bodies(utc_datetime: datetime) -> dict[str, BodyPosition]` 供日期範圍模式使用。

- [ ] **Step 1：先下載並驗證固定星曆資料**

`scripts/fetch_ephemeris.py` 的 manifest 固定兩個官方 raw URL 與全域限制中的 SHA-256；下載到暫存檔、驗證後以原子方式移至 `ephe/`。Hash 不符即刪除暫存檔並以非零狀態退出。

執行：`uv run python scripts/fetch_ephemeris.py`

預期：`ephe/sepl_18.se1` 與 `ephe/semo_18.se1` 存在，SHA-256 完全符合 manifest。

- [ ] **Step 2：寫出 Raman 設定與回傳來源旗標的失敗測試**

```python
def test_reference_chart_uses_raman_sidereal_swiss_ephemeris() -> None:
    snapshot = SwissEphemeris(ephe_path="ephe").calculate(reference_instant, lingya)
    assert snapshot.ayanamsha_name == "Raman"
    assert snapshot.source == "swiss_ephemeris"
    assert snapshot.return_flags & snapshot.required_swiss_flag
    assert snapshot.bodies["sun"].longitude == pytest.approx(61.02, abs=0.05)
    assert snapshot.bodies["moon"].longitude == pytest.approx(111.07, abs=0.05)
    assert snapshot.ascendant.longitude == pytest.approx(41.33, abs=0.08)
```

- [ ] **Step 3：執行確認 Swiss 介面為 Red**

執行：`uv run pytest tests/ephemeris/test_swiss.py -v`

預期：FAIL，因 `SwissEphemeris` 尚不存在。

- [ ] **Step 4：實作唯一的 Swiss Ephemeris 呼叫邊界**

`SwissEphemeris` 使用類別層級 `threading.RLock` 保護 Swiss Ephemeris 全域狀態。在鎖內依序：

```python
swe.set_ephe_path(str(ephe_path))
swe.set_sid_mode(swe.SIDM_RAMAN)
jdet, jdut = swe.utc_to_jd(year, month, day, hour, minute, seconds, swe.GREG_CAL)
flags = swe.FLG_SWIEPH | swe.FLG_SIDEREAL | swe.FLG_SPEED
coords, return_flags = swe.calc_ut(jdut, body_id, flags)
cusps, ascmc = swe.houses_ex(jdut, latitude, longitude, b"W", swe.FLG_SIDEREAL)
```

使用 `ascmc[0]` 作上升、`ascmc[1]` 作 MC。Rahu 使用 `swe.MEAN_NODE`；Ketu 由 `(rahu + 180) % 360` 推導。若任何行星 `return_flags` 沒有 `FLG_SWIEPH`，Snapshot 必須把來源改為實際回傳來源並附 `EPHEMERIS_FALLBACK` 警告；不得標示為 Swiss Ephemeris。`/health` 在這種狀態回傳 503，但本機計算仍可將明確警告與來源交給呼叫者。

- [ ] **Step 5：建立官方基準 Fixture 並收緊容許誤差**

`scripts/capture_reference_fixture.py` 在 `work/reference-swisseph/` 以 `git clone --branch v2.10.03 --depth 1` 取得官方 `aloistr/swisseph`（commit `175e1fcb3108bcd5c0d146c803f51dcf23508012`），執行 `make swetest`，再以 `swetest -b14.6.1983 -ut19:58:00 -sid3 -eswe -p0123456m -house120.312,22.6265,W` 取得基準資料。Script 將 UTC、JD UT、Ayanāṃśa、九大 Graha、上升、MC 與回傳旗標寫成 literal JSON；測試改為讀取該 Fixture，行星與角度誤差分別固定為 `1e-6` 度與 `1e-5` 度。捕捉完成後測試會核對 checkout 的實際 commit，避免標籤移動。

- [ ] **Step 6：驗證並提交星曆介面**

執行：`uv run pytest tests/ephemeris -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS，回傳來源為 `swiss_ephemeris`。

```bash
git add src/bvr_star/models/ephemeris.py src/bvr_star/ephemeris scripts tests/ephemeris tests/fixtures/swisseph
git commit -m "feat: add Raman Swiss Ephemeris adapter"
```

### Task 5：D1、星座、月宿、Pada 與整宮制

**檔案：**

- 建立：`src/bvr_star/models/chart.py`
- 建立：`src/bvr_star/chart/__init__.py`
- 建立：`src/bvr_star/chart/constants.py`
- 建立：`src/bvr_star/chart/zodiac.py`
- 建立：`src/bvr_star/chart/build.py`
- 測試：`tests/chart/test_zodiac.py`
- 測試：`tests/chart/test_build.py`

**介面：**

- 產生：`ZodiacPlacement`、`PlanetPlacement`、`NatalChart`。
- 產生：`zodiac_placement(longitude: float) -> ZodiacPlacement`。
- 產生：`whole_sign_house(longitude: float, ascendant_longitude: float) -> int`。
- 產生：`build_natal_chart(snapshot: EphemerisSnapshot) -> NatalChart`。

- [ ] **Step 1：寫出 360 度環繞與 Ashlesha 第二足測試**

```python
@pytest.mark.parametrize(
    ("longitude", "sign_index", "degree"),
    [(0.0, 0, 0.0), (359.999, 11, 29.999), (360.0, 0, 0.0), (-0.5, 11, 29.5)],
)
def test_zodiac_wraps_longitude(longitude: float, sign_index: int, degree: float) -> None:
    result = zodiac_placement(longitude)
    assert result.sign_index == sign_index
    assert result.degree_in_sign == pytest.approx(degree)


def test_reference_moon_is_ashlesha_second_pada() -> None:
    result = zodiac_placement(111.066)
    assert result.sign_key == "cancer"
    assert result.nakshatra_key == "ashlesha"
    assert result.pada == 2
```

- [ ] **Step 2：執行確認黃道換算為 Red**

執行：`uv run pytest tests/chart/test_zodiac.py -v`

預期：FAIL，因換算函式不存在。

- [ ] **Step 3：實作數學換算**

先以 `longitude % 360` 正規化。星座長度為 30 度、月宿長度為 `360 / 27`、Pada 長度為 `360 / 108`；對恰好 360 度及浮點邊界使用正規化後的半開區間。名稱只從固定 12 星座及 27 月宿常數表取得。

- [ ] **Step 4：寫出整宮宮位與基準盤落宮失敗測試**

```python
def test_whole_sign_houses_for_taurus_ascendant() -> None:
    ascendant = 41.33
    assert whole_sign_house(38.47, ascendant) == 1
    assert whole_sign_house(61.02, ascendant) == 2
    assert whole_sign_house(221.68, ascendant) == 7
    assert whole_sign_house(242.95, ascendant) == 8
```

- [ ] **Step 5：實作 D1 組裝**

宮位公式固定為 `((planet_sign - ascendant_sign) % 12) + 1`。`build_natal_chart` 將 Ephemeris Snapshot 的每顆星轉成 `PlanetPlacement`，保存黃經速度、逆行、宮位、月宿、Pada 與來源 ID；上升本身也建立 ZodiacPlacement。

- [ ] **Step 6：驗證並提交 D1**

執行：`uv run pytest tests/chart -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS。

```bash
git add src/bvr_star/models/chart.py src/bvr_star/chart tests/chart
git commit -m "feat: derive the D1 natal chart"
```

### Task 6：Shodashavarga 分盤

**檔案：**

- 建立：`src/bvr_star/models/varga.py`
- 建立：`src/bvr_star/varga/__init__.py`
- 建立：`src/bvr_star/varga/formulas.py`
- 建立：`src/bvr_star/varga/build.py`
- 建立：`docs/calculation-conventions.md`
- 測試：`tests/varga/test_formulas.py`
- 測試：`tests/varga/test_build.py`

**介面：**

- 產生：`VargaPlacement`、`VargaChart`。
- 產生：`varga_sign(longitude: float, division: int) -> int`。
- 產生：`build_vargas(chart: NatalChart) -> dict[str, VargaChart]`。

- [ ] **Step 1：寫出每一種分盤起點與奇偶規則測試**

```python
@pytest.mark.parametrize(
    ("longitude", "division", "expected_sign"),
    [
        (10.0, 2, 4), (20.0, 2, 3), (40.0, 2, 3), (50.0, 2, 4),
        (31.0, 3, 1), (41.0, 3, 5), (51.0, 3, 9),
        (38.0, 4, 4), (31.0, 7, 7), (31.0, 9, 9),
        (31.0, 10, 9), (31.0, 12, 1), (31.0, 16, 4),
        (31.0, 20, 8), (31.0, 24, 3), (31.0, 27, 3),
        (2.0, 30, 0), (32.0, 30, 1), (31.0, 40, 6),
        (31.0, 45, 4), (30.25, 60, 0),
    ],
)
def test_parasari_varga_mapping(
    longitude: float, division: int, expected_sign: int
) -> None:
    assert varga_sign(longitude, division) == expected_sign
```

- [ ] **Step 2：執行確認分盤公式為 Red**

執行：`uv run pytest tests/varga/test_formulas.py -v`

預期：FAIL，因 `varga_sign` 尚不存在。

- [ ] **Step 3：實作版本化公式登錄表**

公式固定如下並逐條寫入 `docs/calculation-conventions.md`：

- D2：奇數星座前半 Leo、後半 Cancer；偶數星座相反。
- D3：由本星座起依序加 0、4、8 個星座。
- D4：由本星座起依序加 0、3、6、9 個星座。
- D7：奇數星座由本星座起算；偶數星座由第七星座起算，再逐格前進。
- D9：Movable 由本星座、Fixed 由第九星座、Dual 由第五星座起算，再逐格前進。
- D10：奇數星座由本星座、偶數星座由第九星座起算，再逐格前進。
- D12：由本星座起算，再逐格前進。
- D16：Movable 由 Aries、Fixed 由 Leo、Dual 由 Sagittarius 起算。
- D20：Movable 由 Aries、Fixed 由 Sagittarius、Dual 由 Leo 起算。
- D24：奇數星座由 Leo、偶數星座由 Cancer 起算。
- D27：Fire 由 Aries、Earth 由 Cancer、Air 由 Libra、Water 由 Capricorn 起算。
- D30：奇數星座依序使用 0–5 Mars→Aries、5–10 Saturn→Aquarius、10–18 Jupiter→Sagittarius、18–25 Mercury→Gemini、25–30 Venus→Libra；偶數星座依序使用 0–5 Venus→Taurus、5–12 Mercury→Virgo、12–20 Jupiter→Pisces、20–25 Saturn→Capricorn、25–30 Mars→Scorpio。
- D40：奇數星座由 Aries、偶數星座由 Libra 起算。
- D45：Movable 由 Aries、Fixed 由 Leo、Dual 由 Sagittarius 起算。
- D60：每 0.5 度一格，每一星座都由 Aries 起算並循環十二星座。

所有等分盤都使用半開區間，29°59′59.999… 被限制在最後一格。未支援的 division 拋出 `UNSUPPORTED_VARGA`。

- [ ] **Step 4：寫出分盤上升、行星及邊界距離測試**

```python
def test_build_vargas_includes_planets_ascendant_and_boundary_distance() -> None:
    result = build_vargas(reference_chart)
    assert set(result) == {
        "D2", "D3", "D4", "D7", "D9", "D10", "D12",
        "D16", "D20", "D24", "D27", "D30", "D40", "D45", "D60",
    }
    assert result["D9"].ascendant is not None
    assert result["D9"].placements["moon"].boundary_distance_degrees >= 0
    assert result["D10"].rule_set == "parasari_shodashavarga_v1"
```

- [ ] **Step 5：實作分盤組裝並驗證**

`build_vargas` 對上升與每顆星體呼叫同一個 `varga_sign`，保存分盤星座、分盤內相對位置、距離最近切分邊界的本命黃經度數，以及 `parasari_shodashavarga_v1`。

執行：`uv run pytest tests/varga -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS。

- [ ] **Step 6：提交分盤引擎**

```bash
git add src/bvr_star/models/varga.py src/bvr_star/varga tests/varga docs/calculation-conventions.md
git commit -m "feat: calculate Parashari divisional charts"
```

### Task 7：Vimshottari 三層大運

**檔案：**

- 建立：`src/bvr_star/models/dasha.py`
- 建立：`src/bvr_star/dasha/__init__.py`
- 建立：`src/bvr_star/dasha/vimshottari.py`
- 測試：`tests/dasha/test_vimshottari.py`

**介面：**

- 產生：`DashaPeriod`。
- 產生：`calculate_vimshottari(moon_longitude: float, birth_utc: datetime, depth: int) -> list[DashaPeriod]`。
- 產生：`active_dasha_path(periods: list[DashaPeriod], reference_date: date) -> list[DashaPeriod]`。

- [ ] **Step 1：寫出完整出生大運與子期總和測試**

```python
def test_ashwini_start_has_full_ketu_mahadasha() -> None:
    periods = calculate_vimshottari(0.0, birth_utc, depth=1)
    assert periods[0].lord == "ketu"
    assert periods[0].duration_days == pytest.approx(7 * 365.25)


def test_antardashas_start_with_parent_lord_and_end_with_parent() -> None:
    periods = calculate_vimshottari(0.0, birth_utc, depth=2)
    ketu = periods[0]
    assert ketu.children[0].lord == "ketu"
    assert ketu.children[-1].end_utc == ketu.end_utc
```

- [ ] **Step 2：執行確認大運引擎為 Red**

執行：`uv run pytest tests/dasha/test_vimshottari.py -v`

預期：FAIL，因計算函式不存在。

- [ ] **Step 3：實作固定順序、年數與出生餘額**

固定順序與年數為 Ketu 7、Venus 20、Sun 6、Moon 10、Mars 7、Rahu 18、Jupiter 16、Saturn 19、Mercury 17。出生月宿主星由 `nakshatra_index % 9` 決定。出生餘額為月宿未走比例乘主星年數；子期長度為父期長度乘 `child_lord_years / 120`。使用整數微秒累積，最後一個子期直接對齊父期結束，避免浮點累積漂移。

- [ ] **Step 4：補上基準月亮與有效大運測試**

```python
def test_reference_moon_starts_in_mercury_mahadasha() -> None:
    periods = calculate_vimshottari(111.066, reference_birth_utc, depth=3)
    assert periods[0].lord == "mercury"
    assert periods[0].start_utc < reference_birth_utc < periods[0].end_utc
    assert active_dasha_path(periods, date(2026, 8, 21))
```

- [ ] **Step 5：驗證並提交大運引擎**

執行：`uv run pytest tests/dasha -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS。

```bash
git add src/bvr_star/models/dasha.py src/bvr_star/dasha tests/dasha
git commit -m "feat: calculate three-level Vimshottari periods"
```

### Task 8：尊貴狀態、燃燒、相位與 Yoga 證據

**檔案：**

- 建立：`src/bvr_star/models/rules.py`
- 建立：`src/bvr_star/rules/__init__.py`
- 建立：`src/bvr_star/rules/constants.py`
- 建立：`src/bvr_star/rules/dignity.py`
- 建立：`src/bvr_star/rules/aspects.py`
- 建立：`src/bvr_star/rules/yogas.py`
- 建立：`src/bvr_star/rules/evaluate.py`
- 測試：`tests/rules/test_dignity.py`
- 測試：`tests/rules/test_aspects.py`
- 測試：`tests/rules/test_yogas.py`

**介面：**

- 產生：`RuleEvidence`、`AspectEvidence`、`DignityEvidence`。
- 產生：`evaluate_rules(chart: NatalChart) -> list[RuleEvidence]`。

- [ ] **Step 1：寫出擢升土星及燃燒火星失敗測試**

```python
def test_saturn_in_libra_is_exalted() -> None:
    result = dignity_for("saturn", longitude=185.76)
    assert result.statuses == ["exalted"]


def test_mars_within_seventeen_degrees_of_sun_is_combust() -> None:
    result = combustion_for("mars", planet_longitude=57.98, sun_longitude=61.02, retrograde=False)
    assert result.is_combust is True
    assert result.angular_distance == pytest.approx(3.04, abs=0.02)
```

- [ ] **Step 2：執行確認尊貴與燃燒為 Red**

執行：`uv run pytest tests/rules/test_dignity.py -v`

預期：FAIL，因規則函式不存在。

- [ ] **Step 3：實作版本化尊貴與燃燒常數**

星座主星固定為 Mars、Venus、Mercury、Moon、Sun、Mercury、Venus、Mars、Jupiter、Saturn、Saturn、Jupiter。擢升／落陷使用傳統相對星座。Moolatrikona 度數固定為 Sun Leo 0–20、Moon Taurus 4–30、Mars Aries 0–12、Mercury Virgo 16–20、Jupiter Sagittarius 0–10、Venus Libra 0–15、Saturn Aquarius 0–20。燃燒門檻固定為 Moon 12、Mars 17、Mercury 順行 14／逆行 12、Jupiter 11、Venus 順行 10／逆行 8、Saturn 15 度；Rahu/Ketu 不判定燃燒。

- [ ] **Step 4：寫出 Parāśari 特殊相位測試**

```python
@pytest.mark.parametrize(
    ("planet", "source_sign", "target_sign", "aspect_key"),
    [
        ("mars", 0, 3, "fourth"),
        ("mars", 0, 7, "eighth"),
        ("jupiter", 0, 4, "fifth"),
        ("jupiter", 0, 8, "ninth"),
        ("saturn", 0, 2, "third"),
        ("saturn", 0, 9, "tenth"),
        ("venus", 0, 6, "seventh"),
    ],
)
def test_parasari_graha_aspects(planet: str, source_sign: int, target_sign: int, aspect_key: str) -> None:
    assert has_sign_aspect(planet, source_sign, target_sign, aspect_key)
```

所有七顆可見行星有第七相位；Mars 加第四、八；Jupiter 加第五、九；Saturn 加第三、十。`bvr_raman_v1` 不替 Rahu/Ketu 建立 Graha Drishti。每項證據保存整宮目標與距離精確相位點的 `angular_error`。

- [ ] **Step 5：寫出具明確定義的 Yoga 測試**

```python
def test_gaja_kesari_requires_jupiter_in_kendra_from_moon() -> None:
    evidence = evaluate_yogas(chart_with(moon_sign=0, jupiter_sign=3))
    assert "YOGA_GAJA_KESARI_V1" in {item.rule_id for item in evidence}


def test_budha_aditya_requires_same_sign() -> None:
    evidence = evaluate_yogas(chart_with(sun_sign=2, mercury_sign=2))
    assert "YOGA_BUDHA_ADITYA_V1" in {item.rule_id for item in evidence}
```

版本一規則定義固定為：Parivartana＝兩顆星座主互居對方星座；Gaja Kesari＝Jupiter 在 Moon 的 1/4/7/10；Budha Aditya＝Sun 與 Mercury 同星座；Chandra Mangala＝Moon 與 Mars 同星座；Neecha Bhanga＝落陷星的落陷星座主或該星座內擢升星的主星位於 Lagna 或 Moon 的 Kendra；Raja＝Kendra 主與 Trikona 主合相或互換；Dhana＝2/5/9/11 宮主中任兩顆合相或互換；Viparita Raja＝6/8/12 宮主落入 6/8/12 宮。每個 `rule_id` 必須指出這是 V1 定義，不宣稱涵蓋所有古典變體。

- [ ] **Step 6：完成規則整合、驗證與提交**

執行：`uv run pytest tests/rules -v && uv run ruff check . && uv run mypy src`

預期：全部 PASS。

```bash
git add src/bvr_star/models/rules.py src/bvr_star/rules tests/rules docs/calculation-conventions.md
git commit -m "feat: derive traceable Jyotish rule evidence"
```

### Task 9：敏感度、LLM Context 與標準 ChartService

**檔案：**

- 建立：`src/bvr_star/models/response.py`
- 建立：`src/bvr_star/sensitivity.py`
- 建立：`src/bvr_star/llm_context.py`
- 建立：`src/bvr_star/service.py`
- 測試：`tests/service/test_calculate.py`
- 測試：`tests/service/test_date_range.py`
- 測試：`tests/service/test_sensitivity.py`
- 測試：`tests/service/test_llm_context.py`
- 測試資料：`tests/fixtures/requests/reference-chart.json`

**介面：**

- 產生：`ChartResponse` 與 `DateRangeResponse`。
- 產生：`ChartService.calculate(request: ChartRequest) -> ChartResponse | DateRangeResponse`。
- 產生：`build_llm_context(response: ChartResponse) -> LLMContext`。

- [ ] **Step 1：寫出完整計算管線失敗測試**

```python
def test_reference_request_produces_complete_canonical_response() -> None:
    response = service.calculate(reference_request)
    assert response.schema_version == "1.0.0"
    assert response.status == "complete"
    assert response.settings.profile == "bvr_raman_v1"
    assert response.planets["moon"].nakshatra_key == "ashlesha"
    assert response.planets["jupiter"].house == 7
    assert "D9" in response.vargas
    assert response.dashas.periods
    assert response.rules
```

- [ ] **Step 2：執行確認服務層為 Red**

執行：`uv run pytest tests/service/test_calculate.py -v`

預期：FAIL，因 `ChartService` 尚不存在。

- [ ] **Step 3：實作完整計算編排**

`ChartService` 依序呼叫 `resolve_location`、`normalize_birth_time`、`SwissEphemeris.calculate`、`build_natal_chart`、`build_vargas`、`calculate_vimshottari`、`evaluate_rules`、敏感度與 `build_llm_context`。所有相依物由建構式注入，預設工廠才建立 Nominatim 與 SwissEphemeris；測試使用真實純計算模組與固定地點供應商。`provenance` 必須保存 BVR-Star 版本、pyswisseph／Swiss Ephemeris 版本、兩個星曆檔 SHA-256、tzdata 版本、timezonefinder 版本、地理編碼供應商、實際回傳旗標與計算 UTC 時刻。

- [ ] **Step 4：寫出缺少時間的日期範圍失敗測試**

```python
def test_date_range_never_invents_time_sensitive_fields() -> None:
    response = service.calculate(date_only_request)
    assert response.status == "date_range"
    assert response.start_utc < response.end_utc
    assert response.angles is None
    assert response.houses is None
    assert response.vargas is None
    assert response.dashas is None
    assert response.planet_ranges["moon"].start_longitude != response.planet_ranges["moon"].end_longitude
```

日期範圍模式只呼叫 `calculate_bodies` 計算當地日首尾，使用最短圓周方向表達經度範圍，並列出期間跨越的星座或月宿邊界。

- [ ] **Step 5：寫出時間誤差跨界與 LLM 證據回指測試**

```python
def test_sensitivity_warns_when_time_interval_changes_varga_ascendant() -> None:
    response = service.calculate(request_with_accuracy(minutes=5))
    assert any(item.code == "VARGA_ASCENDANT_CHANGED" for item in response.warnings)


def test_llm_context_evidence_ids_exist_in_full_response() -> None:
    response = service.calculate(reference_request)
    known_ids = response.evidence_ids()
    assert set(response.llm_context.evidence_ids) <= known_ids
```

敏感度以出生時間減／加 `time_accuracy_minutes` 各重算一次，比較 D1 上升、宮位與所有分盤上升；只輸出實際變動。`llm_context` 只投影既有欄位，保留精確值、有效大運、重要相位、規則 ID 與警告 ID，不執行第二套計算。

- [ ] **Step 6：執行核心全套測試、Coverage 與型別檢查**

執行：`uv run pytest --cov=bvr_star --cov-report=term-missing && uv run ruff check . && uv run mypy src`

預期：全部 PASS；核心純計算模組 Branch Coverage 至少 90%，不存在 Ruff 或 mypy 錯誤。

- [ ] **Step 7：提交標準服務層**

```bash
git add src/bvr_star/models/response.py src/bvr_star/sensitivity.py src/bvr_star/llm_context.py src/bvr_star/service.py tests/service tests/fixtures/requests
git commit -m "feat: expose the canonical chart service"
```

---

## 第二階段：CLI、AI Prompt 與 HTTP API

### Task 10：CLI、範例與 AI Prompt

**檔案：**

- 建立：`src/bvr_star/cli.py`
- 建立：`src/bvr_star/prompts.py`
- 建立：`prompts/zh-TW/full-reading.md`
- 建立：`prompts/en/full-reading.md`
- 建立：`examples/reference-request.json`
- 建立：`examples/python_client.py`
- 測試：`tests/cli/test_cli.py`

**介面：**

- 產生：Typer `app` 與規格中的五個 CLI 命令。
- 產生：`render_prompt(language: str, api_base_url: str) -> str`。

- [ ] **Step 1：寫出 CLI JSON 純輸出失敗測試**

```python
def test_calculate_writes_only_schema_valid_json_to_stdout(tmp_path: Path) -> None:
    result = runner.invoke(app, ["calculate", "--input", str(reference_request_path)])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "1.0.0"
    assert payload["status"] == "complete"


def test_errors_use_nonzero_exit_and_json_stderr(tmp_path: Path) -> None:
    result = runner.invoke(app, ["calculate", "--input", str(invalid_request_path)])
    assert result.exit_code != 0
    assert json.loads(result.stderr)["error"]["code"] == "VALIDATION_ERROR"
```

- [ ] **Step 2：執行確認 CLI 為 Red**

執行：`uv run pytest tests/cli/test_cli.py -v`

預期：FAIL，因 `bvr_star.cli` 尚不存在。

- [ ] **Step 3：實作五個 CLI 命令**

`calculate` 使用 `ChartRequest.model_validate_json` 讀取檔案，輸出 `model_dump_json(indent=2)`；`resolve-location`、`config`、`prompt` 與 `serve` 呼叫相同服務或工廠。所有一般日誌送至 stderr；stdout 只保留命令結果。

- [ ] **Step 4：撰寫繁中與英文 Prompt**

繁中 Prompt 使用固定九步流程：收集出生資料、呼叫 API/CLI、檢查警告、列出計算事實、列出傳統規則、整合性格／家庭／事業／姻緣／財富／長相／健康、提出有日期窗口的待驗證事件、區分不確定性、完成前核對證據 ID。Prompt 將人物稱為「命主」，並要求健康與財務內容保持反思性質。

`render_prompt` 以 `importlib.resources.files("bvr_star").joinpath("prompt_templates")` 讀取由 Hatch `force-include` 打包的根目錄 Prompt；因此 Git 儲存庫與 Wheel 使用同一份來源檔，不複製第二份範本。它只注入經驗證的 HTTPS API Base URL；CLI 本機模式注入 `local-cli`，Prompt 隨之改用 `bvr-star calculate`。

- [ ] **Step 5：驗證 CLI、實際執行範例並提交**

執行：

```bash
uv run pytest tests/cli -v
uv run bvr-star calculate --input examples/reference-request.json > /tmp/bvr-chart.json
uv run python -m json.tool /tmp/bvr-chart.json >/dev/null
uv run ruff check .
uv run mypy src
```

預期：全部 exit 0，stdout 可直接解析為 JSON。

```bash
git add src/bvr_star/cli.py src/bvr_star/prompts.py prompts examples tests/cli
git commit -m "feat: add CLI and AI prompt package"
```

### Task 11：FastAPI、限流與 OpenAPI

**檔案：**

- 建立：`src/bvr_star/api/__init__.py`
- 建立：`src/bvr_star/api/app.py`
- 建立：`src/bvr_star/api/dependencies.py`
- 建立：`src/bvr_star/api/errors.py`
- 建立：`src/bvr_star/api/limits.py`
- 建立：`scripts/export_openapi.py`
- 建立：`openapi.json`
- 測試：`tests/api/test_health.py`
- 測試：`tests/api/test_calculate.py`
- 測試：`tests/api/test_errors_and_limits.py`
- 測試：`tests/api/test_openapi.py`

**介面：**

- 產生：`create_app(service: ChartService | None = None) -> FastAPI`。
- 產生規格中的七個 HTTP 端點。

- [ ] **Step 1：寫出健康檢查與完整計算失敗測試**

```python
def test_health_reports_ephemeris_readiness(client: TestClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["ephemeris"]["source"] == "swiss_ephemeris"


def test_http_calculation_matches_python_service(client: TestClient) -> None:
    response = client.post("/v1/charts/calculate", json=reference_request.model_dump(mode="json"))
    assert response.status_code == 200
    actual = response.json()
    expected = service.calculate(reference_request).model_dump(mode="json")
    actual.pop("request_id")
    expected.pop("request_id")
    assert actual == expected
```

- [ ] **Step 2：執行確認 API 為 Red**

執行：`uv run pytest tests/api/test_health.py tests/api/test_calculate.py -v`

預期：FAIL，因 `create_app` 尚不存在。

- [ ] **Step 3：實作路由與統一錯誤格式**

`create_app` 設定 `docs_url="/docs"`、`openapi_url="/openapi.json"`，並註冊 `/health`、`/v1/config`、`/v1/locations/resolve`、`/v1/charts/calculate`、`/v1/prompts/full-reading`。Pydantic 驗證與 `BVRStarError` 都轉成：

```json
{"error":{"code":"...","message":"...","details":{}},"request_id":"uuid"}
```

422 用於驗證／歧義、429 用於限流、503 用於地理編碼或星曆不可用、500 隱藏 Stack Trace。

- [ ] **Step 4：寫出 16 KiB 與限流失敗測試**

```python
def test_request_larger_than_16_kib_is_rejected(client: TestClient) -> None:
    response = client.post(
        "/v1/charts/calculate",
        content=b"{" + b" " * 16384 + b"}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413


def test_location_limit_returns_429(client: TestClient) -> None:
    for _ in range(5):
        assert client.post("/v1/locations/resolve", json={"place": "Kaohsiung"}).status_code != 429
    assert client.post("/v1/locations/resolve", json={"place": "Kaohsiung"}).status_code == 429
```

實作單實例、每 IP 滑動分鐘桶：星盤 30/min、地址 5/min。CORS 使用 `allow_origins=["*"]`、`allow_credentials=False`。Access Log 只記錄 Request ID、路徑、狀態與延遲。

- [ ] **Step 5：輸出並驗證 OpenAPI 不過期**

`scripts/export_openapi.py` 以 `create_app().openapi()` 產生排序且縮排固定的 `openapi.json`。測試讀取檔案並比較應用程式當下 Schema，確保工具定義和 API 一致。

執行：`uv run python scripts/export_openapi.py && uv run pytest tests/api -v`

預期：全部 PASS。

- [ ] **Step 6：提交 API**

```bash
git add src/bvr_star/api scripts/export_openapi.py openapi.json tests/api
git commit -m "feat: expose the versioned chart API"
```

---

## 第三階段：封裝、文件與公開部署

### Task 12：Docker、CI、授權及使用文件

**檔案：**

- 建立：`Dockerfile`
- 建立：`.dockerignore`
- 建立：`render.yaml`
- 建立：`.github/workflows/ci.yml`
- 建立：`README.md`
- 建立：`LICENSE`
- 建立：`THIRD_PARTY_NOTICES.md`
- 建立：`SECURITY.md`
- 建立：`CONTRIBUTING.md`
- 建立：`docs/api.md`
- 建立：`docs/ai-integration.md`
- 建立：`docs/self-hosting.md`
- 測試：`tests/smoke/test_container.sh`

**介面：**

- 產生：監聽 `0.0.0.0:$PORT` 的唯讀 Docker 服務。
- 產生：每次 Push/PR 執行的 CI。
- 產生：人類與 AI 可依循的公開文件。

- [ ] **Step 1：先建立會失敗的容器 Smoke Test**

`tests/smoke/test_container.sh` 執行：

```bash
set -euo pipefail
docker build -t bvr-star:test .
container_id=$(docker run -d -p 18080:8000 -e PORT=8000 bvr-star:test)
trap 'docker stop "$container_id" >/dev/null' EXIT
for attempt in $(seq 1 30); do
  curl -fsS http://127.0.0.1:18080/health && break
  sleep 1
done
curl -fsS -X POST http://127.0.0.1:18080/v1/charts/calculate \
  -H 'content-type: application/json' \
  --data @examples/reference-request.json | python3 -m json.tool >/dev/null
```

執行：`bash tests/smoke/test_container.sh`

預期：FAIL，因 Dockerfile 尚不存在。

- [ ] **Step 2：實作非 root Docker 映像**

`Dockerfile` 以 `python:3.11-slim` 多階段建置，安裝 uv、依 `uv.lock` 安裝、執行 `scripts/fetch_ephemeris.py`、建立非 root `app` 使用者，最後執行：

```text
uvicorn bvr_star.api.app:create_app --factory --host 0.0.0.0 --port ${PORT:-8000}
```

映像只含 `src/`、`prompts/`、`ephe/` 與執行相依套件，不包含測試快取或 Git 資料。

- [ ] **Step 3：完成 Render Blueprint 與 CI**

`render.yaml` 建立名稱 `bvr-star`、runtime `docker`、plan `free`、healthCheckPath `/health`、autoDeploy `true` 的 Web Service。CI 在 Ubuntu 執行 Python 3.11 的 `uv sync --locked --all-groups`、pytest coverage、Ruff、mypy、套件建置、OpenAPI 新鮮度檢查與 Docker build；不在一般 PR 執行公開部署。

- [ ] **Step 4：撰寫完整公開文件**

README 依序提供：專案界線、公開 API（部署前標為「尚未發布」，部署後由 Task 13 寫入實際 URL）、CLI 快速開始、curl、Python、AI Prompt、計算設定、缺少出生時間、敏感度、隱私、Cold Start、授權與自行部署。`THIRD_PARTY_NOTICES.md` 記錄 Swiss Ephemeris AGPL／專業雙授權、pyswisseph AGPL、Nominatim 政策、timezonefinder 的 MIT 與時區邊界資料 ODbL。

- [ ] **Step 5：執行完整驗證與容器 Smoke Test**

執行：

```bash
uv run pytest --cov=bvr_star --cov-report=term-missing
uv run ruff check .
uv run mypy src
uv build
uv run python scripts/export_openapi.py
git diff --exit-code openapi.json
bash tests/smoke/test_container.sh
```

預期：所有命令 exit 0，測試零失敗，Docker 健康檢查與基準盤呼叫成功。

- [ ] **Step 6：提交封裝與文件**

```bash
git add Dockerfile .dockerignore render.yaml .github README.md LICENSE THIRD_PARTY_NOTICES.md SECURITY.md CONTRIBUTING.md docs tests/smoke
git commit -m "build: package and document BVR-Star"
```

### Task 13：GitHub 發布、CI 與 Render 公開 API

**檔案：**

- 修改：`README.md`
- 修改：`prompts/zh-TW/full-reading.md`
- 修改：`prompts/en/full-reading.md`
- 修改：`docs/ai-integration.md`

**介面：**

- 產生：公開 `https://github.com/Omurok/BVR-Star`。
- 產生：Render 指派的公開 HTTPS API。

- [ ] **Step 1：發布前重新執行所有驗收命令**

執行：

```bash
uv run pytest --cov=bvr_star --cov-report=term-missing
uv run ruff check .
uv run mypy src
uv build
bash tests/smoke/test_container.sh
git status --short
```

預期：所有驗證 exit 0，`git status --short` 沒有輸出。

- [ ] **Step 2：建立並推送公開 GitHub 儲存庫**

確認 `gh auth status` 的作用中帳號為 `Omurok`，再執行：

```bash
gh repo create Omurok/BVR-Star --public --source=. --remote=origin --push
gh repo view Omurok/BVR-Star --web=false
```

預期：第二個命令顯示公開儲存庫資料及 main 預設分支。

- [ ] **Step 3：等待並驗證 GitHub Actions**

執行：`gh run list --repo Omurok/BVR-Star --limit 1`，取得 Run ID 後執行 `gh run watch RUN_ID --repo Omurok/BVR-Star --exit-status`。

預期：Workflow 結論為 success。

- [ ] **Step 4：在 Render 連結公開儲存庫並建立服務**

開啟 Render Dashboard，選擇 New → Blueprint，連結 `Omurok/BVR-Star` 並套用根目錄 `render.yaml`。若尚未登入或尚未授權 Render 讀取 GitHub，停在該授權畫面請使用者完成登入／授權；不選擇付費方案。服務建置完成後記錄 Render 實際指派的 HTTPS Base URL。

- [ ] **Step 5：以外部網路驗證公開 API**

將 Render 指派網址存入 shell 區域變數 `BVR_API_BASE`，執行：

```bash
curl -fsS "$BVR_API_BASE/health" | python3 -m json.tool
curl -fsS -X POST "$BVR_API_BASE/v1/charts/calculate" \
  -H 'content-type: application/json' \
  --data @examples/reference-request.json > /tmp/bvr-public-reference.json
python3 -m json.tool /tmp/bvr-public-reference.json >/dev/null
```

預期：健康狀態為 `ok`，基準盤回應 `schema_version` 為 `1.0.0`、`status` 為 `complete`。

- [ ] **Step 6：將實際網址寫入文件與 Prompt 並推送**

README 與 AI 整合文件寫入實際 Base URL及免費方案 Cold Start 說明。Prompt 的預設 API URL 使用同一網址，但仍允許呼叫者覆寫。執行：

```bash
git add README.md prompts docs/ai-integration.md
git commit -m "docs: publish the live BVR-Star API"
git push origin main
```

- [ ] **Step 7：最終驗收**

重新執行 Task 13 Step 1、等待最新 GitHub Actions 成功，並再次執行 Step 5。逐項核對設計規格第 17 節十項驗收條件，將實際測試數、公開 GitHub URL、公開 API URL、GitHub Actions Run URL 與 Render Cold Start 狀態記錄在最終交付訊息中。

---

## 規格覆蓋索引

- 規格第 1–3 節「目的、目標、非目標」：全域限制、Task 9、Task 10、Task 12。
- 規格第 4–5 節「使用流程與架構」：Task 1–11 的共同模型與單一 `ChartService`。
- 規格第 6–7 節「輸入、地點與時間」：Task 1–3、Task 9、Task 11。
- 規格第 8 節「計算慣例」：Task 4–8。
- 規格第 9 節「輸出格式」：Task 9。
- 規格第 10–11 節「HTTP、CLI、Python」：Task 9–11。
- 規格第 12 節「AI Prompt」：Task 10、Task 13。
- 規格第 13–15 節「隱私、文件、部署」：Task 11–13。
- 規格第 16–17 節「測試與驗收」：每個 Task 的 Red-Green 步驟、Task 12 Smoke Test、Task 13 最終驗收。

## 計畫完成條件

- 13 個 Task 全部勾選。
- 每個 Production 行為均有先失敗、後通過的測試證據。
- Python、CLI、HTTP 三個介面對相同請求輸出相同 Schema 與計算值。
- 本機全套測試、靜態分析、套件建置、Docker Smoke Test 與 GitHub Actions 全部通過。
- 公開 GitHub 儲存庫及 Render API 可由外部讀取。
- 最終 Prompt 先呼叫程式，再進行傳統占星解讀，並清楚顯示警告與證據來源。
