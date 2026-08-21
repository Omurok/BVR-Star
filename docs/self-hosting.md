# 自行託管

## Docker

```bash
docker build -t bvr-star .
docker run --rm -p 8000:8000 bvr-star
```

開啟 `http://localhost:8000/docs`。映像建置時會下載兩個固定 Swiss Ephemeris 檔並驗證 SHA-256。

## Render

在 Render 建立 Blueprint 並選擇 `Omurok/BVR-Star`；`render.yaml` 已定義 Docker、免費方案、`/health` 及自動部署。若 `bvr-star` 名稱已被佔用，Render 會提供不同網址，請同步更新 README 和 Prompt。

可調整 `BVR_CHART_RATE`、`BVR_GEOCODE_RATE`、`BVR_MAX_BODY_BYTES`。正式服務若需要穩定延遲，請選擇不休眠方案。

本專案使用 Swiss Ephemeris，因此網路部署也受 AGPL 條款約束。閉源部署應先取得適用的 Swiss Ephemeris 專業授權及法律意見。
