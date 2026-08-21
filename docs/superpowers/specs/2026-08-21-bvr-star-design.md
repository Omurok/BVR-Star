# BVR-Star 設計規格

日期：2026-08-21
狀態：已於 2026-08-21 經使用者核准
目標儲存庫：`https://github.com/Omurok/BVR-Star`

## 1. 專案目的

BVR-Star 是一套開源、具確定性且可重複驗算的印度占星計算引擎。它接收出生日期、出生時間與出生地，將民用時間和地理位置標準化，依明確指定的計算慣例建立恆星黃道星盤，並輸出可追溯的 JSON，供人類或語言模型解讀。

本專案將三類工作分開處理：

1. 由程式產生的天文事實與數學轉換。
2. 由可版本化規則引擎產生的印度占星規則。
3. 由外部 AI 或人類占星師完成的敘事性解讀。

主要預設設定檔遵循本次 B. V. Raman 取向分析使用的慣例：

- 恆星黃道；
- Raman Ayanāṃśa；
- 地心行星位置；
- 平均月交點；
- Parāśari 整宮制與行星相位；
- Vimshottari 大運。

本系統不宣稱占星解讀已獲科學驗證。每項衍生規則都會公開其計算慣例與證據，使後續解讀能清楚區分「計算結果」與「詮釋推論」。

## 2. 專案目標

第一版必須提供：

- 可重複使用的 Python 函式庫；
- 輸出機器可讀 JSON 的命令列介面；
- 具公開 OpenAPI Schema 的 FastAPI HTTP 服務；
- Docker 映像與 Render 部署設定；
- 採用版本化設定、結果可重現的星盤計算；
- 為語言模型最佳化的精簡 `llm_context`；
- 繁體中文與英文 AI Prompt 範本；
- 自動化測試，包括已確認的 1983 年高雄基準盤；
- 公開於 `Omurok/BVR-Star`、採 AGPL-3.0 授權的原始碼；
- 不保存使用者資料的公開計算 API。

## 3. 第一版不包含的範圍

第一版不會：

- 在 API 內產生自稱客觀的人生診斷；
- 宣稱推測事件必然已經發生；
- 進行出生時間校正；
- 從先前對話推測缺少的出生時間；
- 納入 Shadbala、Ashtakavarga、Jaimini 大運、KP 占星或 Varshaphala；
- 提供使用者帳號、星盤保存、收費或星盤資料庫；
- 承諾收錄所有古典與現代來源中的全部 Yoga；
- 保證 Render 免費方案具有低延遲或持續在線能力。

上述功能可在核心星盤資料格式穩定後，以獨立且具版本編號的規則模組加入。

## 4. 使用者與主要流程

### 4.1 AI 輔助解讀

AI 接收出生資料後，呼叫公開 HTTP API 或本機 CLI，取得完整星盤回應，再依儲存庫內的 Prompt 撰寫報告。AI 必須將 `facts`、`rules`、`warnings` 與 `sensitivity` 視為不同類型的資料來源，不得根據文字自行重算星體度數。

### 4.2 本機計算

使用者安裝 Python 套件後執行：

```text
bvr-star calculate --input birth.json --output chart.json
```

同一套計算也可透過 Python 函式使用：

```text
calculate_chart(request: ChartRequest) -> ChartResponse
```

### 4.3 公開 API 計算

客戶端將 `ChartRequest` 傳送至 `POST /v1/charts/calculate`，並取得與 Python 函式庫及 CLI 相同格式的 `ChartResponse`。

## 5. 系統架構

本專案以單一 Python 程式庫為核心，在純計算核心外建立不同使用介面：

```text
出生資料
  -> 地點解析
  -> 歷史民用時間標準化
  -> 儒略日與 Swiss Ephemeris 介面
  -> 恆星黃道星盤核心
  -> 印度占星衍生模組
  -> 完整 ChartResponse + 精簡 llm_context
  -> Python / CLI / HTTP 介面
```

