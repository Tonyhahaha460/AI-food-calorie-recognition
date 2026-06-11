const COPY = {
  analysis: "\u5206\u6790\u7d50\u679c",
  title: "\u9910\u9ede\u5206\u6790",
  emptyDescription:
    "\u4e0a\u50b3\u9910\u9ede\u7167\u7247\u5f8c\uff0c\u7cfb\u7d71\u6703\u986f\u793a\u8fa8\u8b58\u51fa\u7684\u98df\u7269\u8207\u71df\u990a\u4f30\u7b97\u3002",
  previewAlt: "\u5206\u6790\u5716\u7247\u9810\u89bd",
  classificationMode:
    "\u76ee\u524d\u4f7f\u7528\u98df\u7269\u5206\u985e\u52a0\u4e0a\u8cc7\u6599\u5eab\u71df\u990a\u67e5\u8868\u6a21\u5f0f\u3002",
  regressionMode:
    "\u76ee\u524d\u4f7f\u7528 AI \u71df\u990a\u4f30\u7b97\u6a21\u5f0f\uff0c\u540d\u7a31\u50c5\u4f9b\u53c3\u8003\u3002",
  warning:
    "\u9019\u6b21\u6709\u90e8\u5206\u7d50\u679c\u4fe1\u5fc3\u4e0d\u8db3\uff0c\u6211\u5df2\u6539\u6210\u4fdd\u5b88\u986f\u793a\uff0c\u4e0d\u518d\u786c\u5957\u932f\u8aa4\u9910\u9ede\u540d\u7a31\u3002",
  totalCalories: "\u7e3d\u71b1\u91cf",
  protein: "\u86cb\u767d\u8cea",
  fat: "\u8102\u80aa",
  carbs: "\u78b3\u6c34",
  itemCount: "\u98df\u7269\u6578\u91cf",
  uncertainFood: "\u5f85\u78ba\u8a8d\u9910\u9ede",
  predictionSource: "\u6a21\u578b\u4f86\u6e90\uff1a",
  closestMatch: "\u6700\u63a5\u8fd1\u9910\u9ede\uff1a",
  customData: "\u81ea\u5efa\u8cc7\u6599",
  calories: "\u71b1\u91cf",
  suggestion: "\u98f2\u98df\u5efa\u8b70",
  candidates: "\u53ef\u80fd\u5019\u9078",
  unknown: "\u672a\u77e5",
  manualTitle: "\u624b\u52d5\u67e5\u8a62\u71b1\u91cf",
  manualDescription:
    "\u5c31\u7b97 AI \u66ab\u6642\u6c92\u6709\u8fa8\u8b58\u6e96\uff0c\u9019\u88e1\u4e5f\u6703\u4fdd\u7559\u4f60\u624b\u52d5\u9078\u64c7\u7684\u98df\u7269\u8207\u4efd\u91cf\u3002",
  manualSource: "\u8cc7\u6599\u4f86\u6e90\uff1a\u98df\u7269\u8cc7\u6599\u5eab",
  manualEmpty:
    "\u5de6\u5074\u624b\u52d5\u8f38\u5165\u98df\u7269\u540d\u7a31\u5f8c\uff0c\u9019\u88e1\u6703\u540c\u6b65\u986f\u793a\u67e5\u8a62\u7d50\u679c\u3002",
  manualAppliedMode:
    "\u76ee\u524d\u4e3b\u7d50\u679c\u5df2\u6539\u7528\u624b\u52d5\u67e5\u8a62\uff0cAI \u8fa8\u8b58\u7d50\u679c\u4fdd\u7559\u5728\u4e0b\u65b9\u53c3\u8003\u3002",
  manualAppliedSource: "\u624b\u52d5\u5957\u7528",
  aiReference: "AI \u5206\u6790\u53c3\u8003",
};

function formatValue(value, unit = "") {
  if (value === null || value === undefined || value === "") {
    return `--${unit}`;
  }
  return `${value}${unit}`;
}

function NutritionCard({ label, value, unit }) {
  return (
    <div className="nutrition-item">
      <span>{label}</span>
      <strong>{formatValue(value, unit)}</strong>
    </div>
  );
}

