# BVR-Star 自訂 GPT Action 與通用網頁表單設計規格

日期：2026-08-21  
狀態：核心方向已由使用者核准，待規格確認  
目標儲存庫：`https://github.com/Omurok/BVR-Star`

## 1. 目標

讓一般 ChatGPT 使用者不需要閱讀 Swagger、撰寫 JSON、處理 HTTP POST，或理解印度星盤計算細節，即可輸入：

- 出生年月日；
- 出生時間；
- 出生地；

並由 BVR-Star 完成確定性的星盤計算，再由使用者選擇的 AI 模型負責自然語言解讀。

本次新增兩個公開入口：

1. BVR-Star 自訂 GPT 專用 Action；
2. 不需要帳號或 AI API 金鑰的通用網頁表單。

成功標準是：ChatGPT 使用者只需提供三項出生資料，自訂 GPT 就能自動呼叫 BVR-Star 並開始解讀；非 ChatGPT 使用者也能透過網頁取得同一套計算資料，再複製到任意 AI。

## 2. 已核准的產品決策

- 網頁採「計算與輸出」模式，不在網站內呼叫 OpenAI 或其他語言模型。
- 不要求部署者提供 OpenAI API 金鑰，因此沒有模型用量費用。
- 自訂 GPT 初期設為「知道連結者可用」，方便在 Threads 等平台分享與驗證。
- API、Action、網頁表單與隱私頁面全部由現有 Render 服務提供。
- 優先讓一般使用者快速完成操作，不把經緯度、IANA 時區、JSON 或 API 術語放在主要流程中。
- 網頁以繁體中文為主要語言。

## 3. 不在本次範圍內

- 網站直接產生 AI 星盤報告；
- 使用者帳號、登入、付款、星盤收藏或歷史紀錄；
- 資料庫、分析追蹤、廣告追蹤或行銷 Cookie；
- 自動發布到 GPT Store；
- 更改 BVR-Star 的星盤數學、分盤公式、大運算法或既有計算設定；
- 以網頁或 GPT 的文字邏輯重新計算星體、宮位、分盤或大運。

## 4. 整體架構

```text
自訂 GPT
  -> POST /v1/actions/calculate
  -> BVR-Star ChartService
  -> 精簡、具證據鏈的 Action JSON
  -> 自訂 GPT 依指令產生解讀

一般瀏覽器
  -> GET /
  -> 填寫出生資料
  -> POST /v1/charts/calculate
  -> 顯示計算摘要
  -> 複製給任意 AI / 下載完整 JSON
```

Action 與網頁表單共用既有 `ChartService`、資料模型及錯誤處理，不建立第二套計算流程。

## 5. 自訂 GPT Action

### 5.1 專用端點

新增：

```text
POST /v1/actions/calculate
```

端點使用適合 GPT Action 的扁平輸入，避免模型建立深層 `ChartRequest` 時遺漏欄位。

主要欄位：

- `birth_date`：必填，`YYYY-MM-DD`；
- `birth_time`：可省略，`HH:MM` 或 `HH:MM:SS`；
- `birth_place`：必填，使用者提供的出生地；
- `latitude`、`longitude`、`timezone`：三者可一起提供，作為已驗證位置；
- `time_accuracy_minutes`：預設 0；
- `reference_date`：可省略，供目前大運選取使用；
- `output_language`：第一版固定接受 `zh-TW`。

若只提供出生地，伺服器沿用既有地理解析流程。若 GPT 已可靠取得經緯度與 IANA 時區，則三者一起傳送，略過地理編碼並提高可重現性。

### 5.2 Action 回應

Action 不回傳完整約百 KB 的 `ChartResponse`，而回傳解讀所需的精簡資料：

- `schema_version`；
- `mode`；
- `location`；
- `time`；
- `provenance`；
- `llm_context`；
- `warnings`；
- `data_handling`。

回應必須保留 `llm_context` 中的事實、分盤、大運、規則證據、敏感度與警告，不把敘事性占星結論寫入 API。

