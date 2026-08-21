# BVR-Star

以固定、可稽核的計算流程，將出生日期、出生時間與出生地轉為適合 AI 直接解讀的印度星盤 JSON。專案採用 Raman Ayanāṃśa、恆星黃道、平均交點、整宮制、Parāśari 規則與 Vimshottari 大運。

> 占星是傳統象徵系統，不是經科學證實的人格診斷或事件預測工具。本服務不提供醫療、法律或財務診斷。

## 公開 API

- API：<https://bvr-star.onrender.com>
- 互動文件：<https://bvr-star.onrender.com/docs>
- OpenAPI：<https://bvr-star.onrender.com/openapi.json>
- AI Prompt：<https://bvr-star.onrender.com/v1/prompts/full-reading?language=zh-TW>

Render 免費服務可能在閒置後休眠，第一次請求可能需要數十秒。如果正式網址因 Render 命名而不同，請以本儲存庫最新版本為準。

## 直接呼叫

```bash
curl -sS https://bvr-star.onrender.com/v1/charts/calculate \
  -H 'Content-Type: application/json' \
  --data @examples/chart-request.json
```

只有 GET 網頁讀取能力的 AI 可使用精簡入口：

```text
https://bvr-star.onrender.com/v1/charts/ai-context?birth_date=1983-06-15&birth_time=03%3A58%3A00&place=Lingya%20District%2C%20Kaohsiung%2C%20Taiwan&latitude=22.62177&longitude=120.312347&timezone=Asia%2FTaipei&time_accuracy_minutes=0&reference_date=2026-08-21
```

AI 應先從可查證地圖資料取得緯度、經度與 IANA 時區，再將三者一起傳入；BVR-Star 會處理出生年份的歷史 UTC offset。它仍使用相同計算核心，但只回傳適合語言模型閱讀的資料。GET 會將出生資料放進網址，可能留在瀏覽器或網路基礎設施紀錄；重視隱私時請使用 POST。

完整請求：

```json
{
  "birth": {
    "date": "1983-06-15",
    "time": "03:58:00",
    "place": "Lingya District, Kaohsiung City, Taiwan",
    "latitude": 22.6265,
    "longitude": 120.312,
    "timezone": "Asia/Taipei",
    "time_accuracy_minutes": 0
  },
  "settings": {"profile": "bvr_raman_v1"},
  "options": {
    "include": ["full", "llm_context"],
    "dasha_depth": 3,
    "reference_date": "2026-08-21",
    "output_language": "zh-TW"
  }
}
```

若只傳 `place`，服務會透過 Nominatim 解析地址並由座標推導時區。正式或可重複計算建議直接傳 `latitude`、`longitude`、IANA `timezone`；三者必須一起提供。

## 給 AI 直接使用

把以下文字貼給支援網路工具或 HTTP Action 的 AI：

> 使用 <https://github.com/Omurok/BVR-Star> 的計算慣例。先收集我的出生日期、出生地當地時間、出生地與時間準確度，再 POST 至 `https://bvr-star.onrender.com/v1/charts/calculate`。只使用 API JSON 中的計算數值，不自行重算。把計算事實、傳統占星規則與綜合解讀分開，並依 `warnings` 和 `sensitivity` 降低不穩定結論的強度。報告涵蓋性格、家庭、事業、姻緣、財富、長相、健康與大運；過往事件只列為附日期與證據 ID 的待驗證假設。除非我指定，稱盤主為「命主」，不要把命主預設為帳號主人。說明占星並非科學診斷，不冒充 B. V. Raman 本人。

更完整、可直接複製的版本在 [繁體中文 Prompt](prompts/zh-TW/full-reading.md)。AI 平台可把 [`openapi.json`](https://bvr-star.onrender.com/openapi.json) 匯入成 Action / Tool。

## 本機安裝

需要 Python 3.11 與 [uv](https://docs.astral.sh/uv/)：

```bash
uv python install 3.11
uv sync
uv run python scripts/fetch_ephemeris.py --output ephe
uv run bvr-star calculate --input examples/chart-request.json
```

啟動 API：

```bash
BVR_EPHE_PATH=ephe uv run bvr-star serve --host 0.0.0.0 --port 8000
```

Python：

```python
import json
from bvr_star import ChartRequest, ChartService

payload = json.load(open("examples/chart-request.json", encoding="utf-8"))
result = ChartService().calculate(ChartRequest.model_validate(payload))
print(result.model_dump_json(indent=2))
```

CLI：

```text
bvr-star calculate --input INPUT.json [--output OUTPUT.json]
bvr-star resolve-location "ADDRESS"
bvr-star config
bvr-star prompt --language zh-TW
bvr-star serve --host 127.0.0.1 --port 8000
```

## 輸出內容

- `provenance`：引擎、設定檔、星曆來源與歲差值
- `chart`：D1 上升、MC、行星、宮位、宮主、月宿與 Pada
- `vargas`：D2、D3、D4、D7、D9、D10、D12、D16、D20、D24、D27、D30、D40、D45、D60
- `dashas`：最多三層 Vimshottari 時間線及參考日有效週期
- `rules`：尊貴度、合相、相位及保守瑜伽條件，每項附證據
- `sensitivity`：依出生時間誤差上下界重算後的穩定與變動項目
- `llm_context`：由同一份型別資料濃縮，供語言模型直接使用

出生時間留空時回傳 `date_range`，列出當地民用日的行星範圍與跨界，並省略所有時間敏感欄位。程式不會偷偷建立 12:00 命盤。

## 計算與限制

完整說明見：

- [計算慣例](docs/calculation-conventions.md)
- [API 與 AI 整合](docs/api-and-ai-integration.md)
- [自行託管與 Render](docs/self-hosting.md)
- [第三方授權](THIRD_PARTY_NOTICES.md)

公開 API 不建立帳號，也不由應用程式保存出生資料或回應。基礎設施與呼叫端仍可能有自己的網路日誌；敏感資料建議自行託管。地址解析預設每 IP 每分鐘 5 次，星盤計算 30 次，本文上限 16 KiB。

## 授權

原始碼採 [AGPL-3.0-or-later](LICENSE)。Swiss Ephemeris 使用 AGPL／專業授權雙軌；閉源或不符合 AGPL 的部署須自行取得適用的專業授權。
