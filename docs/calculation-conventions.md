# 計算慣例

`bvr_raman_v1` 固定使用恆星黃道、Swiss Ephemeris 的 Raman Ayanāṃśa (`SIDM_RAMAN`)、平均月交點、Parāśari 整宮制與傳統 graha drishti。支援 1900-01-01 至 2099-12-31。

出生地的地方民用時間先以 IANA 時區資料轉為 UTC；歷史 UTC offset 由該日期的時區規則決定。夏令時間重疊必須傳 `fold: 0` 或 `fold: 1`。不存在的民用時間會回傳錯誤。傳入經緯度與 IANA 時區時完全略過地址解析。

天文層使用 `pyswisseph==2.10.3.2`，要求 `FLG_SWIEPH | FLG_SIDEREAL | FLG_SPEED`。回應會記錄實際 return flags、星曆來源、函式庫版本與 Raman 歲差值；如果 Swiss 檔案缺失而退回 Moshier，會加入 `EPHEMERIS_FALLBACK` 警告。

D1 使用整宮制。每個星體輸出 0–360 度經度、星座內度數、月宿、Pada、逆行、宮位及證據 ID。Ketu 為 mean Rahu 對點。

支援 D2、D3、D4、D7、D9、D10、D12、D16、D20、D24、D27、D30、D40、D45、D60，規則集 ID 為 `parasari_shodashavarga_v1`。分盤同時輸出距最近邊界的度數；出生時間準確度大於零時，服務會在誤差上下界重算並列出變動項目。

Vimshottari 採 120 年週期及 365.25 日年，從月亮月宿中的實際進度計算出生餘額，最多輸出 Mahadasha、Antardasha、Pratyantardasha 三層。日期是模型慣例下的時間尺度，不應假裝成必然事件日期。

`bvr_rules_v1` 只輸出可稽核的尊貴度、整宮相位、8 度內合相及少量保守瑜伽條件。規則結果不是人生事件。AI 應把計算事實、規則結果與綜合解讀分開。

沒有出生時間時，服務以完整當地民用日的 UTC 起迄計算行星範圍和跨界，省略上升、宮位、分盤上升、大運出生餘額與時間敏感規則；不虛構中午。
