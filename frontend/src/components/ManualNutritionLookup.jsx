import { useEffect, useMemo, useState } from "react";

const COPY = {
  title: "手動查詢熱量",
  description: "如果 AI 辨識失準，還是可以直接搜尋食物名稱，或自己輸入食物與營養數值。",
  placeholder: "輸入食物名稱或關鍵字，例如：炒飯、pizza、dumpling",
  loading: "正在載入食物資料...",
  noData: "目前沒有可查詢的食物資料。",
  noMatch: "找不到符合的食物，請換個關鍵字。",
  searchLabel: "食物名稱",
  portionLabel: "份量選擇",
  customTitle: "手動輸入 / 修改",
  customHint: "如果有先選資料庫食物，沒有填的欄位會自動沿用資料庫數值。",
  foodName: "食物名稱",
  portionInput: "份量文字",
  recordDateTime: "紀錄日期時間",
  calories: "熱量",
  protein: "蛋白質",
  fat: "脂肪",
  carbs: "碳水",
  quickSummary: "手動查詢結果",
  portionUnit: "份",
  apply: "套用成主結果",
  applied: "已套用為主結果",
  replace: "改用這個結果",
  clear: "取消套用",
  appliedHint: "套用後，右側主結果和加入今日日誌都會以這筆手動資料為主。",
  databaseSource: "資料來源：食物資料庫",
  manualSource: "資料來源：手動輸入",
  fillFromDatabase: "套入資料庫",
};

function normalizeKeyword(value) {
  return String(value || "").trim().toLowerCase();
}

function findExactProfile(profiles, value) {
  const normalized = normalizeKeyword(value);
  if (!normalized) {
    return null;
  }

  return (
    profiles.find((profile) => normalizeKeyword(profile.display_name) === normalized) ||
    profiles.find((profile) => normalizeKeyword(profile.label) === normalized) ||
    null
  );
}

function formatNumber(value) {
  if (Number.isInteger(value)) {
    return String(value);
  }

  return String(Number(value.toFixed(1)));
}

function getCurrentDateTimeLocal() {
  const now = new Date();
  const year = now.getFullYear();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  const hours = String(now.getHours()).padStart(2, "0");
  const minutes = String(now.getMinutes()).padStart(2, "0");
  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

function buildRecordedAt(dateTimeValue) {
  const raw = String(dateTimeValue || "").trim();
  if (!raw) {
    return null;
  }

  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    return null;
  }

  return parsed.toISOString();
}

function scalePortionLabel(baseLabel, multiplier) {
  const label = String(baseLabel || "").trim();
  if (!label) {
    return `${multiplier} ${COPY.portionUnit}`;
  }

  const quantityMatch = label.match(/^(\d+(?:\.\d+)?)\s*(.*)$/);
  if (!quantityMatch) {
    return `${multiplier} x ${label}`;
  }

  const baseQuantity = Number(quantityMatch[1]);
  const restLabel = quantityMatch[2] || "";
  const scaledQuantity = formatNumber(baseQuantity * multiplier);
  const scaledRest = restLabel.replace(/\((\d+(?:\.\d+)?)\s*(g|ml)\)/gi, (_, amount, unit) => {
    const scaledAmount = formatNumber(Number(amount) * multiplier);
    return `(${scaledAmount}${unit})`;
  });

  return `${scaledQuantity} ${scaledRest}`.trim();
}

function buildManualSelection(profile, multiplier) {
  if (!profile) {
    return null;
  }

  return {
    label: profile.label,
    sourceType: "database",
    foodName: profile.display_name || profile.label,
    basePortionLabel: profile.default_portion_label,
    portionLabel: scalePortionLabel(profile.default_portion_label, multiplier),
    multiplier,
    nutrition: {
      calories: Math.round(Number(profile.calories || 0) * multiplier),
      protein: Number((Number(profile.protein || 0) * multiplier).toFixed(1)),
      fat: Number((Number(profile.fat || 0) * multiplier).toFixed(1)),
      carbs: Number((Number(profile.carbs || 0) * multiplier).toFixed(1)),
    },
  };
}

function parseOptionalNumber(value) {
  const raw = String(value ?? "").trim();
  if (!raw) {
    return null;
  }

  const numeric = Number(raw);
  if (Number.isNaN(numeric)) {
    return null;
  }

  return numeric;
}

function getEditableValue(overrideValue, fallbackValue) {
  if (String(overrideValue ?? "") !== "") {
    return overrideValue;
  }

  if (fallbackValue === null || fallbackValue === undefined || fallbackValue === "") {
    return "";
  }

  return String(fallbackValue);
}

