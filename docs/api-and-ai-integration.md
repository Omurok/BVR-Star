# API 與 AI 整合

公開端點為 `https://bvr-star.onrender.com`。一般使用者可直接開啟 `/`，自訂 GPT 應匯入 `/gpt/action-openapi.yaml`，完整開發者文件則位於 `/docs` 與 `/openapi.json`。

核心端點：

- `GET /`：不需要登入的繁中網頁表單
- `GET /privacy`：公開資料與隱私說明
- `GET /health`
- `GET /v1/config`
- `POST /v1/locations/resolve`
- `POST /v1/charts/calculate`
- `POST /v1/actions/calculate`：扁平輸入、精簡輸出的自訂 GPT 專用 Action
- `GET /v1/charts/ai-context`：供無法 POST 的一般 AI 網頁讀取工具使用
- `GET /gpt/action-openapi.yaml`：只含 `calculateBvrChart` 的 Action Schema
- `GET /v1/prompts/full-reading?language=zh-TW`

## 自訂 GPT

ChatGPT 自訂 GPT 應匯入 `/gpt/action-openapi.yaml`。該 Schema 只有一個 `calculateBvrChart` 操作，輸入欄位是 `birth_date`、`birth_time` 與 `birth_place` 等扁平資料；模型不必建立完整 `ChartRequest`。完整 Instructions 與建立步驟分別位於 `gpt/instructions-zh-TW.md` 與 `docs/custom-gpt-setup.md`。

Action 成功回傳後，模型必須把 `llm_context` 當成唯一星盤事實來源，不得自行重算度數、宮位、分盤與大運。Action 回應省略不必要的大型完整物件，但保留 `provenance`、地點、時間、規則證據、大運時間線、敏感度與警告。

## 通用 API 工具

一般開發者可匯入 `/openapi.json`，再把出生資料轉為 `ChartRequest`。建議先要求精確日期、地方時間、地址與時間誤差。知道經緯度和 IANA 時區時一起傳入，可避免地理編碼歧義並提高可重複性。

只有 GET 能力的聊天環境可以開啟：

```text
https://bvr-star.onrender.com/v1/charts/ai-context?birth_date=1983-06-15&birth_time=03%3A58%3A00&place=Lingya%20District%2C%20Kaohsiung%2C%20Taiwan&latitude=22.62177&longitude=120.312347&timezone=Asia%2FTaipei&time_accuracy_minutes=0&reference_date=2026-08-21
```

AI 應先透過可查證的地圖或地理資料取得緯度、經度及 IANA 時區，三者一起傳入；不要自行計算出生年的 UTC offset，歷史時區規則由 BVR-Star 處理。此端點回傳精簡但可回溯的 `llm_context`。GET 查詢字串可能留在瀏覽器歷史、代理、AI 網頁工具或平台日誌中；API 會加入 `GET_QUERY_CONTAINS_BIRTH_DATA` 警告。應用程式不持久保存資料，但對隱私敏感的使用者仍應使用 POST。

成功後先讀 `mode`。`complete` 可使用 `llm_context` 撰寫報告，必要時回查完整 `chart`、`vargas`、`dashas`、`rules`。`date_range` 僅能處理全日穩定資料。完整繁中指令在 `prompts/zh-TW/full-reading.md`。

Render 免費實例可能休眠；第一次呼叫可能需要數十秒。遇到 503 可稍後重試，遇到 422 應依 `error.code` 修正輸入，遇到 429 應等待後再呼叫。不要自動反覆解析同一地址。

BVR-Star 應用程式不把請求或回應寫入資料庫，但呼叫者、AI 平台與基礎設施仍可能有自己的日誌政策。網頁表單使用 POST，並且不使用瀏覽器持久儲存。若資料敏感，請閱讀 `/privacy`、考慮自行託管並直接傳經緯度與時區。
