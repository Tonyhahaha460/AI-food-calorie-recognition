import { GOAL_MODES, TRAINING_DAY_TYPES, formatAmount, getGoalModeConfig } from "../utils/nutritionCoachHelpers";

function ProgressBar({ target, percent, visualPercent, status }) {
  if (Number(target || 0) <= 0) {
    return <div className="coach-progress-empty">尚未設定目標</div>;
  }

  return (
    <div className={`coach-progress-track coach-progress-track--${status}`} aria-label={`進度 ${percent}%`}>
      <span style={{ width: `${visualPercent}%` }} />
    </div>
  );
}

export function CoachHeroCard({ dateLabel, memberLabel, summary, calorieTarget, coachSummary }) {
  const ringPercent = Math.min(100, Math.max(0, calorieTarget?.visualPercent || 0));
  const hasCalorieTarget = Boolean(calorieTarget?.hasTarget);
  const ringStyle = {
    "--coach-ring": `${ringPercent}%`,
  };

  return (
    <section className="coach-hero-card">
      <div className="coach-hero-main">
        <div>
          <p className="eyebrow">AI 飲食教練</p>
          <h1>{coachSummary.title}</h1>
          <p>{coachSummary.message}</p>
          <div className="coach-status-row">
            <span>{coachSummary.state}</span>
            <span>{dateLabel}</span>
            <span>{memberLabel}</span>
          </div>
        </div>
        <div className="coach-progress-ring" style={ringStyle}>
          <div>
            <span>今日已攝取</span>
            <strong>{formatAmount(summary.calories, "千卡")}</strong>
            <small>{hasCalorieTarget ? `${calorieTarget?.percent || 0}%` : "--"}</small>
          </div>
        </div>
      </div>

      <div className="coach-stat-strip">
        <div>
          <span>目標熱量</span>
          <strong>{formatAmount(calorieTarget?.target || 0, "千卡")}</strong>
        </div>
        <div>
          <span>{calorieTarget?.remaining?.label || "剩餘"}熱量</span>
          <strong>{hasCalorieTarget ? formatAmount(calorieTarget?.remaining?.amount || 0, "千卡") : "--"}</strong>
        </div>
        <div>
          <span>今日紀錄數</span>
          <strong>{summary.count}</strong>
        </div>
        <div>
          <span>蛋白質</span>
          <strong>{formatAmount(summary.protein, "克")}</strong>
        </div>
      </div>
    </section>
  );
}

export function GoalModeSelector({ goalMode, onChange }) {
  return (
    <section className="panel-card command-section">
      <div className="section-heading">
        <p className="eyebrow">目標模式</p>
        <h2>選擇今天的飲食策略</h2>
      </div>
      <div className="goal-mode-grid">
        {Object.values(GOAL_MODES).map((mode) => (
          <button
            key={mode.key}
            type="button"
            className={`goal-mode-card ${goalMode === mode.key ? "active" : ""}`}
            onClick={() => onChange(mode.key)}
          >
            <span>{mode.shortLabel}</span>
            <strong>{mode.label}</strong>
            <small>{mode.targetUser}</small>
            <em>{mode.nutritionStrategy}</em>
          </button>
        ))}
      </div>
    </section>
  );
}

export function NutritionTargetGrid({ targets }) {
  return (
    <section className="panel-card command-section">
      <div className="section-heading">
        <p className="eyebrow">營養目標</p>
        <h2>今日熱量與三大營養素</h2>
      </div>
      <div className="nutrition-command-grid">
        {targets.map((target) => (
          <article className={`nutrition-command-card nutrition-command-card--${target.status}`} key={target.key}>
            <div className="nutrition-command-topline">
              <span className="nutrition-command-token">{target.token}</span>
              <div>
                <span>{target.label}</span>
                <strong>{target.hasTarget ? `${target.percent}%` : "--"}</strong>
              </div>
            </div>
            <div className="nutrition-command-values">
              <div>
                <span>今日目標</span>
                <strong>{target.hasTarget ? formatAmount(target.target, target.unit) : "--"}</strong>
              </div>
              <div>
                <span>已使用</span>
                <strong>{formatAmount(target.used, target.unit)}</strong>
              </div>
              <div>
                <span>{target.remaining.label}</span>
                <strong>{target.hasTarget ? formatAmount(target.remaining.amount, target.unit) : "--"}</strong>
              </div>
            </div>
            <ProgressBar
              target={target.target}
              percent={target.hasTarget ? target.percent : 0}
              visualPercent={target.visualPercent}
              status={target.status}
            />
          </article>
        ))}
      </div>
    </section>
  );
}

