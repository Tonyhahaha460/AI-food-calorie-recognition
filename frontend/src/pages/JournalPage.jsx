import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchFoodProfiles } from "../api/foodProfilesApi";
import Layout from "../components/Layout";
import { useAuth } from "../context/AuthContext";
import {
  ACTIVITY_LEVEL_OPTIONS,
  calculateBmr,
  calculateFatLossTarget,
  calculateTdee,
  getActivityOption,
} from "../utils/bmr";
import {
  listMemberJournalEntries,
  removeJournalEntry,
  summarizeJournalEntries,
  updateJournalEntry,
} from "../utils/memberJournal";

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
const JOURNAL_UI_VERSION = "2026-04-14.2";

const dateKey = (value = new Date()) =>
  `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;

const dateTitle = (value = "") => String(value).replaceAll("-", "/") || "--";

function parseDateKey(value) {
  const [y, m, d] = String(value || "").split("-");
  return y && m && d ? new Date(Number(y), Number(m) - 1, Number(d), 12) : new Date();
}

function monthTitle(value) {
  return `${value.getFullYear()}年${value.getMonth() + 1}月`;
}

function remaining(value) {
  return Math.max(0, Math.round(Number(value || 0)));
}

function proteinTarget(weightKg, mode) {
  return Math.round(Number(weightKg || 0) * (mode === "fat_loss" ? 2 : 1.6));
}

function fatTarget(calories) {
  return Math.round((Number(calories || 0) * 0.25) / 9);
}

function carbTarget(calories, protein, fat) {
  return Math.max(0, Math.round((Number(calories || 0) - Number(protein || 0) * 4 - Number(fat || 0) * 9) / 4));
}

function timeText(value) {
  const date = new Date(value);
  return Number.isNaN(date.getTime())
    ? "--:--"
    : date.toLocaleTimeString("zh-TW", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: false,
      });
}

function toDatetimeLocal(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(
    2,
    "0"
  )}T${String(date.getHours()).padStart(2, "0")}:${String(date.getMinutes()).padStart(2, "0")}`;
}

function groupEntries(entries) {
  const map = new Map();
  entries.forEach((entry) => {
    const key = String(entry.date_key || "").trim();
    if (!key) return;
    const bucket = map.get(key) || [];
    bucket.push(entry);
    map.set(key, bucket);
  });
  return Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([key, items]) => ({
      key,
      items: [...items].sort((a, b) => String(b.created_at || "").localeCompare(String(a.created_at || ""))),
    }));
}

function buildCalendar(monthDate, counts, selectedKey, todayKey) {
  const year = monthDate.getFullYear();
  const month = monthDate.getMonth();
  const firstDay = new Date(year, month, 1);
  const startOffset = firstDay.getDay();
  const totalDays = Math.ceil((startOffset + new Date(year, month + 1, 0).getDate()) / 7) * 7;
  const startDate = new Date(year, month, 1 - startOffset, 12);
  return Array.from({ length: totalDays }, (_, index) => {
    const value = new Date(startDate);
    value.setDate(startDate.getDate() + index);
    const key = dateKey(value);
    return {
      key,
      day: value.getDate(),
      count: counts.get(key) || 0,
      currentMonth: value.getMonth() === month,
      selected: key === selectedKey,
      today: key === todayKey,
    };
  });
}

function buildEditForm(entry) {
  return {
    foodName: entry.food_name || "",
    portionLabel: entry.portion_label || "",
    createdAt: toDatetimeLocal(entry.created_at),
    calories: String(entry.nutrition?.calories ?? ""),
    protein: String(entry.nutrition?.protein ?? ""),
    fat: String(entry.nutrition?.fat ?? ""),
    carbs: String(entry.nutrition?.carbs ?? ""),
  };
}