### 5.3 Action OpenAPI

新增獨立、最小化的 Action Schema：

```text
GET /gpt/action-openapi.yaml
```

Schema 只公開一個 `operationId`：

```text
calculateBvrChart
```

它不匯入 BVR-Star 的完整 OpenAPI，以免 GPT 面對多個近似端點時選錯工具。Schema 的 server 固定指向：

```text
https://bvr-star.onrender.com
```

第一版不使用 Action 驗證，沿用公開 API 限流。

### 5.4 自訂 GPT 指令套件

儲存庫新增：

- `gpt/instructions-zh-TW.md`：可直接貼入 GPT Builder 的完整指令；
- `gpt/action-openapi.yaml`：Action Schema 原始檔；
- `gpt/conversation-starters.md`：建議開場問題；
- `docs/custom-gpt-setup.md`：非技術使用者可照做的建立與分享說明。

GPT 指令必須要求：

1. 缺少出生日期、出生時間或出生地時，以簡短問題補齊；出生時間未知時允許日期範圍模式。
2. 使用者不需要自己提供 JSON、經緯度或時區。
3. 資料足夠後自動呼叫 `calculateBvrChart`，不要求使用者再次輸入相同資料。
4. 只有 Action 成功回傳 BVR-Star JSON 後才能開始星盤解讀。
5. 星體度數、上升、宮位、分盤、大運與規則不得由 GPT 自行重算或覆蓋。
6. 地點不明確時，根據 API 候選向使用者確認，不自行猜測。
7. 報告涵蓋性格、家庭、事業、姻緣、財富、外貌、健康與人生階段。
8. 過往事件只能寫成可供核對的時間窗與可能主題，不得宣稱已經確定發生。
9. 清楚區分計算事實、傳統占星推論與不確定性。
10. 提醒占星不是科學驗證的診斷方式，健康與財務內容不得取代專業意見。

## 6. 通用網頁表單

### 6.1 公開網址

```text
GET /
```

首頁直接顯示表單，不要求使用者先閱讀文件。

### 6.2 主要欄位

第一屏只顯示：

- 出生日期；
- 出生時間；
- 出生地；
- 「開始計算」按鈕。

次要欄位放在「進階設定」折疊區：

- 出生時間可能誤差；
- 經緯度；
- IANA 時區；
- 分析參考日期。

欄位旁使用生活化說明，不要求使用者理解印度占星術語。

### 6.3 計算流程

瀏覽器以 same-origin POST 呼叫既有：

```text
POST /v1/charts/calculate
```

表單不把出生資料放進網址，也不把資料寫入 Local Storage、Session Storage、Cookie 或任何資料庫。

免費 Render 服務休眠時，送出後顯示：

```text
服務可能正在喚醒，第一次計算約需數十秒，請不要重複送出。
```

若 API 回傳地點不明確、時間無效、服務喚醒失敗或其他已知錯誤，畫面將錯誤翻譯成可行動的繁體中文提示。

### 6.4 結果頁

成功後顯示：

- 已解析的出生地、經緯度與時區；
- 計算設定及資料版本；
- 上升、月亮與主要大運等簡要計算摘要；
- API 警告與出生時間敏感度；
- 「複製完整 Prompt 給 AI」；
- 「下載完整 JSON」；
- 「重新輸入」。

「複製完整 Prompt 給 AI」會複製一份不依賴先前聊天脈絡、可直接貼到全新 ChatGPT、Claude、Gemini 或其他模型對話的繁體中文指令，後面附上本次完整 API 計算輸出。指令包含角色與資料界線、十二段報告結構、過往事件驗證規則、安全界線與完成檢查，並要求模型只解讀已計算資料，不自行重算星盤。頁面同時提供完整 Prompt 預覽，讓無法使用剪貼簿的使用者手動複製。

頁面不聲稱已提供 AI 解讀；它只顯示 BVR-Star 計算資料與轉交方式。