export function DailyMissions({ missions }) {
  return (
    <section className="panel-card command-section">
      <div className="section-heading">
        <p className="eyebrow">每日任務</p>
        <h2>今天先完成這三件事</h2>
      </div>
      <ol className="daily-mission-list">
        {missions.map((mission) => (
          <li key={mission}>
            <span />
            <p>{mission}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function TrainingCoachCard({ goalMode, trainingDayType, onTrainingDayChange, advice }) {
  const mode = getGoalModeConfig(goalMode);

  return (
    <section className="panel-card command-section coach-advice-card">
      <div className="section-heading">
        <p className="eyebrow">訓練搭配</p>
        <h2>{advice.title}</h2>
      </div>
      <label className="training-day-select">
        <span>今天類型</span>
        <select value={trainingDayType} onChange={(event) => onTrainingDayChange(event.target.value)}>
          {Object.entries(TRAINING_DAY_TYPES).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </label>
      <p>{advice.body}</p>
      <small>{advice.note}</small>
      <div className="coach-mode-pill">{mode.exerciseStrategy}</div>
    </section>
  );
}

export function NextMealSuggestion({ suggestion }) {
  return (
    <section className="panel-card command-section">
      <div className="section-heading">
        <p className="eyebrow">下一餐</p>
        <h2>{suggestion.title}</h2>
      </div>
      <div className="meal-direction-card">
        <span>建議方向</span>
        <strong>{suggestion.direction}</strong>
        <p>{suggestion.reason}</p>
      </div>
      <div className="meal-chip-row">
        <span>推薦</span>
        {suggestion.recommended.map((item) => (
          <strong key={item}>{item}</strong>
        ))}
      </div>
      <div className="meal-chip-row meal-chip-row--avoid">
        <span>少碰</span>
        {suggestion.avoid.map((item) => (
          <strong key={item}>{item}</strong>
        ))}
      </div>
    </section>
  );
}

export function ExerciseRecoveryCard({ plan }) {
  return (
    <section className={`panel-card command-section recovery-plan-card ${plan.shouldShow ? "active" : ""}`}>
      <div className="section-heading">
        <p className="eyebrow">運動換算</p>
        <h2>{plan.shouldShow ? "可以這樣平衡今天" : "目前不需要補償運動"}</h2>
      </div>
      <p>{plan.message}</p>
      <div className="exercise-option-grid">
        {plan.options.map((option) => (
          <article key={option.name}>
            <span>{option.intensity}</span>
            <strong>{option.name}</strong>
            <b>{option.minutes} 分鐘</b>
            <small>{option.note}</small>
          </article>
        ))}
      </div>
      {plan.usesDefaultWeight ? <small className="muted-text">未設定體重時會先以 70kg 估算。</small> : null}
    </section>
  );
}

export function MacroGapAnalysis({ targets }) {
  return (
    <section className="panel-card command-section">
      <div className="section-heading">
        <p className="eyebrow">缺口分析</p>
        <h2>蛋白質、脂肪、碳水狀態</h2>
      </div>
      <div className="macro-gap-grid">
        {targets.map((target) => (
          <article className={`macro-gap-card macro-gap-card--${target.status}`} key={target.key}>
            <div>
              <span>{target.label}</span>
              <strong>{target.remaining.text}</strong>
            </div>
            <ProgressBar
              target={target.target}
              percent={target.percent}
              visualPercent={target.visualPercent}
              status={target.status}
            />
            <small>
              已使用 {formatAmount(target.used, target.unit)} / 目標{" "}
              {target.hasTarget ? formatAmount(target.target, target.unit) : "--"}
            </small>
          </article>
        ))}
      </div>
    </section>
  );
}

export function PostLogImpactCard({ impact }) {
  if (!impact) return null;

  return (
    <section className="panel-card command-section post-log-impact-card">
      <div className="section-heading">
        <p className="eyebrow">最新紀錄影響</p>
        <h2>{impact.foodName}</h2>
      </div>
      <p>{impact.message}</p>
      <div className="impact-macro-row">
        <span>{formatAmount(impact.nutrition.calories, "千卡")}</span>
        <span>P {formatAmount(impact.nutrition.protein, "克")}</span>
        <span>F {formatAmount(impact.nutrition.fat, "克")}</span>
        <span>C {formatAmount(impact.nutrition.carbs, "克")}</span>
      </div>
    </section>
  );
}

export function WeeklyCoachReview({ review }) {
  return (
    <section className="panel-card command-section weekly-review-card">
      <div className="section-heading">
        <p className="eyebrow">週回顧</p>
        <h2>{review.ready ? "本週飲食趨勢" : "等待更多紀錄"}</h2>
      </div>
      <p>{review.message}</p>
      {review.ready ? (
        <div className="weekly-review-stats">
          <div>
            <span>平均熱量</span>
            <strong>{formatAmount(review.averageCalories, "千卡")}</strong>
          </div>
          <div>
            <span>蛋白達標日</span>
            <strong>
              {review.proteinDays}/{review.totalDays}
            </strong>
          </div>
          <div>
            <span>脂肪超標日</span>
            <strong>
              {review.fatOverDays}/{review.totalDays}
            </strong>
          </div>
        </div>
      ) : null}
    </section>
  );
}
