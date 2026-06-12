import { Link } from "react-router-dom";
import { GOAL_MODES, TRAINING_DAY_TYPES, formatAmount, getGoalModeConfig } from "../utils/nutritionCoachHelpers";

function ProgressBar({ target, percent, visualPercent, status, label }) {
  if (Number(target || 0) <= 0) {
    return <div className="os-progress-empty">尚未設定目標</div>;
  }

  return (
    <div
      className={`os-progress-track os-progress-track--${status}`}
      role="progressbar"
      aria-label={label || `進度 ${percent}%`}
      aria-valuemin="0"
      aria-valuemax="100"
      aria-valuenow={Math.min(100, Math.max(0, visualPercent))}
    >
      <span style={{ width: `${visualPercent}%` }} />
    </div>
  );
}

export function CoachHeader({ dateLabel, modeLabel }) {
  return (
    <section className="os-coach-header">
      <div>
        <p className="os-kicker">AI Nutrition Operating System</p>
        <h1>今日飲食教練</h1>
        <div className="os-header-meta">
          <span>{dateLabel}</span>
          <span>模式：{modeLabel}</span>
        </div>
      </div>
      <Link to="/recognition" className="os-primary-cta">
        + 掃描下一餐
      </Link>
    </section>
  );
}

export function CoachHeroCard({ dateLabel, memberLabel, summary, calorieTarget, coachSummary }) {
  const ringPercent = Math.min(100, Math.max(0, calorieTarget?.visualPercent || 0));
  const hasCalorieTarget = Boolean(calorieTarget?.hasTarget);
  const status = calorieTarget?.status || "low";
  const ringStyle = {
    "--orb-progress": `${ringPercent}%`,
  };

  return (
    <section className={`os-hero os-hero--${status}`}>
      <div className="os-hero-copy">
        <p className="os-kicker">Today Command Center</p>
        <h2>{coachSummary.title}</h2>
        <div className="os-hero-numbers">
          <strong>{formatAmount(summary.calories, "千卡")}</strong>
          <span>/ {formatAmount(calorieTarget?.target || 0, "千卡")}</span>
        </div>
        <p>{coachSummary.message}</p>
        <div className="os-quick-actions">
          <a href="#next-meal">下一餐建議</a>
          <a href="#training-recovery">今日平衡方案</a>
        </div>
        <div className="os-hero-context">
          <span>{coachSummary.state}</span>
          <span>{dateLabel}</span>
          <span>{memberLabel}</span>
        </div>
      </div>

      <div className={`live-calorie-orb live-calorie-orb--${status}`} style={ringStyle}>
        <div className="live-calorie-orb-inner">
          <span>今日已吃</span>
          <strong>{formatAmount(summary.calories, "千卡").replace("千卡", " kcal")}</strong>
          <b>{hasCalorieTarget ? `${calorieTarget?.percent || 0}%` : "--"}</b>
          <small>{hasCalorieTarget ? calorieTarget?.remaining?.text : "尚未設定目標"}</small>
        </div>
      </div>
    </section>
  );
}

export function TodayDecisionStrip({ items }) {
  return (
    <section className="os-decision-strip" aria-label="今天下一步">
      {items.map((item) => (
        <article className={`os-decision-card os-decision-card--${item.tone || "normal"}`} key={item.label}>
          <span>{item.label}</span>
          <strong>{item.value}</strong>
          <small>{item.meta}</small>
        </article>
      ))}
    </section>
  );
}

export function GoalModeSelector({ goalMode, onChange }) {
  return (
    <section className="os-section os-mode-section">
      <div className="os-section-heading">
        <p className="os-kicker">Goal Mode</p>
        <h2>今天用哪一種策略</h2>
      </div>
      <div className="os-mode-grid">
        {Object.values(GOAL_MODES).map((mode) => (
          <button
            key={mode.key}
            type="button"
            className={`os-mode-card ${goalMode === mode.key ? "is-active" : ""}`}
            onClick={() => onChange(mode.key)}
          >
            {goalMode === mode.key ? <span className="os-current-badge">目前模式</span> : null}
            <strong>{mode.label}</strong>
            <small>{mode.targetUser}</small>
            <em>{mode.nutritionStrategy}</em>
            <b>{mode.exerciseStrategy}</b>
          </button>
        ))}
      </div>
    </section>
  );
}

export function NutritionTargetGrid({ targets }) {
  return (
    <section className="os-section">
      <div className="os-section-heading">
        <p className="os-kicker">Nutrition Targets</p>
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
              label={`${target.label}進度`}
            />
          </article>
        ))}
      </div>
    </section>
  );
}

export function DailyMissions({ missions }) {
  return (
    <section className="os-section os-mission-card">
      <div className="os-section-heading">
        <p className="os-kicker">Action Board</p>
        <h2>今日任務</h2>
      </div>
      <ol className="os-mission-list">
        {missions.slice(0, 3).map((mission, index) => (
          <li key={mission}>
            <span>{String(index + 1).padStart(2, "0")}</span>
            <p>{mission}</p>
            <b>{index === 0 ? "優先" : "今日"}</b>
          </li>
        ))}
      </ol>
    </section>
  );
}

