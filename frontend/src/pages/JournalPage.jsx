import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { fetchFoodProfiles } from "../api/foodProfilesApi";
import Layout from "../components/Layout";
import {
  CoachHeroCard,
  CoachHeader,
  DailyMissions,
  EmptyState,
  ExerciseRecoveryCard,
  FloatingCoachButton,
  GoalModeSelector,
  MacroGapAnalysis,
  NextMealSuggestion,
  PostLogImpactCard,
  SmartScanButton,
  TodayDecisionStrip,
  TrainingCoachCard,
  WeeklyCoachReview,
} from "../components/NutritionCommandCenter";
import { useAuth } from "../context/AuthContext";
import {
  ACTIVITY_LEVEL_OPTIONS,
  calculateBmr,
  calculateFatLossTarget,
  calculateTdee,
  getActivityOption,
} from "../utils/bmr";
import {
  buildJournalDateTimePayload,
  calculateDailyNutrition,
  getEntryDateTimeInputValue,
  getEntryLocalDate,
  listMemberJournalEntries,
  normalizeNutrition,
  removeJournalEntry,
  updateJournalEntry,
} from "../utils/memberJournal";
import {
  buildNutritionTargets,
  formatAmount,
  generateExerciseRecoveryPlan,
  generateModeAwareCoachSummary,
  generateModeAwareDailyMissions,
  generateModeAwareMealSuggestion,
  generateModeAwareTrainingAdvice,
  generatePostLogImpact,
  generateWeeklyCoachReview,
} from "../utils/nutritionCoachHelpers";