function JournalPage() {
  const { isMemberLoggedIn, memberName, memberAccount, memberProfile, updateMemberProfile, openAuthModal } = useAuth();
  const [draftProfile, setDraftProfile] = useState(memberProfile);
  const [entries, setEntries] = useState([]);
  const [foodProfiles, setFoodProfiles] = useState([]);
  const [goalMode, setGoalMode] = useState("maintain");
  const [selectedDateKey, setSelectedDateKey] = useState("");
  const [visibleMonth, setVisibleMonth] = useState(() => new Date(new Date().getFullYear(), new Date().getMonth(), 1));
  const [editingId, setEditingId] = useState("");
  const [editForm, setEditForm] = useState(null);
  const [editLookupOpen, setEditLookupOpen] = useState(false);
  const [saveMessage, setSaveMessage] = useState("");
  const todayKey = useMemo(() => dateKey(new Date()), []);

  useEffect(() => {
    setDraftProfile(memberProfile);
  }, [memberProfile]);

  useEffect(() => {
    let cancelled = false;
    if (!isMemberLoggedIn) {
      setEntries([]);
      return undefined;
    }
    listMemberJournalEntries(memberAccount)
      .then((items) => {
        if (!cancelled) setEntries(items);
      })
      .catch(() => {
        if (!cancelled) setEntries([]);
      });
    return () => {
      cancelled = true;
    };
  }, [isMemberLoggedIn, memberAccount]);

  useEffect(() => {
    fetchFoodProfiles()
      .then(setFoodProfiles)
      .catch(() => setFoodProfiles([]));
  }, []);

  const grouped = useMemo(() => groupEntries(entries), [entries]);
  const byDate = useMemo(() => new Map(grouped.map((group) => [group.key, group.items])), [grouped]);
  const counts = useMemo(() => new Map(grouped.map((group) => [group.key, group.items.length])), [grouped]);

  useEffect(() => {
    if (!grouped.length) {
      setSelectedDateKey(todayKey);
      const today = parseDateKey(todayKey);
      setVisibleMonth(new Date(today.getFullYear(), today.getMonth(), 1));
      return;
    }
    if (selectedDateKey && byDate.has(selectedDateKey)) return;
    const preferredKey = byDate.has(todayKey) ? todayKey : grouped[0].key;
    setSelectedDateKey(preferredKey);
    const value = parseDateKey(preferredKey);
    setVisibleMonth(new Date(value.getFullYear(), value.getMonth(), 1));
  }, [grouped, byDate, selectedDateKey, todayKey]);

  const selectedEntries = useMemo(() => byDate.get(selectedDateKey) || [], [byDate, selectedDateKey]);
  const selectedSummary = useMemo(() => summarizeJournalEntries(selectedEntries), [selectedEntries]);
  const todaySummary = useMemo(
    () => summarizeJournalEntries(entries.filter((entry) => entry.date_key === todayKey)),
    [entries, todayKey]
  );

  const editMatches = useMemo(() => {
    const keyword = String(editForm?.foodName || "")
      .trim()
      .toLowerCase();
    if (!keyword) return foodProfiles.slice(0, 6);
    return foodProfiles
      .filter((profile) =>
        [profile.display_name, profile.label, profile.parent_category].some((candidate) =>
          String(candidate || "")
            .toLowerCase()
            .includes(keyword)
        )
      )
      .slice(0, 6);
  }, [editForm?.foodName, foodProfiles]);

  const profile = useMemo(
    () => ({
      ...draftProfile,
      heightCm: Number(draftProfile.heightCm || 0),
      weightKg: Number(draftProfile.weightKg || 0),
      age: Number(draftProfile.age || 0),
    }),
    [draftProfile]
  );

  const bmr = calculateBmr(profile);
  const tdee = calculateTdee(profile);
  const cutCalories = calculateFatLossTarget(profile);
  const activity = getActivityOption(profile.activityLevel);
  const calorieGoal = goalMode === "fat_loss" ? cutCalories : tdee;
  const proteinGoal = proteinTarget(profile.weightKg, goalMode);
  const fatGoal = fatTarget(calorieGoal);
  const carbsGoal = carbTarget(calorieGoal, proteinGoal, fatGoal);
  const leftCalories = remaining(calorieGoal - Number(selectedSummary.calories || 0));
  const leftProtein = remaining(proteinGoal - Number(selectedSummary.protein || 0));
  const leftFat = remaining(fatGoal - Number(selectedSummary.fat || 0));
  const leftCarbs = remaining(carbsGoal - Number(selectedSummary.carbs || 0));

  const calendar = useMemo(
    () => buildCalendar(visibleMonth, counts, selectedDateKey, todayKey),
    [visibleMonth, counts, selectedDateKey, todayKey]
  );

  async function reload() {
    if (!isMemberLoggedIn) {
      setEntries([]);
      return;
    }
    try {
      setEntries(await listMemberJournalEntries(memberAccount));
    } catch {
      setEntries([]);
    }
  }

  async function removeEntry(entryId) {
    await removeJournalEntry(memberAccount, entryId);
    if (editingId === entryId) {
      setEditingId("");
      setEditForm(null);
      setEditLookupOpen(false);
    }
    await reload();
  }

  async function saveProfile() {
    const result = await updateMemberProfile(profile);
    if (result.ok) {
      setSaveMessage("會員資料已更新。");
      window.setTimeout(() => setSaveMessage(""), 2000);
    }
  }

  async function saveEdit(entryId) {
    if (!editForm) return;
    await updateJournalEntry(memberAccount, entryId, {
      food_name: editForm.foodName.trim() || "未命名餐點",
      portion_label: editForm.portionLabel.trim() || "1 份",
      created_at: editForm.createdAt ? new Date(editForm.createdAt).toISOString() : undefined,
      nutrition: {
        calories: Number(editForm.calories || 0),
        protein: Number(editForm.protein || 0),
        fat: Number(editForm.fat || 0),
        carbs: Number(editForm.carbs || 0),
      },
    });
    setEditingId("");
    setEditForm(null);
    setEditLookupOpen(false);
    await reload();
  }

  if (!isMemberLoggedIn) {
    return (
      <Layout>
        <section className="panel-card journal-summary-card">
          <span>會員模式</span>
          <h2>登入後查看你的飲食日誌</h2>
          <p>登入後可以查看月曆日誌、編輯每日餐點，並依照會員資料計算 BMR、TDEE 與每日熱量目標。</p>
          <div className="journal-actions">
            <button type="button" className="secondary-button" onClick={() => openAuthModal("login")}>
              會員登入
            </button>
            <button type="button" className="primary-button" onClick={() => openAuthModal("register")}>
              註冊會員
            </button>
            <Link to="/recognition" className="secondary-button">
              返回掃描頁
            </Link>
          </div>
        </section>
      </Layout>
    );
  }

  return (
    <Layout>
      <section className="page-header">
        <p className="eyebrow">會員日誌</p>
        <h1>依日期查看餐點與營養</h1>
        <p className="subtitle">我們會依照你目前選取的日期，統計當天已加入日誌的熱量、蛋白質、脂肪與碳水。</p>
      </section>

      <div className="journal-summary-grid">
        <section className="panel-card journal-summary-card">
          <span>會員資料</span>
          <strong>{memberName || memberAccount}</strong>
          <div className="profile-editor-grid">
            <label>
              <span>性別</span>
              <select
                value={draftProfile.gender}
                onChange={(event) => setDraftProfile((current) => ({ ...current, gender: event.target.value }))}
              >
                <option value="male">男性</option>
                <option value="female">女性</option>
              </select>
            </label>
            <label>
              <span>身高 (cm)</span>
              <input
                type="number"
                min="1"
                value={draftProfile.heightCm}
                onChange={(event) => setDraftProfile((current) => ({ ...current, heightCm: event.target.value }))}
              />
            </label>
            <label>
              <span>體重 (kg)</span>
              <input
                type="number"
                min="1"
                step="0.1"
                value={draftProfile.weightKg}
                onChange={(event) => setDraftProfile((current) => ({ ...current, weightKg: event.target.value }))}
              />
            </label>
            <label>
              <span>年齡</span>
              <input
                type="number"
                min="1"
                value={draftProfile.age}
                onChange={(event) => setDraftProfile((current) => ({ ...current, age: event.target.value }))}
              />
            </label>
            <label className="profile-editor-wide">
              <span>活動量</span>
              <select
                value={draftProfile.activityLevel}
                onChange={(event) => setDraftProfile((current) => ({ ...current, activityLevel: event.target.value }))}
              >
                {ACTIVITY_LEVEL_OPTIONS.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="profile-editor-actions">
            <button type="button" className="primary-button" onClick={saveProfile}>
              儲存會員資料
            </button>
            {saveMessage ? <span className="muted-text">{saveMessage}</span> : null}
          </div>
        </section>

        <section className="panel-card journal-summary-card">
          <div className="journal-summary-metric">
            <span>今日總熱量</span>
            <strong>{todaySummary.calories} kcal</strong>
          </div>
          <div className="journal-summary-metric">
            <span>今日筆數</span>
            <strong>{todaySummary.count}</strong>
          </div>
          <Link to="/recognition" className="primary-button">
            返回掃描頁
          </Link>
        </section>
      </div>

      <section className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">BMR</p>
          <h2>基礎代謝與每日消耗</h2>
        </div>
        <div className="bmr-grid">
          <div className="journal-summary-metric">
            <span>基礎代謝率 BMR</span>
            <strong>{bmr || "--"} kcal</strong>
          </div>
          <div className="journal-summary-metric">
            <span>活動量總消耗 TDEE</span>
            <strong>{tdee || "--"} kcal</strong>
            <small>{activity.label}</small>
          </div>
          <div className="journal-summary-metric">
            <span>減脂建議熱量</span>
            <strong>{cutCalories || "--"} kcal</strong>
          </div>
        </div>
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">熱量目標</p>
          <h2>維持體態 / 減脂建議</h2>
        </div>
        <div className="journal-goal-toggle">
          <button
            type="button"
            className={`journal-goal-chip ${goalMode === "maintain" ? "active" : ""}`}
            onClick={() => setGoalMode("maintain")}
          >
            維持體態
          </button>
          <button
            type="button"
            className={`journal-goal-chip ${goalMode === "fat_loss" ? "active" : ""}`}
            onClick={() => setGoalMode("fat_loss")}
          >
            減脂建議
          </button>
        </div>
        <div className="journal-goal-summary">
          <div className="journal-summary-metric journal-double-metric">
            <div>
              <span>今日目標熱量</span>
              <strong>{calorieGoal || "--"} 千卡</strong>
            </div>
            <div>
              <span>剩餘熱量</span>
              <strong>{leftCalories} 千卡</strong>
            </div>
          </div>
          <div className="journal-summary-metric journal-double-metric">
            <div>
              <span>今日目標蛋白質</span>
              <strong>{proteinGoal || "--"} 克</strong>
            </div>
            <div>
              <span>剩餘蛋白質</span>
              <strong>{leftProtein} 克</strong>
            </div>
          </div>
          <div className="journal-summary-metric journal-double-metric">
            <div>
              <span>今日目標脂肪</span>
              <strong>{fatGoal || "--"} 克</strong>
            </div>
            <div>
              <span>剩餘脂肪</span>
              <strong>{leftFat} 克</strong>
            </div>
          </div>
          <div className="journal-summary-metric journal-double-metric">
            <div>
              <span>今日目標碳水</span>
              <strong>{carbsGoal || "--"} 克</strong>
            </div>
            <div>
              <span>剩餘碳水</span>
              <strong>{leftCarbs} 克</strong>
            </div>
          </div>
        </div>
        <p className="muted-text">這個區會根據您目前點選的日期，扣掉當天已經加入日誌的用餐點。</p>
        <p className="muted-text journal-goal-debug">
          畫面版本 {JOURNAL_UI_VERSION} · 目前模式：{goalMode === "fat_loss" ? "減脂建議" : "維持體態"} · 選取日期：
          {dateTitle(selectedDateKey)} · 已扣熱量：{selectedSummary.calories} 千卡
        </p>
      </section>

      <section className="panel-card">
        <div className="section-heading">
          <p className="eyebrow">日期切換</p>
          <h2>依日期查看餐點</h2>
        </div>
        {grouped.length === 0 ? (
          <p>目前還沒有任何日誌紀錄，先去掃描頁新增一筆吧。</p>
        ) : (
          <>
            <div className="journal-calendar-header">
              <button
                type="button"
                className="secondary-button"
                onClick={() => setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() - 1, 1))}
              >
                上個月
              </button>
              <strong>{monthTitle(visibleMonth)}</strong>
              <button
                type="button"
                className="secondary-button"
                onClick={() => setVisibleMonth((current) => new Date(current.getFullYear(), current.getMonth() + 1, 1))}
              >
                下個月
              </button>
            </div>

            <div className="journal-calendar-grid">
              {WEEKDAYS.map((label) => (
                <div key={label} className="journal-calendar-weekday">
                  {label}
                </div>
              ))}
              {calendar.map((day) => (
                <button
                  key={day.key}
                  type="button"
                  className={[
                    "journal-calendar-cell",
                    day.currentMonth ? "" : "journal-calendar-cell--outside",
                    day.today ? "journal-calendar-cell--today" : "",
                    day.selected ? "journal-calendar-cell--selected" : "",
                  ]
                    .filter(Boolean)
                    .join(" ")}
                  onClick={() => {
                    setSelectedDateKey(day.key);
                    const value = parseDateKey(day.key);
                    setVisibleMonth(new Date(value.getFullYear(), value.getMonth(), 1));
                  }}
                >
                  <span className="journal-calendar-day">{day.day}</span>
                  {day.today ? <small>今天</small> : null}
                  {day.count > 0 ? <small className="journal-calendar-count">{day.count} 筆</small> : null}
                </button>
              ))}
            </div>

            <div className="journal-day-summary">
              <div className="journal-summary-metric">
                <span>目前日期</span>
                <strong>{dateTitle(selectedDateKey)}</strong>
              </div>
              <div className="journal-summary-metric">
                <span>當日總熱量</span>
                <strong>{selectedSummary.calories} 千卡</strong>
              </div>
              <div className="journal-summary-metric">
                <span>當日餐點筆數</span>
                <strong>{selectedSummary.count}</strong>
              </div>
              <div className="journal-summary-metric">
                <span>當日蛋白質</span>
                <strong>{selectedSummary.protein} 克</strong>
              </div>
              <div className="journal-summary-metric">
                <span>當日脂肪</span>
                <strong>{selectedSummary.fat} 克</strong>
              </div>
              <div className="journal-summary-metric">
                <span>當日碳水</span>
                <strong>{selectedSummary.carbs} 克</strong>
              </div>
            </div>

            <div className="section-heading">
              <p className="eyebrow">當日時間軸</p>
              <h3>查看每一筆餐點</h3>
            </div>
            {selectedEntries.length === 0 ? (
              <p>這一天目前沒有任何紀錄。</p>
            ) : (
              <div className="journal-timeline">
                {selectedEntries.map((entry) => {
                  const isEditing = editingId === entry.id && editForm;
                  return (
                    <article className="journal-entry-row" key={entry.id}>
                      <div className="journal-entry-time">{timeText(entry.created_at)}</div>
                      <div className="journal-entry-content">
                        <div className="journal-entry-header">
                          <div>
                            <strong>{entry.food_name}</strong>
                            <span>{entry.portion_label}</span>
                          </div>
                          <div className="journal-entry-actions">
                            <button
                              type="button"
                              className="manual-lookup-clear journal-entry-edit"
                              onClick={() => {
                                setEditingId(entry.id);
                                setEditForm(buildEditForm(entry));
                                setEditLookupOpen(false);
                              }}
                            >
                              編輯
                            </button>
                            <button
                              type="button"
                              className="manual-lookup-clear journal-entry-delete"
                              onClick={() => removeEntry(entry.id)}
                            >
                              刪除
                            </button>
                          </div>
                        </div>
                        <div className="journal-entry-macros">
                          <span>熱量 {entry.nutrition.calories} kcal</span>
                          <span>蛋白質 {entry.nutrition.protein} g</span>
                          <span>脂肪 {entry.nutrition.fat} g</span>
                          <span>碳水 {entry.nutrition.carbs} g</span>
                        </div>

                        {isEditing ? (
                          <div className="manual-edit-card journal-entry-edit-form">
                            <p className="muted-text">這裡可以直接搜尋資料庫食物，點一下後會自動帶入份量與營養數值。</p>
                            <div className="manual-edit-grid">
                              <label className="manual-edit-wide">
                                <span>食物名稱</span>
                                <div className="manual-lookup-input-wrap">
                                  <input
                                    value={editForm.foodName}
                                    onChange={(event) => {
                                      setEditForm((current) => ({ ...current, foodName: event.target.value }));
                                      setEditLookupOpen(true);
                                    }}
                                    onFocus={() => setEditLookupOpen(true)}
                                    onBlur={() => window.setTimeout(() => setEditLookupOpen(false), 120)}
                                    placeholder="搜尋食物名稱，例如：牛排、炒飯、餃子"
                                  />
                                  {editLookupOpen ? (
                                    <div className="manual-lookup-dropdown">
                                      {editMatches.length === 0 ? (
                                        <div className="manual-lookup-empty">找不到對應的食物，請直接手動輸入。</div>
                                      ) : (
                                        editMatches.map((profile) => (
                                          <button
                                            key={profile.label}
                                            type="button"
                                            className="manual-lookup-option"
                                            onMouseDown={(event) => event.preventDefault()}
                                            onClick={() => {
                                              setEditForm((current) => ({
                                                ...current,
                                                foodName: profile.display_name || profile.label,
                                                portionLabel: profile.default_portion_label || current.portionLabel || "1 份",
                                                calories: String(profile.calories ?? ""),
                                                protein: String(profile.protein ?? ""),
                                                fat: String(profile.fat ?? ""),
                                                carbs: String(profile.carbs ?? ""),
                                              }));
                                              setEditLookupOpen(false);
                                            }}
                                          >
                                            <strong>{profile.display_name || profile.label}</strong>
                                            <span>{profile.default_portion_label}</span>
                                          </button>
                                        ))
                                      )}
                                    </div>
                                  ) : null}
                                </div>
                              </label>
                              <label>
                                <span>紀錄日期時間</span>
                                <input
                                  type="datetime-local"
                                  value={editForm.createdAt}
                                  onChange={(event) =>
                                    setEditForm((current) => ({ ...current, createdAt: event.target.value }))
                                  }
                                />
                              </label>
                              <label>
                                <span>份量文字</span>
                                <input
                                  value={editForm.portionLabel}
                                  onChange={(event) =>
                                    setEditForm((current) => ({ ...current, portionLabel: event.target.value }))
                                  }
                                />
                              </label>
                              <label>
                                <span>熱量</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="1"
                                  value={editForm.calories}
                                  onChange={(event) =>
                                    setEditForm((current) => ({ ...current, calories: event.target.value }))
                                  }
                                />
                              </label>
                              <label>
                                <span>蛋白質</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="0.1"
                                  value={editForm.protein}
                                  onChange={(event) =>
                                    setEditForm((current) => ({ ...current, protein: event.target.value }))
                                  }
                                />
                              </label>
                              <label>
                                <span>脂肪</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="0.1"
                                  value={editForm.fat}
                                  onChange={(event) =>
                                    setEditForm((current) => ({ ...current, fat: event.target.value }))
                                  }
                                />
                              </label>
                              <label>
                                <span>碳水</span>
                                <input
                                  type="number"
                                  min="0"
                                  step="0.1"
                                  value={editForm.carbs}
                                  onChange={(event) =>
                                    setEditForm((current) => ({ ...current, carbs: event.target.value }))
                                  }
                                />
                              </label>
                            </div>
                            <div className="journal-entry-edit-actions">
                              <button type="button" className="primary-button" onClick={() => saveEdit(entry.id)}>
                                儲存變更
                              </button>
                              <button
                                type="button"
                                className="secondary-button"
                                onClick={() => {
                                  setEditingId("");
                                  setEditForm(null);
                                  setEditLookupOpen(false);
                                }}
                              >
                                取消
                              </button>
                            </div>
                          </div>
                        ) : null}
                      </div>
                    </article>
                  );
                })}
              </div>
            )}
          </>
        )}
      </section>
    </Layout>
  );
}

export default JournalPage;