核心模組不得匯入 FastAPI、命令列參數解析、Render 或 Prompt 程式碼。需要網路的地理編碼必須置於抽象介面之後，使計算核心可以離線測試；使用者提供精確經緯度時，可完全略過地理編碼。

### 5.1 模組邊界

- `models`：經驗證的請求、回應、警告、來源與錯誤模型。
- `location`：地理編碼介面、供應商實作、座標驗證與時區查找。
- `time`：IANA 時區、重疊或不存在時間偵測、UTC 轉換及儒略日前置處理。
- `ephemeris`：唯一可以呼叫 Swiss Ephemeris 的模組。
- `chart`：星座、宮位、上升、月宿、Pada 與行星落點。
- `varga`：依指定規則集版本計算分盤。
- `dasha`：Vimshottari 出生餘額與多層大運計算。
- `rules`：尊貴狀態、燃燒、合相、Parāśari 相位、宮主與 Yoga 證據。
- `sensitivity`：依出生時間誤差上下界重新計算並比較結構。
- `llm`：節省 Token 的計算結果投影，不產生敘事性預測。
- `cli`：本機命令列介面。
- `api`：FastAPI 路由、HTTP 錯誤轉換、限流及 OpenAPI 資訊。

每個模組只有一個公開邊界，且不必讀取其他模組的內部實作即可測試。

## 6. 輸入格式

標準 JSON 請求如下：

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

驗證規則：

- `date` 為必填欄位。
- 第一版接受 1900-01-01 至 2099-12-31 的民用日期，超出範圍時回傳 `DATE_OUT_OF_RANGE`。
- 只有在日期範圍模式中，`time` 才可以省略。
- 完整計算必須提供 `place`，或同時提供 `latitude`、`longitude` 與 `timezone`。
- 明確提供的經緯度與時區優先於地址，回應中必須記錄此項選擇。
- 緯度必須介於 -90 至 90；經度必須介於 -180 至 180。
- `time_accuracy_minutes` 必須大於或等於零，且僅在提供出生時間時使用。
- 一般時間不提供 `fold`；遇到夏令時間回撥造成的重疊時間時，才以 `0` 或 `1` 選擇其中一次。
- `reference_date` 預設為請求當下的 UTC 日期，只用於選取 `llm_context` 內的有效大運路徑，不會改變本命盤。
- 不認識的計算設定直接拒絕，不得默默套用預設值。

## 7. 地點與時間標準化

### 7.1 地址模式

低流量部署的預設供應商為 OpenStreetMap Nominatim，必須使用可識別的 User-Agent、每個服務實例每秒最多一次的地理編碼請求，以及有容量上限的快取。供應商必須可透過設定替換。

若同一地址解析出實質不同的候選地點，API 回傳 `LOCATION_AMBIGUOUS` 與候選清單。客戶端必須改用更精確的地址，或重新提交明確的經緯度與時區。服務不得隱藏低可信度的地點選擇。

### 7.2 座標模式

除非請求已提供時區，服務會依經緯度取得 IANA 時區識別字。歷史 UTC 時差與夏令時間規則由 Python `zoneinfo` 和固定版本的 `tzdata` 套件讀取 IANA 時區資料庫。

### 7.3 民用時間邊界情況

- 不存在的當地時間回傳 `LOCAL_TIME_NONEXISTENT`。
- 重疊的當地時間回傳 `LOCAL_TIME_AMBIGUOUS`，後續請求必須明確指定 `fold`。
- 回應必須記錄當地時間、IANA 時區、UTC 時差、UTC 時刻、儒略日、地點來源及資料版本。

### 7.4 缺少出生時間

若沒有 `time`，回應模式為 `date_range`。引擎計算當地民用日的起點與終點，回傳行星經度範圍，以及期間發生的星座或月宿跨界；上升、宮位、分盤上升、大運出生餘額及其他時間敏感結論一律省略。程式不得虛構中午出生時間。