function NutritionMetric({ label, value, unit }) {
  return (
    <div className="manual-lookup-metric">
      <span>{label}</span>
      <strong>
        {value}
        {unit}
      </strong>
    </div>
  );
}

function ManualNutritionLookup({
  profiles,
  loading,
  error,
  onSelectionChange,
  appliedSelection,
  onApplySelection,
  onClearAppliedSelection,
}) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeField, setActiveField] = useState("search");
  const [selectedLabel, setSelectedLabel] = useState("");
  const [multiplier, setMultiplier] = useState(1);
  const [recordDateTime, setRecordDateTime] = useState(getCurrentDateTimeLocal());
  const [overrides, setOverrides] = useState({
    foodName: "",
    portionLabel: "",
    calories: "",
    protein: "",
    fat: "",
    carbs: "",
  });

  const normalizedQuery = normalizeKeyword(query);
  const filteredProfiles = profiles
    .filter((profile) => {
      if (!normalizedQuery) {
        return true;
      }

      const candidates = [profile.display_name, profile.label, profile.parent_category];
      return candidates.some((candidate) => normalizeKeyword(candidate).includes(normalizedQuery));
    })
    .slice(0, 8);

  const selectedProfile = profiles.find((profile) => profile.label === selectedLabel) || null;
  const baseSelection = useMemo(
    () => buildManualSelection(selectedProfile, multiplier),
    [selectedProfile, multiplier]
  );

  const effectiveSelection = useMemo(() => {
    const foodName =
      String(overrides.foodName || "").trim() ||
      baseSelection?.foodName ||
      String(query || "").trim();
    const portionLabel =
      String(overrides.portionLabel || "").trim() ||
      baseSelection?.portionLabel ||
      `${multiplier} ${COPY.portionUnit}`;

    const nutrition = {
      calories: parseOptionalNumber(overrides.calories) ?? Number(baseSelection?.nutrition.calories || 0),
      protein: parseOptionalNumber(overrides.protein) ?? Number(baseSelection?.nutrition.protein || 0),
      fat: parseOptionalNumber(overrides.fat) ?? Number(baseSelection?.nutrition.fat || 0),
      carbs: parseOptionalNumber(overrides.carbs) ?? Number(baseSelection?.nutrition.carbs || 0),
    };

    const hasAnyNutrition = Object.values(nutrition).some((value) => Number(value || 0) > 0);
    const isValid = Boolean(foodName) && (Boolean(selectedProfile) || hasAnyNutrition);
    if (!isValid) {
      return null;
    }

    return {
      label:
        selectedProfile?.label ||
        `manual_${foodName.toLowerCase().replace(/\s+/g, "_").replace(/[^\w\u4e00-\u9fff-]/g, "")}`,
      sourceType: selectedProfile ? "database" : "manual",
      foodName,
      basePortionLabel: selectedProfile?.default_portion_label || "",
      portionLabel,
      multiplier,
      recordedDateTime: recordDateTime,
      recordedAt: buildRecordedAt(recordDateTime),
      nutrition: {
        calories: Math.round(Number(nutrition.calories || 0)),
        protein: Number(Number(nutrition.protein || 0).toFixed(1)),
        fat: Number(Number(nutrition.fat || 0).toFixed(1)),
        carbs: Number(Number(nutrition.carbs || 0).toFixed(1)),
      },
    };
  }, [baseSelection, multiplier, overrides, query, recordDateTime, selectedProfile]);

  const isApplied =
    Boolean(appliedSelection) &&
    Boolean(effectiveSelection) &&
    appliedSelection.label === effectiveSelection.label &&
    appliedSelection.portionLabel === effectiveSelection.portionLabel &&
    appliedSelection.recordedAt === effectiveSelection.recordedAt &&
    appliedSelection.nutrition.calories === effectiveSelection.nutrition.calories &&
    appliedSelection.nutrition.protein === effectiveSelection.nutrition.protein &&
    appliedSelection.nutrition.fat === effectiveSelection.nutrition.fat &&
    appliedSelection.nutrition.carbs === effectiveSelection.nutrition.carbs;

  useEffect(() => {
    onSelectionChange(effectiveSelection);
  }, [effectiveSelection, onSelectionChange]);

  function handleQueryChange(event, field = "search") {
    const nextValue = event.target.value;
    setQuery(nextValue);
    setIsOpen(true);
    setActiveField(field);

    const exactProfile = findExactProfile(profiles, nextValue);
    if (exactProfile) {
      setSelectedLabel(exactProfile.label);
      return;
    }

    if (!selectedProfile) {
      return;
    }

    const matchesSelected =
      nextValue.trim() === String(selectedProfile.display_name || "").trim() ||
      nextValue.trim() === String(selectedProfile.label || "").trim();

    if (!matchesSelected) {
      setSelectedLabel("");
    }
  }

  function handleProfileSelect(profile) {
    setSelectedLabel(profile.label);
    setQuery(profile.display_name || profile.label);
    setMultiplier(1);
    setOverrides({
      foodName: "",
      portionLabel: "",
      calories: "",
      protein: "",
      fat: "",
      carbs: "",
    });
    setIsOpen(false);
  }

  function handleInputKeyDown(event) {
    if (event.key === "Enter" && filteredProfiles.length > 0) {
      event.preventDefault();
      handleProfileSelect(filteredProfiles[0]);
    }

    if (event.key === "Escape") {
      setIsOpen(false);
    }
  }

  function handleOverrideChange(field, value) {
    setOverrides((current) => ({
      ...current,
      [field]: value,
    }));
  }

  function handleFillFromDatabase() {
    if (!baseSelection) {
      return;
    }

    setOverrides({
      foodName: baseSelection.foodName,
      portionLabel: baseSelection.portionLabel,
      calories: String(baseSelection.nutrition.calories),
      protein: String(baseSelection.nutrition.protein),
      fat: String(baseSelection.nutrition.fat),
      carbs: String(baseSelection.nutrition.carbs),
    });
  }

  return (
    <div className="manual-lookup-card">
      <div className="manual-lookup-header">
        <h3>{COPY.title}</h3>
        <p>{COPY.description}</p>
      </div>

      <label className="manual-lookup-field">
        <span>{COPY.searchLabel}</span>
        <div className="manual-lookup-input-wrap">
          <input
            type="text"
            value={query}
            placeholder={COPY.placeholder}
            onChange={(event) => handleQueryChange(event, "search")}
            onFocus={() => {
              setActiveField("search");
              setIsOpen(true);
            }}
            onBlur={() => window.setTimeout(() => setIsOpen(false), 120)}
            onKeyDown={handleInputKeyDown}
          />
          {isOpen && activeField === "search" ? (
            <div className="manual-lookup-dropdown">
              {loading ? <div className="manual-lookup-empty">{COPY.loading}</div> : null}
              {!loading && error ? <div className="manual-lookup-empty">{error}</div> : null}
              {!loading && !error && profiles.length === 0 ? (
                <div className="manual-lookup-empty">{COPY.noData}</div>
              ) : null}
              {!loading && !error && profiles.length > 0 && filteredProfiles.length === 0 ? (
                <div className="manual-lookup-empty">{COPY.noMatch}</div>
              ) : null}
              {!loading &&
                !error &&
                filteredProfiles.map((profile) => (
                  <button
                    key={profile.label}
                    type="button"
                    className={`manual-lookup-option ${
                      profile.label === selectedLabel ? "active" : ""
                    }`}
                    onMouseDown={(event) => event.preventDefault()}
                    onClick={() => handleProfileSelect(profile)}
                  >
                    <strong>{profile.display_name || profile.label}</strong>
                    <span>{profile.default_portion_label}</span>
                  </button>
                ))}
            </div>
          ) : null}
        </div>
      </label>

      {selectedProfile ? (
        <div className="manual-lookup-field">
          <span>{COPY.portionLabel}</span>
          <div className="manual-portion-options">
            {[1, 2, 3].map((value) => (
              <button
                key={value}
                type="button"
                className={`manual-portion-chip ${multiplier === value ? "active" : ""}`}
                onClick={() => setMultiplier(value)}
              >
                {scalePortionLabel(selectedProfile.default_portion_label, value)}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      <div className="manual-edit-card">
        <div className="manual-lookup-header">
          <h3>{COPY.customTitle}</h3>
          <p>{COPY.customHint}</p>
        </div>

        <div className="manual-edit-grid">
          <label className="manual-edit-wide">
            <span>{COPY.foodName}</span>
            <div className="manual-lookup-input-wrap">
              <input
                type="text"
                value={getEditableValue(overrides.foodName, baseSelection?.foodName || query)}
                onChange={(event) => {
                  handleOverrideChange("foodName", event.target.value);
                  handleQueryChange(event, "manual");
                }}
                onFocus={() => {
                  setActiveField("manual");
                  setIsOpen(true);
                }}
                onBlur={() => window.setTimeout(() => setIsOpen(false), 120)}
                onKeyDown={handleInputKeyDown}
                placeholder="例如：餃子、牛排、炒飯"
              />
              {isOpen && activeField === "manual" ? (
                <div className="manual-lookup-dropdown">
                  {loading ? <div className="manual-lookup-empty">{COPY.loading}</div> : null}
                  {!loading && error ? <div className="manual-lookup-empty">{error}</div> : null}
                  {!loading && !error && profiles.length === 0 ? (
                    <div className="manual-lookup-empty">{COPY.noData}</div>
                  ) : null}
                  {!loading && !error && profiles.length > 0 && filteredProfiles.length === 0 ? (
                    <div className="manual-lookup-empty">{COPY.noMatch}</div>
                  ) : null}
                  {!loading &&
                    !error &&
                    filteredProfiles.map((profile) => (
                      <button
                        key={`manual-${profile.label}`}
                        type="button"
                        className={`manual-lookup-option ${
                          profile.label === selectedLabel ? "active" : ""
                        }`}
                        onMouseDown={(event) => event.preventDefault()}
                        onClick={() => handleProfileSelect(profile)}
                      >
                        <strong>{profile.display_name || profile.label}</strong>
                        <span>{profile.default_portion_label}</span>
                      </button>
                    ))}
                </div>
              ) : null}
            </div>
          </label>

          <label>
            <span>{COPY.recordDateTime}</span>
            <input
              type="datetime-local"
              value={recordDateTime}
              onChange={(event) => setRecordDateTime(event.target.value)}
            />
          </label>

          <label className="manual-edit-wide">
            <span>{COPY.portionInput}</span>
            <input
              type="text"
              value={getEditableValue(overrides.portionLabel, baseSelection?.portionLabel)}
              onChange={(event) => handleOverrideChange("portionLabel", event.target.value)}
              placeholder="例如：6 顆、1 碗、2 片"
            />
          </label>

          <label>
            <span>{COPY.calories}</span>
            <input
              type="number"
              min="0"
              step="1"
              value={getEditableValue(overrides.calories, baseSelection?.nutrition.calories)}
              onChange={(event) => handleOverrideChange("calories", event.target.value)}
              placeholder="kcal"
            />
          </label>

          <label>
            <span>{COPY.protein}</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={getEditableValue(overrides.protein, baseSelection?.nutrition.protein)}
              onChange={(event) => handleOverrideChange("protein", event.target.value)}
              placeholder="g"
            />
          </label>

          <label>
            <span>{COPY.fat}</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={getEditableValue(overrides.fat, baseSelection?.nutrition.fat)}
              onChange={(event) => handleOverrideChange("fat", event.target.value)}
              placeholder="g"
            />
          </label>

          <label>
            <span>{COPY.carbs}</span>
            <input
              type="number"
              min="0"
              step="0.1"
              value={getEditableValue(overrides.carbs, baseSelection?.nutrition.carbs)}
              onChange={(event) => handleOverrideChange("carbs", event.target.value)}
              placeholder="g"
            />
          </label>
        </div>

        <div className="manual-lookup-actions">
          <button
            type="button"
            className="secondary-button"
            onClick={handleFillFromDatabase}
            disabled={!baseSelection}
          >
            {COPY.fillFromDatabase}
          </button>
        </div>
      </div>

      {effectiveSelection ? (
        <div className="manual-lookup-preview">
          <div className="manual-lookup-summary">
            <span>{COPY.quickSummary}</span>
            <strong>{effectiveSelection.foodName}</strong>
            <small>{effectiveSelection.portionLabel}</small>
            <small>{recordDateTime.replace("T", " ")}</small>
            <small>
              {effectiveSelection.sourceType === "database"
                ? COPY.databaseSource
                : COPY.manualSource}
            </small>
          </div>
          <div className="manual-lookup-actions">
            <button
              type="button"
              className={`secondary-button manual-lookup-apply ${isApplied ? "active" : ""}`}
              onClick={() => onApplySelection(effectiveSelection)}
            >
              {isApplied ? COPY.applied : appliedSelection ? COPY.replace : COPY.apply}
            </button>
            {appliedSelection ? (
              <button
                type="button"
                className="manual-lookup-clear"
                onClick={onClearAppliedSelection}
              >
                {COPY.clear}
              </button>
            ) : null}
          </div>
          {isApplied ? <p className="manual-lookup-applied-hint">{COPY.appliedHint}</p> : null}
          <div className="manual-lookup-metrics">
            <NutritionMetric label={COPY.calories} value={effectiveSelection.nutrition.calories} unit=" kcal" />
            <NutritionMetric label={COPY.protein} value={effectiveSelection.nutrition.protein} unit=" g" />
            <NutritionMetric label={COPY.fat} value={effectiveSelection.nutrition.fat} unit=" g" />
            <NutritionMetric label={COPY.carbs} value={effectiveSelection.nutrition.carbs} unit=" g" />
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default ManualNutritionLookup;
