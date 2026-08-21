"use strict";

const chartForm = document.querySelector("#chartForm");
const intakeSection = document.querySelector("#intakeSection");
const stepsSection = document.querySelector("#how-it-works");
const resultSection = document.querySelector("#resultSection");
const resultHeading = document.querySelector("#resultHeading");
const submitButton = document.querySelector("#submitButton");
const formStatus = document.querySelector("#formStatus");
const summaryList = document.querySelector("#summaryList");
const warningPanel = document.querySelector("#warningPanel");
const warningList = document.querySelector("#warningList");
const aiPromptPreview = document.querySelector("#aiPromptPreview");
const technicalJson = document.querySelector("#technicalJson");
const copyButton = document.querySelector("#copyButton");
const downloadButton = document.querySelector("#downloadButton");
const resetButton = document.querySelector("#resetButton");
const copyStatus = document.querySelector("#copyStatus");
const advancedSettings = document.querySelector("#advancedSettings");

let currentResult = null;

const planetNames = {
  sun: "太陽",
  moon: "月亮",
  mars: "火星",
  mercury: "水星",
  jupiter: "木星",
  venus: "金星",
  saturn: "土星",
  rahu: "羅喉",
  ketu: "計都",
};

const warningMessages = {
  BIRTH_TIME_MISSING: "出生時間未知，本次只計算整日穩定的行星範圍。",
  TIME_SENSITIVE_FIELDS_OMITTED: "上升、宮位、分盤上升與大運餘額等時間敏感欄位已省略。",
  GET_QUERY_CONTAINS_BIRTH_DATA: "這筆資料曾透過 GET 網址傳送；網址可能留在瀏覽紀錄。",
};

class UserFacingError extends Error {}

function fieldValue(id) {
  return document.querySelector(`#${id}`).value.trim();
}

function buildPayload() {
  const latitude = fieldValue("latitude");
  const longitude = fieldValue("longitude");
  const timezone = fieldValue("timezone");
  const coordinateCount = [latitude, longitude, timezone].filter(Boolean).length;

  if (coordinateCount > 0 && coordinateCount < 3) {
    throw new UserFacingError("經緯度與 IANA 時區必須一起填寫，或三項全部留空。");
  }

  const birthTime = fieldValue("birthTime");
  const referenceDate = fieldValue("referenceDate");
  const timeAccuracy = Number.parseInt(fieldValue("timeAccuracy") || "0", 10);
  const birth = {
    date: fieldValue("birthDate"),
    place: fieldValue("birthPlace"),
    time_accuracy_minutes: birthTime ? timeAccuracy : 0,
  };

  if (birthTime) birth.time = birthTime;
  if (coordinateCount === 3) {
    birth.latitude = Number.parseFloat(latitude);
    birth.longitude = Number.parseFloat(longitude);
    birth.timezone = timezone;
  }

  const options = {
    include: ["full", "llm_context"],
    dasha_depth: 3,
    output_language: "zh-TW",
  };
  if (referenceDate) options.reference_date = referenceDate;

  return {
    birth,
    settings: {profile: "bvr_raman_v1"},
    options,
  };
}

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  submitButton.setAttribute("aria-busy", String(isLoading));
  submitButton.textContent = isLoading ? "正在計算…" : "開始計算";
}

function clearFormStatus() {
  formStatus.textContent = "";
  formStatus.classList.remove("is-error");
}

function showError(message) {
  formStatus.textContent = message;
  formStatus.classList.add("is-error");
  formStatus.scrollIntoView({behavior: "smooth", block: "center"});
}

function apiErrorMessage(payload, status) {
  const error = payload?.error;
  if (!error) return `計算服務回傳錯誤（HTTP ${status}），請稍後再試。`;

  const known = {
    LOCATION_NOT_FOUND: "找不到這個出生地。請加入行政區、城市與國家後再試。",
    GEOCODER_UNAVAILABLE: "出生地解析服務暫時不可用，請稍後再試。",
    EPHEMERIS_UNAVAILABLE: "星曆計算服務暫時不可用，請稍後再試。",
    TIMEZONE_NOT_FOUND: "無法從這個地點判定時區，請在進階設定填入經緯度與 IANA 時區。",
    LOCAL_TIME_NONEXISTENT: "這個當地時間因夏令時間調整而不存在，請核對出生時間。",
    LOCAL_TIME_AMBIGUOUS: "這個當地時間因夏令時間回撥而出現兩次，請改用 API 指定 fold。",
    RATE_LIMIT_EXCEEDED: "短時間內計算次數過多，請稍候一分鐘再試。",
    INPUT_VALIDATION_ERROR: "出生資料格式不完整，請檢查日期、時間與進階欄位。",
  };

  if (error.code === "LOCATION_AMBIGUOUS") {
    const candidates = error.details?.candidates || [];
    const names = candidates.slice(0, 3).map((item) => item.display_name).filter(Boolean);
    const suffix = names.length ? ` 可能地點：${names.join("；")}` : "";
    return `出生地不夠明確，請加入更完整的行政區、城市與國家。${suffix}`;
  }

  return known[error.code] || error.message || `計算服務回傳錯誤（HTTP ${status}）。`;
}