### 6.5 介面要求

- 手機優先、桌面可讀；
- 不依賴前端框架或外部 CDN；
- HTML、CSS、JavaScript 隨 Python 套件一起部署；
- 支援鍵盤操作與清楚的焦點狀態；
- 日期、時間與錯誤提示具可讀標籤；
- 避免過度神秘或宣稱必然準確的行銷語言；
- 提供 GitHub、API 文件、完整 Prompt 與隱私政策連結。

## 7. 隱私政策

新增：

```text
GET /privacy
```

頁面以繁體中文明確說明：

- BVR-Star 應用程式不建立帳號，也不把出生資料與計算結果保存至資料庫；
- POST 表單不把出生資料放在網址；
- Render、網路服務商或使用者所選 AI 平台仍可能依各自政策保留連線或對話紀錄；
- 若只輸入地址，服務會透過地理編碼供應商解析地點；
- 使用者將結果貼給第三方 AI 後，其處理由該平台政策管轄；
- 占星解讀不屬於科學診斷，不應取代醫療、法律或財務專業意見。

不得使用絕對性的「完全不留任何紀錄」字眼，因為部署平台可能保有基礎連線日誌。

## 8. 錯誤與限制

- Action 與表單沿用現有限流。
- Action 對缺少欄位回傳短而清楚的結構化錯誤，讓 GPT 能直接追問。
- 對 Render 冷啟動或 503，GPT 指令允許以同一參數重試一次。
- 對 DNS、平台禁止外部連線或 Action 權限問題，不假裝已取得結果，改提供網頁表單網址。
- GET `/v1/charts/ai-context` 保留作一般唯讀網頁工具相容入口，但自訂 GPT 與新表單優先使用 POST。

## 9. 部署與分享流程

程式推送至 GitHub `main` 後，由已連接的 Render 服務自動部署。

部署完成後，建立自訂 GPT 時：

1. 貼入 `gpt/instructions-zh-TW.md`；
2. 將 `https://bvr-star.onrender.com/gpt/action-openapi.yaml` 匯入 Action；
3. 設定隱私政策 URL 為 `https://bvr-star.onrender.com/privacy`；
4. 測試一筆已知出生資料；
5. 設為「知道連結者可用」；
6. 將 GPT 分享連結與通用表單網址貼到 Threads。

自訂 GPT 的建立與分享屬 ChatGPT 帳號內的外部狀態變更；在實際按下發布或分享前，需由使用者確認。

## 10. 驗收條件

- 一般使用者在自訂 GPT 只輸入出生日期、時間與地點，即可觸發一次正確的 Action 呼叫。
- Action Schema 只有一個計算 operation，無須使用者理解 API 欄位。
- Action 回應包含解讀必需的 BVR-Star 證據，但不回傳不必要的完整大型 JSON。
- `/` 可在手機與桌面完成填寫、計算、複製 AI 內容及下載 JSON。
- 表單不使用 GET 傳送出生資料，也不寫入瀏覽器持久儲存。
- `/privacy`、GitHub、API 文件與 Prompt 連結可從首頁直接到達。
- 網站與 Action 不使用 OpenAI API 金鑰，也不在伺服器內產生 AI 解讀。
- 既有 POST API、GET AI 相容端點、CLI 與計算核心維持相容。
- 儲存庫包含可直接貼入 GPT Builder 的繁中指令、Action Schema 與非技術設定說明。

## 11. 實作原則

- 將 HTTP 輸入轉換與回應投影抽成小型共用函式，避免 GET、Action 與表單各自複製計算邏輯。
- 靜態資源透過 FastAPI 提供，並包含於 wheel 與 Docker 映像。
- 網頁不新增大型前端相依套件，以降低 Render 建置時間與維護成本。
- 不修改確定性的占星計算核心。
- 依使用者先前要求，本次不新增完整自動化測試套件；部署前只進行必要的格式與啟動檢查，避免阻礙快速上線。