export function TrainingCoachCard({ goalMode, trainingDayType, onTrainingDayChange, advice }) {
  const mode = getGoalModeConfig(goalMode);

  return (
    <section className="os-section os-training-card" id="training-recovery">
      <div className="os-section-heading">
        <p className="os-kicker">Training + Recovery</p>
        <h2>{advice.title}</h2>
      </div>
      <label className="os-training-select">
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
      <div className="os-soft-badge">{mode.exerciseStrategy}</div>
    </section>
  );
}

export function NextMealSuggestion({ suggestion }) {
  return (
    <section className="os-section os-meal-card" id="next-meal">
      <div className="os-section-heading os-section-heading-row">
        <div>
          <p className="os-kicker">Meal Intelligence</p>
          <h2>{suggestion.title}</h2>
        </div>
        <span className="os-ai-badge">AI 建議</span>
      </div>
      <div className="os-meal-direction">
        <span>推薦方向</span>
        <strong>{suggestion.direction}</strong>
        <p>{suggestion.reason}</p>
      </div>
      <div className="os-chip-group">
        <span>推薦</span>
        {suggestion.recommended.map((item) => (
          <strong key={item}>{item}</strong>
        ))}
      </div>
      <div className="os-chip-group os-chip-group--avoid">
        <span>避免</span>
        {suggestion.avoid.map((item) => (
          <strong key={item}>{item}</strong>
        ))}
      </div>
      <Link to="/recognition" className="os-secondary-cta">
        掃描下一餐
      </Link>
    </section>
  );
}

export function ExerciseRecoveryCard({ plan }) {
  return (
    <section className={`os-section os-recovery-card ${plan.shouldShow ? "is-active" : ""}`}>
      <div className="os-section-heading">
        <p className="os-kicker">Balance Plan</p>
        <h2>{plan.shouldShow ? "今日平衡方案" : "目前不需要補償運動"}</h2>
      </div>
      <p>{plan.message}</p>
      <div className="os-exercise-grid">
        {plan.options.map((option) => (
          <article key={option.name}>
            <span>{option.intensity}</span>
            <strong>{option.name}</strong>
            <b>{option.minutes} 分鐘</b>
            <small>{option.note}</small>
          </article>
        ))}
      </div>
      <small className="os-helper-note">估算值，請依自身體能調整。也可以分 2-3 天用小幅飲食調整平衡。</small>
      {plan.usesDefaultWeight ? <small className="os-helper-note">未設定體重時會先以 70kg 估算。</small> : null}
    </section>
  );
}

export function MacroGapAnalysis({ targets }) {
  return (
    <section className="os-section os-macro-panel">
      <div className="os-section-heading">
        <p className="os-kicker">Macro Balance</p>
        <h2>營養平衡</h2>
      </div>
      <div className="os-macro-list">
        {targets.map((target) => (
          <article className={`os-macro-row os-macro-row--${target.status}`} key={target.key}>
            <span className="os-macro-token">{target.token}</span>
            <div className="os-macro-main">
              <div>
                <strong>{target.label}</strong>
                <small>
                  {formatAmount(target.used, target.unit)} / {target.hasTarget ? formatAmount(target.target, target.unit) : "--"}
                </small>
              </div>
              <ProgressBar
                target={target.target}
                percent={target.percent}
                visualPercent={target.visualPercent}
                status={target.status}
                label={`${target.label}進度`}
              />
            </div>
            <div className="os-macro-result">
              <strong>{target.hasTarget ? `${target.percent}%` : "--"}</strong>
              <small>{target.remaining.text}</small>
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}

export function PostLogImpactCard({ impact }) {
  if (!impact) return null;

  return (
    <section className="os-section os-impact-card">
      <div className="os-section-heading">
        <p className="os-kicker">Latest Impact</p>
        <h2>已加入 {impact.foodName}</h2>
      </div>
      <p>{impact.message}</p>
      <div className="os-impact-row">
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
    <section className="os-section os-memory-card">
      <div className="os-section-heading">
        <p className="os-kicker">Personal Memory</p>
        <h2>{review.ready ? "你的飲食模式" : "我會越來越懂你"}</h2>
      </div>
      <p>{review.message}</p>
      {review.ready ? (
        <div className="os-memory-stats">
          <div>
            <span>平均熱量</span>
            <strong>{formatAmount(review.averageCalories, "千卡")}</strong>
          </div>
          <div>
            <span>蛋白達標</span>
            <strong>
              {review.proteinDays}/{review.totalDays} 天
            </strong>
          </div>
          <div>
            <span>脂肪超標</span>
            <strong>
              {review.fatOverDays}/{review.totalDays} 天
            </strong>
          </div>
        </div>
      ) : null}
    </section>
  );
}

export function SmartScanButton() {
  return (
    <Link to="/recognition" className="os-floating-scan">
      + 掃描
    </Link>
  );
}

export function FloatingCoachButton() {
  return (
    <a href="#next-meal" className="os-floating-coach">
      問教練
    </a>
  );
}

export function EmptyState() {
  return (
    <div className="os-empty-state">
      <strong>今天還沒有飲食紀錄</strong>
      <p>掃描你的第一份餐點，我會幫你估算熱量與下一餐策略。</p>
      <Link to="/recognition" className="os-primary-cta">
        開始掃描
      </Link>
    </div>
  );
}