const WEEKDAYS = ["日", "一", "二", "三", "四", "五", "六"];
const dateKey = (value = new Date()) =>
  `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;

const dateTitle = (value = "") => String(value).replaceAll("-", "/") || "--";

const modeLabel = (goalMode) =>
  goalMode === "fat_loss" ? "減脂建議" : goalMode === "fitness_daily" ? "健人日常" : "維持體態";

function parseDateKey(value) {
  const [y, m, d] = String(value || "").split("-");
  return y && m && d ? new Date(Number(y), Number(m) - 1, Number(d), 12) : new Date();
}

function monthTitle(value) {
  return `${value.getFullYear()}年${value.getMonth() + 1}月`;
}

function weekdayTitle(value) {
  const date = parseDateKey(value);
  return `星期${WEEKDAYS[date.getDay()]}`;
}

function proteinTarget(weightKg, mode) {
  return Math.round(Number(weightKg || 0) * (mode === "maintain" ? 1.6 : 2));
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

function groupEntries(entries) {
  const map = new Map();
  entries.forEach((entry) => {
    const key = String(getEntryLocalDate(entry) || "").trim();
    if (!key) return;
    const bucket = map.get(key) || [];
    bucket.push(entry);
    map.set(key, bucket);
  });
  return Array.from(map.entries())
    .sort((a, b) => b[0].localeCompare(a[0]))
    .map(([key, items]) => ({
      key,
      items: [...items].sort((a, b) =>
        String(b.local_date_time || b.localDateTime || b.created_at || "").localeCompare(
          String(a.local_date_time || a.localDateTime || a.created_at || "")
        )
      ),
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
  const nutrition = normalizeNutrition(entry);
  return {
    foodName: entry.food_name || "",
    portionLabel: entry.portion_label || "",
    createdAt: getEntryDateTimeInputValue(entry),
    calories: String(nutrition.calories ?? ""),
    protein: String(nutrition.protein ?? ""),
    fat: String(nutrition.fat ?? ""),
    carbs: String(nutrition.carbs ?? ""),
  };
}

function JournalPage() {
  const { isMemberLoggedIn, memberName, memberAccount, memberProfile, updateMemberProfile, openAuthModal } = useAuth();
  const [draftProfile, setDraftProfile] = useState(memberProfile);
  const [entries, setEntries] = useState([]);
  const [foodProfiles, setFoodProfiles] = useState([]);
  const [goalMode, setGoalMode] = useState("maintain");
  const [trainingDayType, setTrainingDayType] = useState("strength");
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
  const selectedSummary = useMemo(() => calculateDailyNutrition(selectedEntries), [selectedEntries]);
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
  const nutritionTargets = useMemo(
    () =>
      buildNutritionTargets(selectedSummary, {
        calories: calorieGoal,
        protein: proteinGoal,
        fat: fatGoal,
        carbs: carbsGoal,
      }),
    [
      calorieGoal,
      carbsGoal,
      fatGoal,
      proteinGoal,
      selectedSummary.calories,
      selectedSummary.carbs,
      selectedSummary.fat,
      selectedSummary.protein,
    ]
  );
  const calorieGoalCard = nutritionTargets.find((target) => target.key === "calories") || nutritionTargets[0];
  const macroTargets = nutritionTargets.filter((target) => target.key !== "calories");
  const targetValues = useMemo(
    () => ({
      calories: calorieGoal,
      protein: proteinGoal,
      fat: fatGoal,
      carbs: carbsGoal,
    }),
    [calorieGoal, carbsGoal, fatGoal, proteinGoal]
  );
  const coachSummary = useMemo(
    () => generateModeAwareCoachSummary(goalMode, selectedSummary, targetValues),
    [goalMode, selectedSummary, targetValues]
  );
  const dailyMissions = useMemo(
    () => generateModeAwareDailyMissions(goalMode, selectedSummary, targetValues),
    [goalMode, selectedSummary, targetValues]
  );
  const trainingAdvice = useMemo(
    () => generateModeAwareTrainingAdvice(goalMode, selectedSummary, targetValues),
    [goalMode, selectedSummary, targetValues]
  );
  const mealSuggestion = useMemo(
    () => generateModeAwareMealSuggestion(goalMode, selectedSummary, targetValues),
    [goalMode, selectedSummary, targetValues]
  );
  const exercisePlan = useMemo(
    () => generateExerciseRecoveryPlan(goalMode, selectedSummary, targetValues, profile.weightKg),
    [goalMode, profile.weightKg, selectedSummary, targetValues]
  );
  const latestEntry = selectedEntries[0] || null;
  const postLogImpact = useMemo(() => generatePostLogImpact(latestEntry, goalMode), [latestEntry, goalMode]);
  const weeklyReview = useMemo(() => generateWeeklyCoachReview(entries, targetValues), [entries, targetValues]);
  const selectedDateLabel = useMemo(
    () => `${dateTitle(selectedDateKey)} · ${weekdayTitle(selectedDateKey)}`,
    [selectedDateKey]
  );
  const decisionItems = useMemo(() => {
    const sortedMacros = [...macroTargets].sort((a, b) => b.percent - a.percent);
    const overMacro = sortedMacros.find((target) => target.isOver);
    const proteinTarget = macroTargets.find((target) => target.key === "protein");
    const attention = overMacro
      ? {
          value: `${overMacro.label}超標`,
          meta: overMacro.remaining.text,
          tone: "over",
        }
      : proteinTarget && proteinTarget.percent < 60
        ? {
            value: "蛋白質偏低",
            meta: proteinTarget.remaining.text,
            tone: "near",
          }
        : {
            value: "節奏穩定",
            meta: "保持目前飲食節奏",
            tone: "normal",
          };
    const movement = exercisePlan.shouldShow
      ? `${exercisePlan.options[0]?.name || "快走"} ${exercisePlan.options[0]?.minutes || 20} 分鐘`
      : goalMode === "fitness_daily"
        ? "重訓 45-70 分鐘"
        : "快走 20-30 分鐘";

    return [
      { label: "最該注意", ...attention },
      { label: "下一餐方向", value: mealSuggestion.direction, meta: mealSuggestion.title, tone: "normal" },
      { label: "今日動一動", value: movement, meta: trainingAdvice.title, tone: exercisePlan.shouldShow ? "near" : "low" },
    ];
  }, [exercisePlan, goalMode, macroTargets, mealSuggestion.direction, mealSuggestion.title, trainingAdvice.title]);

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
      ...buildJournalDateTimePayload(editForm.createdAt),
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
      <div className="nutrition-os-page">
      <CoachHeader dateLabel={selectedDateLabel} modeLabel={modeLabel(goalMode)} />

      <CoachHeroCard
        dateLabel={selectedDateLabel}
        memberLabel={memberName || memberAccount}
        summary={selectedSummary}
        calorieTarget={calorieGoalCard}
        coachSummary={coachSummary}
      />

      <TodayDecisionStrip items={decisionItems} />

      <GoalModeSelector goalMode={goalMode} onChange={setGoalMode} />

      <div className="os-main-layout">
        <main className="os-main-column">
          <div className="os-action-grid">
            <DailyMissions missions={dailyMissions} />
            <NextMealSuggestion suggestion={mealSuggestion} />
          </div>

          <div className="os-action-grid os-action-grid--training">
            <TrainingCoachCard
              goalMode={goalMode}
              trainingDayType={trainingDayType}
              onTrainingDayChange={setTrainingDayType}
              advice={trainingAdvice}
            />
            <ExerciseRecoveryCard plan={exercisePlan} />
          </div>

      <section className="os-section food-timeline-section">
        <div className="os-section-heading os-section-heading-row">
          <div>
            <p className="os-kicker">Food Timeline</p>
            <h2>今日飲食時間線</h2>
          </div>
          <span className="os-soft-badge">{dateTitle(selectedDateKey)}</span>
        </div>
        {grouped.length === 0 ? (
          <EmptyState />
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
                <strong>{formatAmount(selectedSummary.calories, "千卡")}</strong>
              </div>
              <div className="journal-summary-metric">
                <span>當日餐點筆數</span>
                <strong>{selectedSummary.count}</strong>
              </div>
              <div className="journal-summary-metric">
                <span>蛋白質</span>
                <strong>{formatAmount(selectedSummary.protein, "克")}</strong>
              </div>
              <div className="journal-summary-metric">
                <span>脂肪</span>
                <strong>{formatAmount(selectedSummary.fat, "克")}</strong>
              </div>
              <div className="journal-summary-metric">
                <span>碳水</span>
                <strong>{formatAmount(selectedSummary.carbs, "克")}</strong>
              </div>
            </div>

            <div className="os-section-heading">
              <p className="os-kicker">Meals</p>
              <h3>查看每一筆餐點</h3>
            </div>
            {selectedEntries.length === 0 ? (
              <EmptyState />
            ) : (
              <div className="journal-timeline">
                {selectedEntries.map((entry) => {
                  const isEditing = editingId === entry.id && editForm;
                  const nutrition = normalizeNutrition(entry);
                  return (
                    <article className="journal-entry-row" key={entry.id}>
                      <div className="journal-entry-time">
                        {timeText(entry.local_date_time || entry.localDateTime || entry.created_at)}
                      </div>
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
                          <span>熱量 {formatAmount(nutrition.calories, "千卡")}</span>
                          <span>P {formatAmount(nutrition.protein, "克")}</span>
                          <span>F {formatAmount(nutrition.fat, "克")}</span>
                          <span>C {formatAmount(nutrition.carbs, "克")}</span>
                        </div>

                        {isEditing ? (
                          <div className="manual-edit-card journal-entry-edit-form">
                            <p className="muted-text">調整餐點、份量或日期時間後，時間線與營養統計會立即重新歸類。</p>
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
        </main>

        <aside className="os-side-column">
          <MacroGapAnalysis targets={macroTargets} />
          <PostLogImpactCard impact={postLogImpact} />
          <WeeklyCoachReview review={weeklyReview} />

          <section className="os-section member-profile-card">
          <div className="section-heading">
            <p className="eyebrow">會員資料</p>
            <h2>代謝計算設定</h2>
          </div>
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

        <section className="os-section metabolism-card">
          <div className="section-heading">
            <p className="eyebrow">BMR / TDEE</p>
            <h2>今日目標基準</h2>
          </div>
          <div className="coach-metric-row">
            <div>
              <span>基礎代謝率</span>
              <strong>{bmr || "--"} kcal</strong>
            </div>
            <div>
              <span>活動量消耗</span>
              <strong>{tdee || "--"} kcal</strong>
            </div>
            <div>
              <span>減脂建議</span>
              <strong>{cutCalories || "--"} kcal</strong>
            </div>
          </div>
          <p className="muted-text">{activity.label}</p>
        </section>
        </aside>
      </div>
      <SmartScanButton />
      <FloatingCoachButton />
      </div>
    </Layout>
  );
}

export default JournalPage;