## 8. 計算慣例

每次回應都必須包含解析後的完整慣例設定。`bvr_raman_v1` 固定使用：

- Swiss Ephemeris 恆星黃道旗標；
- Raman Ayanāṃśa（`SE_SIDM_RAMAN`）；
- 當日黃道的地心黃經；
- 以平均月交點計算 Rahu，Ketu 固定在正對面；
- 以恆星黃道上升星座建立整宮制；
- 傳統 Parāśari 行星相位；
- Vimshottari 大運，每一大運年使用 365.25 日；
- 註冊為 `parasari_shodashavarga_v1` 的分盤公式。

回應必須保存 Swiss Ephemeris 的實際回傳旗標。若程式從 Swiss Ephemeris 星曆檔退回其他計算來源，必須在來源資料中明確說明並回傳警告。Docker 部署必須包含支援日期範圍所需、版本固定的星曆資料。

### 8.1 計算星體與角度

第一版計算：

- 太陽、月亮、水星、金星、火星、木星及土星；
- 平均 Rahu 與由其推導的 Ketu；
- 出生時間已知時的上升與 MC。

每顆星體的回應包含恆星黃經、星座、星座內度數、月宿、Pada、黃經速度、逆行狀態、宮位與計算來源。

### 8.2 分盤

第一版包含 D1 與傳統 Shodashavarga 組合：

- D2、D3、D4、D7、D9、D10、D12；
- D16、D20、D24、D27、D30；
- D40、D45、D60。

每張分盤必須記錄公式規則集識別字、行星落點、出生時間已知時的分盤上升、星座主星及距離邊界的度數。若出生時間誤差區間跨越分盤邊界，程式必須產生敏感度警告，不得只輸出一個毫無保留的落點。

### 8.3 Vimshottari 大運

引擎依月亮所在月宿推導出生大運，計算出生時的大運餘額，並展開至指定層級。第一版接受第一至第三層：Mahadasha、Antardasha 與 Pratyantardasha。每一期間包含主星、UTC 與當地曆法起訖時間、父層路徑及計算慣例。

### 8.4 規則證據

第一版推導：

- 星座與宮位主星；
- 自有星座、擢升、落陷、Moolatrikona，以及可設定的行星友敵關係；
- 順行與逆行；
- 依版本化門檻表判定的燃燒；
- 附精確角距的合相；
- 附來源、目標、相位種類及度數證據的 Parāśari 相位；
- 以版本化規則識別字表示的常見 Yoga，第一批包括 Parivartana、Gaja Kesari、Budha Aditya、Chandra Mangala、Neecha Bhanga、常見 Dhana／Raja 組合，以及 Viparita Raja 組合。

每項衍生規則包含 `rule_id`、輸入證據、結果、強弱修飾、來源說明及規則集版本。API 不得將一項已觸發規則直接轉換成必然發生的人生事件。

## 9. 輸出格式

回應具有固定的頂層結構：

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

`llm_context` 必須由同一份具型別的回應資料產生，不得進行第二套計算。內容包括：

- 精簡行星落點與宮主關係；
- 最精確的重要合相與相位；
- 尊貴狀態與燃燒修飾；
- 重要分盤中的重複確認及矛盾；
- 依呼叫者指定參考日期選出的有效大運；
- 敏感度與不確定性說明；
- 可回指完整回應的證據識別字。

數值欄位必須保持數值型別。可另外提供人類可讀標籤，但不得以標籤取代精確數值。

## 10. HTTP API

公開 API 以 `/v1` 進行版本管理：

- `GET /health`：程序與星曆資料就緒狀態。
- `GET /v1/config`：支援的設定檔、設定、版本及限制。
- `POST /v1/locations/resolve`：低流量地址解析。
- `POST /v1/charts/calculate`：完整計算或日期範圍計算。
- `GET /v1/prompts/full-reading?language=zh-TW`：版本化 AI Prompt 範本。
- `GET /docs`：FastAPI 互動式說明文件。
- `GET /openapi.json`：機器可讀的工具 Schema。