function CandidateList({ alternatives }) {
  if (!alternatives || alternatives.length === 0) {
    return null;
  }

  return (
    <div className="candidate-list">
      <span className="candidate-title">{COPY.candidates}</span>
      <div className="candidate-chips">
        {alternatives.slice(0, 3).map((candidate, index) => (
          <span className="candidate-chip" key={`${candidate.source}-${candidate.raw_label}-${index}`}>
            {candidate.raw_label || candidate.label || COPY.unknown}:{" "}
            {Math.round((candidate.confidence || 0) * 100)}%
          </span>
        ))}
      </div>
    </div>
  );
}

function ManualLookupCard({ manualLookup }) {
  if (!manualLookup) {
    return null;
  }

  const sourceText =
    manualLookup.sourceType === "manual" ? "資料來源：手動輸入" : COPY.manualSource;

  return (
    <div className="manual-results-card">
      <div className="manual-results-header">
        <div>
          <h3>{COPY.manualTitle}</h3>
          <p>{COPY.manualDescription}</p>
        </div>
        <div className="manual-results-badge">{sourceText}</div>
      </div>

      <div className="manual-results-summary">
        <strong>{manualLookup.foodName}</strong>
        <span>{manualLookup.portionLabel}</span>
      </div>

      <div className="nutrition-grid">
        <NutritionCard label={COPY.calories} value={manualLookup.nutrition.calories} unit=" kcal" />
        <NutritionCard label={COPY.protein} value={manualLookup.nutrition.protein} unit=" g" />
        <NutritionCard label={COPY.fat} value={manualLookup.nutrition.fat} unit=" g" />
        <NutritionCard label={COPY.carbs} value={manualLookup.nutrition.carbs} unit=" g" />
      </div>
    </div>
  );
}

function buildAppliedManualResult(manualLookup) {
  if (!manualLookup) {
    return null;
  }

  return {
    analysis_mode: "manual_lookup",
    total_calories: manualLookup.nutrition.calories,
    total_nutrition: {
      calories: manualLookup.nutrition.calories,
      protein: manualLookup.nutrition.protein,
      fat: manualLookup.nutrition.fat,
      carbs: manualLookup.nutrition.carbs,
    },
    suggestion:
      "\u76ee\u524d\u4e3b\u7d50\u679c\u4f7f\u7528\u624b\u52d5\u67e5\u8a62\u8cc7\u6599\uff0c\u53ef\u4ee5\u518d\u5229\u7528 AI \u7d50\u679c\u5c0d\u7167\uff0c\u6216\u91cd\u65b0\u62cd\u651d\u66f4\u6e05\u695a\u7684\u5716\u7247\u3002",
    items: [
      {
        food_name: manualLookup.foodName,
        confidence: 1,
        estimated_portion: manualLookup.portionLabel,
        nutrition: manualLookup.nutrition,
        prediction_source: COPY.manualAppliedSource,
        raw_prediction_label: manualLookup.label,
        decision_reason: "manual_override",
        alternatives: [],
        is_uncertain: false,
      },
    ],
    has_uncertain_items: false,
  };
}

function ItemCard({ item, index }) {
  return (
    <article className={`detected-item-card ${item.is_uncertain ? "uncertain-item-card" : ""}`}>
      <div className="detected-item-header">
        <div>
          <h3>{item.food_name || COPY.uncertainFood}</h3>
          <p>{item.estimated_portion}</p>
          {item.is_uncertain ? <p className="uncertain-text">{item.uncertain_message}</p> : null}
          {item.prediction_source ? (
            <p className="prediction-source-text">
              {COPY.predictionSource}
              {item.prediction_source}
            </p>
          ) : null}
          {item.closest_match_name ? (
            <p className="closest-match-text">
              {COPY.closestMatch}
              {item.closest_parent_name ? `${item.closest_parent_name} / ` : ""}
              {item.closest_match_name}
              {item.closest_match_source
                ? ` (${item.closest_match_source === "nutrition5k" ? "Nutrition5k" : COPY.customData})`
                : ""}
            </p>
          ) : null}
        </div>

        <div className="confidence-chip">{Math.round((item.confidence || 0) * 100)}%</div>
      </div>

      <CandidateList alternatives={item.alternatives} />

      <div className="nutrition-grid">
        <NutritionCard label={COPY.calories} value={item.nutrition.calories} unit=" kcal" />
        <NutritionCard label={COPY.protein} value={item.nutrition.protein} unit=" g" />
        <NutritionCard label={COPY.fat} value={item.nutrition.fat} unit=" g" />
        <NutritionCard label={COPY.carbs} value={item.nutrition.carbs} unit=" g" />
      </div>
    </article>
  );
}

