import { useMemo } from "react";
import { useAuth } from "../context/AuthContext";

const COPY = {
  eyebrow: "今日日誌",
  title: "加入今日已攝取的餐點",
  totalCalories: "今日總熱量",
  totalCount: "今日筆數",
  add: "加入今日日誌",
  loginToAdd: "先登入會員再加入日誌",
  needEntry: "請先準備一筆要加入的餐點",
  empty: "目前今天還沒有任何餐點紀錄，先從圖片分析或手動輸入開始。",
  remove: "刪除這筆",
  pendingTitle: "待加入紀錄",
  aiSource: "資料來源：AI 分析",
  manualSource: "資料來源：手動輸入",
  sourceSwitch: "加入來源",
  sourceAi: "AI 分析",
  sourceManual: "手動輸入",
};

function formatTime(value) {
  if (!value) {
    return "--:--";
  }

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleTimeString("zh-TW", {
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });
}

function TodayJournalSection({
  currentEntry,
  aiEntry,
  manualEntry,
  selectedSourceMode,
  onSelectSource,
  todayEntries,
  summary,
  onAddEntry,
  onPromptRegister,
  onRemoveEntry,
}) {
  const { isMemberLoggedIn, memberName, demoMemberAccount } = useAuth();

  const activeSource = useMemo(() => {
    if (selectedSourceMode === "ai" && aiEntry) {
      return "ai";
    }

    if (selectedSourceMode === "manual" && manualEntry) {
      return "manual";
    }

    if (currentEntry?.source === "manual_lookup" || !aiEntry) {
      return manualEntry ? "manual" : "";
    }

    return aiEntry ? "ai" : "";
  }, [aiEntry, currentEntry?.source, manualEntry, selectedSourceMode]);

  const helperText = useMemo(() => {
    if (isMemberLoggedIn) {
      return `${memberName || "示範會員"} 今天已加入 ${summary.count} 筆餐點。`;
    }

    return `登入會員後就能把分析結果或手動輸入加入日誌。示範帳號：${demoMemberAccount}`;
  }, [demoMemberAccount, isMemberLoggedIn, memberName, summary.count]);

  const sourceLabel = activeSource === "manual" ? COPY.manualSource : COPY.aiSource;

  return (
    <section className="panel-card today-journal-card">
      <div className="section-heading">
        <p className="eyebrow">{COPY.eyebrow}</p>
        <h2>{COPY.title}</h2>
      </div>

      <p className="today-journal-helper">{helperText}</p>

      <div className="today-journal-summary">
        <div className="journal-summary-metric">
          <span>{COPY.totalCalories}</span>
          <strong>{summary.calories || 0} kcal</strong>
        </div>
        <div className="journal-summary-metric">
          <span>{COPY.totalCount}</span>
          <strong>{summary.count}</strong>
        </div>
      </div>

      {currentEntry ? (
        <div className="today-journal-pending">
          <div className="today-journal-pending-header">
            <strong>{COPY.pendingTitle}</strong>
            <span>{sourceLabel}</span>
          </div>

          {aiEntry && manualEntry ? (
            <div className="today-journal-source-switch">
              <span>{COPY.sourceSwitch}</span>
              <div className="today-journal-source-buttons">
                <button
                  type="button"
                  className={`today-journal-source-button ${activeSource === "ai" ? "is-active" : ""}`}
                  onClick={() => onSelectSource("ai")}
                >
                  {COPY.sourceAi}
                </button>
                <button
                  type="button"
                  className={`today-journal-source-button ${activeSource === "manual" ? "is-active" : ""}`}
                  onClick={() => onSelectSource("manual")}
                >
                  {COPY.sourceManual}
                </button>
              </div>
            </div>
          ) : null}

          <div className="today-journal-pending-body">
            <div>
              <strong>{currentEntry.food_name}</strong>
              <p>{currentEntry.portion_label}</p>
            </div>
            <div className="today-journal-pending-macros">
              <span>熱量 {currentEntry.nutrition.calories} kcal</span>
              <span>蛋白質 {currentEntry.nutrition.protein} g</span>
              <span>脂肪 {currentEntry.nutrition.fat} g</span>
              <span>碳水 {currentEntry.nutrition.carbs} g</span>
            </div>
          </div>
        </div>
      ) : null}

      <div className="today-journal-action">
        {isMemberLoggedIn ? (
          <button type="button" className="primary-button" onClick={onAddEntry} disabled={!currentEntry}>
            {currentEntry ? COPY.add : COPY.needEntry}
          </button>
        ) : (
          <button type="button" className="primary-button" onClick={onPromptRegister}>
            {COPY.loginToAdd}
          </button>
        )}
      </div>

      {todayEntries.length === 0 ? (
        <p className="muted-text">{COPY.empty}</p>
      ) : (
        <div className="history-grid">
          {todayEntries.map((entry) => (
            <article className="history-card today-journal-entry" key={entry.id}>
              <div className="history-thumb">
                {entry.image_preview ? (
                  <img src={entry.image_preview} alt={entry.food_name} className="preview-image" />
                ) : (
                  <div className="history-thumb-placeholder">{entry.food_name}</div>
                )}
              </div>
              <div className="history-meta">
                <strong>{entry.food_name}</strong>
                <span>{entry.portion_label}</span>
                <small>
                  {entry.nutrition.calories} kcal · {formatTime(entry.created_at)}
                </small>
                <button
                  type="button"
                  className="manual-lookup-clear"
                  onClick={() => onRemoveEntry(entry.id)}
                >
                  {COPY.remove}
                </button>
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

export default TodayJournalSection;