星盤計算成功時回傳 HTTP 200。輸入驗證與歧義錯誤使用 HTTP 422，並附固定格式的錯誤內容。超過限流時使用 HTTP 429。供應商或星曆資料未就緒時使用 HTTP 503。未預期錯誤只回傳不透明的請求識別字，不得暴露 Stack Trace。

請求本文上限為 16 KiB。第一版沒有身分驗證、不接受檔案上傳，也不允許任意網址擷取。單一免費方案實例預設每個 IP 每分鐘最多計算 30 張星盤、解析 5 次地址。`/v1/config` 必須公開限制值，部署設定可以將限制調低。

## 11. CLI 與 Python API

CLI 提供：

```text
bvr-star calculate --input INPUT.json [--output OUTPUT.json]
bvr-star resolve-location "ADDRESS"
bvr-star config
bvr-star prompt --language zh-TW
bvr-star serve --host 127.0.0.1 --port 8000
```

若未提供 `--output`，JSON 寫入標準輸出；診斷資訊寫入標準錯誤，使 AI 不必先清除日誌即可解析標準輸出。錯誤使用非零結束碼，並採用與 HTTP 相同的固定錯誤格式。

Python API 接受並回傳標準型別模型。不同介面不得維護各自獨立的計算結果型別。

## 12. AI Prompt 套件

儲存庫在 `prompts/zh-TW/` 與 `prompts/en/` 提供簡潔 Prompt。繁體中文全面報告 Prompt 指示 AI：

1. 收集出生日期、當地出生時間、出生地及時間準確度。
2. 解讀前先呼叫公開 API 或本機 CLI。
3. 只以計算欄位與證據識別字作為星盤來源。
4. 分開標示「計算事實」「傳統占星規則」與「綜合解讀」。
5. 以傳統占星解讀涵蓋性格、家庭、事業、姻緣、財富、長相與健康。
6. 將過往事件內容表達為附日期的待驗證假設。
7. 在受影響結論附近揭露時間、地點、分盤及規則警告。
8. 除非使用者指定其他角色，否則一律稱為「命主」。
9. 將醫療、財務與關係內容定位為反思參考，不冒充診斷或確定事實。

Prompt 必須使用正向、依序排列的操作步驟與完成條件。計算慣例以 API 回應及計算文件為單一真實來源；Prompt 只指向相關欄位，不重複可能過時的表格。

README 範例包括：

- 可直接複製、使用公開 API 的中文 Prompt；
- 供 Codex 或其他程式代理使用的本機 CLI Prompt；
- curl 範例；
- Python 範例；
- 將 `openapi.json` 匯入 AI 工具或 Action 系統的說明。

## 13. 隱私、安全與維運

- API 不持久保存請求或回應。
- 應用程式日誌只記錄請求識別字、狀態、延遲及錯誤類別，不記錄請求本文或出生資料。
- 公開 API 回傳占星計算與規則證據，不產生醫療或財務診斷。
- CORS 允許公開、無憑證的使用方式；服務不接受 Cookie。
- 地理編碼呼叫採嚴格限流，且供應商可替換。
- 相依套件版本及下載的星曆資料必須固定版本並驗證 Checksum。
- `/health` 必須在回報健康前確認所需星曆來源已就緒。

## 14. 儲存庫與文件

預定儲存庫結構：

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

文件包括：

- 快速開始與公開 API 網址；
- 計算慣例及支援日期範圍；
- 請求與回應 Schema；
- 規則與證據目錄；
- 地址、時區及出生時間準確度的處理方式；
- AI 整合指南；
- 部署與自行託管指南；
- Swiss Ephemeris 及第三方授權聲明。

由於 Swiss Ephemeris 採 AGPL 或專業授權雙軌制，本專案使用 AGPL-3.0。若要進行閉源部署，必須取得並遵守適用的 Swiss Ephemeris 專業授權。

