# 建立 BVR-Star 自訂 GPT

這份說明讓非技術使用者把 BVR-Star 接成 ChatGPT 自訂 GPT Action。完成後，使用者只要輸入出生日期、出生時間與出生地，GPT 就會自動取得程式計算結果，再由目前使用的模型負責解讀。

## 準備好的公開網址

- 通用表單：<https://bvr-star.onrender.com/>
- Action Schema：<https://bvr-star.onrender.com/gpt/action-openapi.yaml>
- 隱私政策：<https://bvr-star.onrender.com/privacy>
- API 文件：<https://bvr-star.onrender.com/docs>

## GPT 基本資料

- 名稱：`BVR-Star 印度星盤分析`
- 說明：`輸入出生日期、時間與地點，先由開源程式精準排出 Raman 印度星盤，再由 ChatGPT 依計算結果解讀。`
- Instructions：完整複製 [`gpt/instructions-zh-TW.md`](../gpt/instructions-zh-TW.md)
- Conversation starters：逐行複製 [`gpt/conversation-starters.md`](../gpt/conversation-starters.md)

## 加入 Action

1. 在 ChatGPT 的 GPT 編輯器建立一個新的 GPT。
2. 貼上名稱、說明、Instructions 與 Conversation starters。
3. 進入 Actions，選擇建立新的 Action。
4. Authentication 選擇 `None`。
5. 匯入：`https://bvr-star.onrender.com/gpt/action-openapi.yaml`。
6. 確認工具只出現一個操作：`calculateBvrChart`。
7. 隱私政策網址填入：`https://bvr-star.onrender.com/privacy`。

如果編輯器不接受遠端匯入，就打開 Action Schema 網址，複製全部 YAML 後貼入 Schema 欄位。

## 發布前核對

用下列資料測試：

```text
出生日期：1983-06-15
出生時間：03:58
出生地：台灣高雄市苓雅區
```

預期行為：

1. GPT 自動呼叫 `calculateBvrChart`，不要求使用者撰寫 JSON。
2. 成功回傳後才開始解讀。
3. 解析時區為 `Asia/Taipei`。
4. 主要計算資料包含金牛上升、巨蟹月亮及 Vimshottari 大運內容。
5. GPT 不宣稱占星是科學診斷，也不把推測事件寫成已發生事實。

Render 免費服務閒置後可能需要數十秒喚醒。503 或 timeout 可用相同參數重試一次；不要因為第一次較慢就更改出生資料。

## 分享方式

初期建議選擇「知道連結者可用」，先把連結分享給實際使用者。實際按下發布會改變 ChatGPT 帳號中的公開狀態，應由 GPT 擁有者在發布當下確認。

這個 Action 只把出生資料送到 BVR-Star 計算，BVR-Star 應用程式不建立星盤資料庫。Render 等基礎設施及 ChatGPT 對話仍可能依各自政策保留紀錄，詳細內容請看公開隱私政策。