function formatDegree(placement) {
  if (!placement || typeof placement.degree !== "number") return "—";
  let degrees = Math.floor(placement.degree);
  let minutes = Math.round((placement.degree - degrees) * 60);
  if (minutes === 60) {
    degrees += 1;
    minutes = 0;
  }
  return `${placement.sign || placement.sign_key || ""} ${degrees}°${String(minutes).padStart(2, "0")}′`;
}

function dashaLabel(activePath) {
  if (!Array.isArray(activePath) || activePath.length === 0) return "—";
  return activePath
    .map((period, index) => {
      const name = planetNames[period.lord] || period.lord;
      if (index === 0) return `${name}大運`;
      return name;
    })
    .join(" → ");
}

function addSummaryRow(label, value) {
  const row = document.createElement("div");
  row.className = "summary-row";
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = value || "—";
  row.append(term, description);
  summaryList.append(row);
}

function renderWarnings(data) {
  const warnings = [...(data.warnings || [])];
  const changed = data.sensitivity?.changed || data.llm_context?.sensitivity?.changed || [];
  if (changed.length) {
    warnings.push(`出生時間誤差會影響：${changed.join("、")}。解讀時應保留不確定性。`);
  }

  warningList.replaceChildren();
  warnings.forEach((warning) => {
    const item = document.createElement("li");
    item.textContent = warningMessages[warning] || warning;
    warningList.append(item);
  });
  warningPanel.hidden = warnings.length === 0;
}

function renderResult(data) {
  currentResult = data;
  summaryList.replaceChildren();

  addSummaryRow("解析地點", data.location?.display_name);
  if (data.mode === "complete") {
    addSummaryRow("當地時間", data.time?.local_datetime?.replace("T", " "));
    addSummaryRow("時區", data.time?.timezone || data.location?.timezone);
    addSummaryRow("上升", formatDegree(data.llm_context?.ascendant));
    addSummaryRow("月亮", formatDegree(data.llm_context?.planets?.moon));
    addSummaryRow("目前大運", dashaLabel(data.llm_context?.active_dasha));
  } else {
    const localRange = [data.time?.start_local, data.time?.end_local]
      .filter(Boolean)
      .map((value) => value.replace("T", " "))
      .join(" ～ ");
    addSummaryRow("計算範圍", localRange);
    addSummaryRow("時區", data.time?.timezone || data.location?.timezone);
    addSummaryRow("時間敏感項目", "未計算上升、宮位、分盤上升與大運餘額");
  }

  renderWarnings(data);
  technicalJson.textContent = JSON.stringify(data, null, 2);
  aiPromptPreview.textContent = aiPromptText();
  copyStatus.textContent = "";
  intakeSection.hidden = true;
  stepsSection.hidden = true;
  resultSection.hidden = false;
  resultHeading.focus({preventScroll: true});
  resultSection.scrollIntoView({behavior: "smooth", block: "start"});
}

function aiPromptText() {
  const instructions = `# BVR-Star 印度星盤完整解讀任務

這是一份可以貼進全新 AI 對話、獨立完成的任務。不要假設你讀過任何先前對話，也不要再要求使用者提供出生資料；本 Prompt 尾端已附上出生資料及 BVR-Star 的完整程式計算結果。

## 角色與資料界線

你是一位嚴謹的印度占星報告撰寫助手，不冒充 Bangalore Venkata Raman 本人。以下 JSON 已由 BVR-Star 依 Raman Ayanamsha、恆星黃道、平均月交點、整宮制、Parashari 規則及 Vimshottari 大運完成確定性計算。

- 只能使用 JSON 中的 chart、vargas、dashas、rules、llm_context、warnings、sensitivity、location、time 與 provenance 作為星盤事實。
- 不得自行重算、猜測、修正或覆寫星體度數、星座、月宿、Pada、上升、宮位、分盤、相位與大運。
- 清楚區分「程式計算事實」「傳統占星規則結果」與「綜合解讀」，不可把解讀寫成已科學證實的事實。
- 除非資料另有說明，全文稱盤主為「命主」，不要預設命主是帳號本人，也不要從其他對話或個人資料反向校準。

## 開始前核對

先簡短列出並核對：出生日期、出生地當地時間、解析地點、經緯度、IANA 時區、計算模式、Raman 設定、參考日期、資料來源版本及所有 warnings。若 mode 是 date_range，只能分析整日穩定資料；不得補猜上升、宮位、分盤上升、大運出生餘額、婚期或精確事件時間。

## 報告內容

請以繁體中文撰寫客觀、全面、可核對的完整報告，依序包含：

1. 資料、方法、可信度與限制；
2. 命盤骨架、最強結構及主要證據；
3. 性格、思考、情緒、優勢與盲點；
4. 外貌、氣質及他人第一印象；
5. 原生家庭、父母、手足、居住與家族課題；
6. 學習、技能、事業型態、工作環境、合作與發展階段；
7. 感情模式、姻緣、親密需求、配偶互動與婚姻課題；
8. 財富來源、收入、資產、風險及資源管理；
9. 健康與壓力傾向，只作一般生活反思，不作醫療診斷；
10. Vimshottari 大運、次運與重要人生階段，標明起訖日期；
11. 三至六個過往事件待驗證時間窗；
12. 證據索引、不確定性及可向命主追問的驗證問題。

每一大段優先列出直接依據，例如星體、宮位、分盤、大運路徑、important_rule_facts 或 evidence IDs。若結論涉及 sensitivity.changed，必須降低語氣強度並明示不確定性。

## 過往事件驗證規則

每個時間窗都要列出日期區間、相對應的大運／次運或規則證據、最可能的事件主題及至少一種替代可能。只能使用「可能」「較容易」「值得核對」等措辭，不得聲稱事件已確定發生，也不得利用未提供的人生經歷迎合結果。

## 安全與表述

避免奉承、恐嚇、宿命論及必然事件。占星是傳統象徵框架，不是經科學驗證的人格診斷或預測工具。健康、財務、法律與關係內容不得取代合格專業意見；不得診斷疾病、建議停藥、保證獲利，或斷言死亡、重病、離婚、犯罪與破產。

## 完成前檢查

確認所有精確數字都能回指附帶 JSON；已反映 warnings 與 sensitivity；三類資訊已明確區分；事件驗證均標為假設；沒有自行重算星盤。

## BVR-Star 完整計算結果
`;
  return `${instructions}\n\n${JSON.stringify(currentResult, null, 2)}`;
}