## 15. 部署

首次公開部署使用連結至 `Omurok/BVR-Star` 的 Docker 型 Render Web Service。`render.yaml` 指定免費方案，讓應用程式監聽 `0.0.0.0:$PORT`，以 `/health` 作為健康檢查，並從 `main` 分支自動部署。

預期服務名稱為 `bvr-star`；實際 `onrender.com` 網址必須等 Render 指派後，才能寫入 README 與 Prompt。設計不得假設特定子網域一定可用。

免費服務可能在閒置後休眠並產生 Cold Start。README 與 API 整合指南必須說明此限制。改用持續在線的付費實例屬於另一項付費決策。

部署需要使用者以 Render 帳號連結公開 GitHub 儲存庫。如果目前環境沒有已驗證的 Render 登入狀態，實作流程必須停在最小必要授權步驟，請使用者完成授權。

## 16. 測試策略

實作採用 Red-Green-Refactor。每個具實際邏輯的公開函式，必須先有一項會失敗的行為測試。

測試群組包括：

- 星座、月宿、Pada、360 度環繞、分盤、相位、燃燒及大運邊界的人工固定值單元測試；
- 歷史 UTC 時差、不存在時間、重疊時間及 UTC 轉換測試；
- 使用完整錄製供應商回應的離線地點測試，不以缺少欄位的簡化 Mock 取代；
- 以固定版本官方 `swetest` 結果驗證星曆介面；
- 1983-06-15 03:58:00、Asia/Taipei、高雄市苓雅區座標的黃金基準盤；
- 跨越上升或分盤邊界的敏感度測試；
- 將標準輸出解析成標準 Schema 的 CLI 整合測試；
- 成功、日期盤、地點歧義、輸入驗證、限流及相依服務不可用的 API 測試；
- 啟動映像、等待就緒，再呼叫 `/health` 與 `/v1/charts/calculate` 的 Docker Smoke Test。

天文預期值必須是從固定版本官方工具取得的常值，不得由受測程式的輔助函式重新計算。每種欄位必須記錄允許誤差。先前討論的星盤是回歸測試目標，但不是唯一的天文資料來源。

GitHub Actions 必須在 Push 與 Pull Request 時執行測試、靜態分析、套件建置及 Docker 建置。

## 17. 驗收條件

第一版只有在以下每一項都有證據時才能驗收：

1. 同一份標準請求經 Python、CLI 及 HTTP 介面產生符合 Schema 且可重複的相同結果。
2. 基準盤在文件記錄的允許誤差內符合固定版本的 `swetest` 結果。
3. Raman Ayanāṃśa、平均交點、整宮制、月宿／Pada、指定分盤、三層大運、規則證據及敏感度都有測試保護。
4. 缺少時間模式回傳範圍、排除時間敏感欄位，且不虛構出生時間。
5. 地址或民用時間有歧義時，回傳可採取行動的結構化錯誤。
6. AI Prompt 先呼叫計算介面，且能在不重算星盤數值的前提下完成報告。
7. Docker 映像可從乾淨環境建置，並通過即時健康與星盤 Smoke Test。
8. 公開 `Omurok/BVR-Star` 儲存庫的 GitHub Actions 全部通過。
9. 公開 Render 網址能回傳健康狀態及成功的基準盤計算。
10. README 記錄正式網址、Cold Start 限制、計算設定檔、隱私處理及授權。

## 18. 外部參考資料

- Swiss Ephemeris 程式介面：<https://www.astro.com/swisseph/swephprg.htm>
- Swiss Ephemeris 授權：<https://www.astro.com/swisseph/sweph_e.htm>
- IANA 時區資料庫：<https://www.iana.org/time-zones/tz-link>
- Nominatim 使用政策：<https://operations.osmfoundation.org/policies/nominatim/>
- Render Web Service：<https://render.com/docs/web-services>
- Render 免費服務限制：<https://render.com/docs/free>
