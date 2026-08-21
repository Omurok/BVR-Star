# API 與 AI 整合

公開端點預定為 `https://bvr-star.onrender.com`。互動文件在 `/docs`，工具 Schema 在 `/openapi.json`。

核心端點：

- `GET /health`
- `GET /v1/config`
- `POST /v1/locations/resolve`
- `POST /v1/charts/calculate`
- `GET /v1/prompts/full-reading?language=zh-TW`

AI 工具只需匯入 `/openapi.json`，再把使用者出生資料轉為 `ChartRequest`。建議先要求精確日期、地方時間、地址與時間誤差。知道經緯度和 IANA 時區時一起傳入，可避免地理編碼歧義並提高可重複性。

成功後先讀 `mode`。`complete` 可使用 `llm_context` 撰寫報告，必要時回查完整 `chart`、`vargas`、`dashas`、`rules`。`date_range` 僅能處理全日穩定資料。完整繁中指令在 `prompts/zh-TW/full-reading.md`。

Render 免費實例可能休眠；第一次呼叫可能需要數十秒。遇到 503 可稍後重試，遇到 422 應依 `error.code` 修正輸入，遇到 429 應等待後再呼叫。不要自動反覆解析同一地址。

服務不保存本文，但呼叫者與基礎設施仍可能有自己的日誌政策。若資料敏感，請自行託管並直接傳經緯度與時區。