function MealResults({ result, previewUrl, manualLookup, appliedManualLookup }) {
  const displayResult = appliedManualLookup ? buildAppliedManualResult(appliedManualLookup) : result;
  const aiReferenceResult = appliedManualLookup && result ? result : null;
  const displayPreview = displayResult?.image_preview || result?.image_preview || previewUrl;

  if (!displayResult) {
    return (
      <section className="panel-card results-panel">
        <div className="section-heading">
          <p className="eyebrow">{COPY.analysis}</p>
          <h2>{COPY.title}</h2>
        </div>
        <p>{COPY.emptyDescription}</p>
        <ManualLookupCard manualLookup={manualLookup} />
      </section>
    );
  }

  const isRegression = displayResult.analysis_mode === "regression";
  const isClassificationLookup = displayResult.analysis_mode === "classification_lookup";
  const isManualApplied = Boolean(appliedManualLookup);

  return (
    <section className="panel-card results-panel">
      <div className="section-heading">
        <p className="eyebrow">{COPY.analysis}</p>
        <h2>{COPY.title}</h2>
      </div>

      <div className="result-overview-grid">
        {displayPreview ? (
          <div className="preview-wrapper compact-preview">
            <img src={displayPreview} alt={COPY.previewAlt} className="preview-image" />
          </div>
        ) : (
          <div className="preview-placeholder compact-preview">{COPY.previewAlt}</div>
        )}

        <div className="totals-card">
          {isClassificationLookup ? <p className="result-mode-note">{COPY.classificationMode}</p> : null}
          {isRegression ? <p className="result-mode-note">{COPY.regressionMode}</p> : null}
          {isManualApplied ? <p className="result-mode-note">{COPY.manualAppliedMode}</p> : null}
          {displayResult.has_uncertain_items ? <p className="result-warning-note">{COPY.warning}</p> : null}

          <div className="total-calories">
            <span>{COPY.totalCalories}</span>
            <strong>{formatValue(displayResult.total_calories, " kcal")}</strong>
          </div>

          <div className="nutrition-grid">
            <NutritionCard
              label={COPY.protein}
              value={displayResult.total_nutrition.protein}
              unit=" g"
            />
            <NutritionCard label={COPY.fat} value={displayResult.total_nutrition.fat} unit=" g" />
            <NutritionCard
              label={COPY.carbs}
              value={displayResult.total_nutrition.carbs}
              unit=" g"
            />
            <NutritionCard label={COPY.itemCount} value={displayResult.items.length} unit="" />
          </div>
        </div>
      </div>

      {!isManualApplied && manualLookup ? <ManualLookupCard manualLookup={manualLookup} /> : null}

      <div className="detected-items-list">
        {displayResult.items.map((item, index) => (
          <ItemCard item={item} index={index} key={`${item.food_name}-${index}`} />
        ))}
      </div>

      {aiReferenceResult ? (
        <div className="manual-results-card ai-reference-card">
          <div className="manual-results-header">
            <div>
              <h3>{COPY.aiReference}</h3>
              <p>{COPY.manualAppliedMode}</p>
            </div>
          </div>
          <div className="detected-items-list ai-reference-list">
            {aiReferenceResult.items.map((item, index) => (
              <ItemCard item={item} index={index} key={`ai-reference-${item.food_name}-${index}`} />
            ))}
          </div>
        </div>
      ) : null}

      <div className="suggestion-box">
        <h3>{COPY.suggestion}</h3>
        <p>{displayResult.suggestion}</p>
      </div>
    </section>
  );
}

export default MealResults;