async function writeClipboard(text) {
  if (navigator.clipboard?.writeText) {
    await navigator.clipboard.writeText(text);
    return;
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  const copied = document.execCommand("copy");
  textarea.remove();
  if (!copied) throw new Error("Clipboard unavailable");
}

async function copyForAi() {
  if (!currentResult) return;
  copyButton.disabled = true;
  try {
    await writeClipboard(aiPromptText());
    copyStatus.textContent = "完整 Prompt 已複製，可直接貼到全新的 AI 對話。";
  } catch {
    copyStatus.textContent = "瀏覽器無法自動複製，請展開完整 Prompt 並手動複製。";
  } finally {
    copyButton.disabled = false;
  }
}

function downloadJson() {
  if (!currentResult) return;
  const date = currentResult.request?.birth?.date || fieldValue("birthDate") || "chart";
  const blob = new Blob([JSON.stringify(currentResult, null, 2)], {type: "application/json"});
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `bvr-star-${date}.json`;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 0);
  copyStatus.textContent = "完整 JSON 已開始下載。";
}

function resetForm() {
  currentResult = null;
  chartForm.reset();
  advancedSettings.open = false;
  summaryList.replaceChildren();
  warningList.replaceChildren();
  aiPromptPreview.textContent = "";
  technicalJson.textContent = "";
  copyStatus.textContent = "";
  clearFormStatus();
  resultSection.hidden = true;
  intakeSection.hidden = false;
  stepsSection.hidden = false;
  document.querySelector("#intakeHeading").focus?.({preventScroll: true});
  intakeSection.scrollIntoView({behavior: "smooth", block: "start"});
}

async function calculate(event) {
  event.preventDefault();
  clearFormStatus();
  if (!chartForm.reportValidity()) return;

  let payload;
  try {
    payload = buildPayload();
  } catch (error) {
    showError(error.message);
    return;
  }

  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 120000);
  const wakeMessage = window.setTimeout(() => {
    formStatus.textContent = "服務可能正在喚醒，第一次計算約需數十秒，請不要重複送出。";
  }, 12000);

  setLoading(true);
  formStatus.textContent = "正在連接 BVR-Star 並計算星盤…";

  try {
    const response = await fetch("/v1/charts/calculate", {
      method: "POST",
      headers: {"Content-Type": "application/json", Accept: "application/json"},
      body: JSON.stringify(payload),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new UserFacingError(apiErrorMessage(data, response.status));
    if (!data) throw new UserFacingError("計算服務沒有回傳可讀資料，請稍後再試。");
    renderResult(data);
  } catch (error) {
    if (error.name === "AbortError") {
      showError("等待超過兩分鐘。Render 服務可能仍在喚醒，請稍後重新送出一次。");
    } else if (error instanceof UserFacingError) {
      showError(error.message);
    } else {
      showError("無法連接計算服務。請檢查網路，稍後再試一次。");
    }
  } finally {
    window.clearTimeout(timeout);
    window.clearTimeout(wakeMessage);
    setLoading(false);
  }
}

chartForm.addEventListener("submit", calculate);
copyButton.addEventListener("click", copyForAi);
downloadButton.addEventListener("click", downloadJson);
resetButton.addEventListener("click", resetForm);
