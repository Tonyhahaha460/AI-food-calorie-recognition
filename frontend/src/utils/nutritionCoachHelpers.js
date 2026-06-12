import { normalizeNutrition } from "./memberJournal.js";

export const GOAL_MODES = {
  maintain: {
    key: "maintain",
    label: "維持體態",
    shortLabel: "維持",
    targetUser: "想穩定體重、維持目前身形的人",
    nutritionStrategy: "熱量接近 TDEE，三大營養素均衡",
    exerciseStrategy: "每週 2-3 次活動，重點是穩定與習慣",
    tone: "平衡、穩定、不要過度限制",
  },
  fat_loss: {
    key: "fat_loss",
    label: "減脂建議",
    shortLabel: "減脂",
    targetUser: "想降低體脂、控制體重的人",
    nutritionStrategy: "小幅熱量赤字、高蛋白、控制高油高糖",
    exerciseStrategy: "重訓 + 有氧，避免只靠少吃",
    tone: "明確、克制、給出可執行的下一餐與運動建議",
  },
  fitness_daily: {
    key: "fitness_daily",
    label: "健人日常",
    shortLabel: "健人",
    targetUser: "有固定健身習慣、想兼顧體態與訓練表現的人",
    nutritionStrategy: "高蛋白，訓練日前後碳水更有彈性",
    exerciseStrategy: "每週 3-5 次重訓，可搭配低中強度有氧",
    tone: "像健身教練，重點放在蛋白質缺口、訓練前後補給與恢復",
  },
};

export const TRAINING_DAY_TYPES = {
  rest: "休息日",
  strength: "重訓日",
  cardio: "有氧日",
  mixed: "重訓 + 有氧",
  active_recovery: "主動恢復",
};

export const EXERCISE_OPTIONS = [
  { name: "快走", met: 4.3, intensity: "低強度", note: "適合大多數人，飯後也比較容易執行" },
  { name: "騎腳踏車", met: 6.8, intensity: "中強度", note: "消耗效率比快走高" },
  { name: "慢跑", met: 7.0, intensity: "中高強度", note: "效率高，但不適合所有人飯後立即進行" },
  { name: "重訓", met: 3.5, intensity: "肌力訓練", note: "熱量消耗不是最高，但有助於維持肌肉量" },
  { name: "爬樓梯", met: 8.8, intensity: "高強度", note: "時間短但強度高" },
];

const HIGH_PROTEIN_FOODS = ["雞胸便當", "滷雞腿便當去皮", "茶葉蛋", "豆腐蛋花湯", "鮪魚飯糰", "牛肉湯", "無糖豆漿", "舒肥雞胸"];
const LOW_FAT_FOODS = ["燙青菜", "水煮蛋", "清湯", "烤地瓜", "舒肥雞胸", "飯糰搭配無糖豆漿", "豆腐湯"];
const CARB_FOODS = ["白飯半碗", "飯糰", "地瓜", "燕麥", "御飯糰", "香蕉"];
const AVOID_FOODS = ["雞排", "鹽酥雞", "奶茶", "炒飯", "炸物", "高油醬料", "三寶飯肥肉多", "滷肉飯大碗"];

export function toNumber(value) {
  if (typeof value === "string") {
    const match = value.replaceAll(",", "").match(/-?\d+(\.\d+)?/);
    return match ? Number(match[0]) || 0 : 0;
  }
  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

export function formatNutritionNumber(value, digits = 1) {
  const numeric = toNumber(value);
  if (Number.isInteger(numeric)) {
    return String(numeric);
  }
  return numeric.toFixed(digits).replace(/\.0$/, "");
}

export function formatAmount(value, unit) {
  const numeric = toNumber(value);
  const rounded = unit === "千卡" ? Math.round(numeric) : Math.round(numeric * 10) / 10;
  return `${Number.isInteger(rounded) ? rounded : rounded.toFixed(1)}${unit}`;
}

export function normalizeFoodEntry(entry = {}) {
  const nutrition = normalizeNutrition(entry);
  return {
    ...entry,
    calories: nutrition.calories,
    protein: nutrition.protein,
    fat: nutrition.fat,
    carbs: nutrition.carbs,
    nutrition,
  };
}

export function getProgressPercent(used, target) {
  const targetValue = toNumber(target);
  if (targetValue <= 0) return 0;
  return Math.round((toNumber(used) / targetValue) * 100);
}

export function getVisualProgressPercent(used, target) {
  return Math.min(100, Math.max(0, getProgressPercent(used, target)));
}

export function getRemainingValue(target, used) {
  return Math.max(toNumber(target) - toNumber(used), 0);
}

export function getExceededValue(used, target) {
  return Math.max(toNumber(used) - toNumber(target), 0);
}

export function getProgressStatus(percent) {
  const value = toNumber(percent);
  if (value >= 100) return "over";
  if (value >= 85) return "near";
  if (value < 40) return "low";
  return "normal";
}

export function getRemainingText(target, used, unit) {
  const targetNumber = toNumber(target);
  const usedNumber = toNumber(used);
  if (targetNumber <= 0) {
    return {
      label: "尚未設定",
      amount: 0,
      text: "尚未設定目標",
      isOver: false,
      hasTarget: false,
    };
  }

  const difference = targetNumber - usedNumber;
  const isOver = difference < 0;
  const amount = Math.abs(difference);
  const label = isOver ? "超出" : "剩餘";
  return {
    label,
    amount,
    text: `${label} ${formatNutritionNumber(amount)}${unit}`,
    isOver,
    hasTarget: true,
  };
}

export function getGoalModeConfig(goalMode) {
  return GOAL_MODES[goalMode] || GOAL_MODES.maintain;
}

export function normalizeNutritionTargets(rawTargets = {}, memberProfile = {}) {
  return {
    calories: toNumber(
      rawTargets.calories ??
        rawTargets.targetCalories ??
        rawTargets.dailyCalories ??
        rawTargets.calorieGoal ??
        rawTargets.caloriesTarget ??
        memberProfile.targetCalories ??
        memberProfile.dailyCalories ??
        memberProfile.calorieGoal ??
        memberProfile.caloriesTarget
    ),
    protein: toNumber(
      rawTargets.protein ??
        rawTargets.targetProtein ??
        rawTargets.proteinGoal ??
        memberProfile.targetProtein ??
        memberProfile.proteinGoal
    ),
    fat: toNumber(rawTargets.fat ?? rawTargets.targetFat ?? rawTargets.fatGoal ?? memberProfile.targetFat ?? memberProfile.fatGoal),
    carbs: toNumber(
      rawTargets.carbs ??
        rawTargets.carbohydrate ??
        rawTargets.carbohydrates ??
        rawTargets.targetCarbs ??
        rawTargets.carbsGoal ??
        memberProfile.targetCarbs ??
        memberProfile.carbsGoal
    ),
  };
}

export function buildNutritionTargets(summary = {}, rawTargets = {}) {
  const targets = normalizeNutritionTargets(rawTargets);
  const normalizedSummary = normalizeFoodEntry(summary);
  const rows = [
    { key: "calories", label: "熱量", unit: "千卡", used: normalizedSummary.calories, target: targets.calories, token: "kcal" },
    { key: "protein", label: "蛋白質", unit: "克", used: normalizedSummary.protein, target: targets.protein, token: "P" },
    { key: "fat", label: "脂肪", unit: "克", used: normalizedSummary.fat, target: targets.fat, token: "F" },
    { key: "carbs", label: "碳水", unit: "克", used: normalizedSummary.carbs, target: targets.carbs, token: "C" },
  ];

  return rows.map((row) => {
    const percent = getProgressPercent(row.used, row.target);
    const remaining = getRemainingText(row.target, row.used, row.unit);
    const exceeded = getExceededValue(row.used, row.target);
    const hasTarget = toNumber(row.target) > 0;
    return {
      ...row,
      percent,
      visualPercent: getVisualProgressPercent(row.used, row.target),
      status: getProgressStatus(percent),
      remainingValue: getRemainingValue(row.target, row.used),
      exceeded,
      remaining,
      isOver: exceeded > 0,
      hasTarget,
    };
  });
}

export function generateModeAwareCoachSummary(goalMode, summary, targets) {
  const mode = getGoalModeConfig(goalMode);
  const caloriePercent = getProgressPercent(summary.calories, targets.calories);
  const calorieRemaining = getRemainingText(targets.calories, summary.calories, "千卡");
  const proteinPercent = getProgressPercent(summary.protein, targets.protein);

  if (calorieRemaining.isOver) {
    return {
      title: "今天熱量已超出目標",
      state: "需要平衡",
      tone: mode.tone,
      message:
        goalMode === "fitness_daily"
          ? `已超出 ${formatAmount(calorieRemaining.amount, "千卡")}。如果今天有訓練，可以把重點放在恢復與本週平均，不需要用懲罰式有氧處理。`
          : `已超出 ${formatAmount(calorieRemaining.amount, "千卡")}。下一餐建議清淡高蛋白，或安排低中強度活動協助平衡。`,
      caloriePercent,
      calorieRemaining,
      proteinPercent,
    };
  }

  if (proteinPercent < 40) {
    return {
      title: "蛋白質完成度偏低",
      state: "下一餐補蛋白",
      tone: mode.tone,
      message: `目前還能吃 ${formatAmount(calorieRemaining.amount, "千卡")}。下一餐優先選擇雞胸、蛋、豆腐或無糖豆漿，讓蛋白質進度拉上來。`,
      caloriePercent,
      calorieRemaining,
      proteinPercent,
    };
  }

  if (caloriePercent >= 85) {
    return {
      title: "接近今日熱量目標",
      state: "放慢加餐",
      tone: mode.tone,
      message: `今日熱量已達 ${caloriePercent}%。接下來選擇低油、低糖、高飽足的餐點，避免不小心超標。`,
      caloriePercent,
      calorieRemaining,
      proteinPercent,
    };
  }

  return {
    title: "今天狀態穩定",
    state: "可規劃下一餐",
    tone: mode.tone,
    message: `目前攝取 ${formatAmount(summary.calories, "千卡")}，還有 ${formatAmount(calorieRemaining.amount, "千卡")} 空間。依照「${mode.label}」模式，下一餐以 ${goalMode === "fat_loss" ? "高蛋白、低油" : "均衡蛋白質與主食"} 為主。`,
    caloriePercent,
    calorieRemaining,
    proteinPercent,
  };
}

export function generateModeAwareDailyMissions(goalMode, summary, targets) {
  const proteinGap = Math.max(toNumber(targets.protein) - toNumber(summary.protein), 0);
  const fatPercent = getProgressPercent(summary.fat, targets.fat);
  const caloriePercent = getProgressPercent(summary.calories, targets.calories);

  if (goalMode === "fat_loss") {
    return [
      `再補 ${formatAmount(proteinGap, "克")} 蛋白質，優先選低脂來源`,
      fatPercent >= 70 ? "下一餐避開炸物、高油醬料與奶茶" : "維持低油烹調，保留熱量赤字",
      caloriePercent >= 85 ? "今天停止加餐，改喝水或無糖茶" : "下一餐控制在低熱量密度餐點",
    ];
  }

  if (goalMode === "fitness_daily") {
    return [
      `今日蛋白質還差 ${formatAmount(proteinGap, "克")}`,
      "訓練後補 25-35g 蛋白質",
      "訓練前可補 40-60g 碳水，提升表現",
    ];
  }

  return [
    "保持三餐穩定，不需要過度限制",
    "晚餐後散步 20 分鐘，維持活動量",
    proteinGap > 20 ? "下一餐補一份蛋白質" : "下一餐維持均衡蛋白質與主食",
  ];
}

export function generateModeAwareTrainingAdvice(goalMode, summary, targets) {
  const caloriePercent = getProgressPercent(summary.calories, targets.calories);
  const extraCalories = Math.max(toNumber(summary.calories) - toNumber(targets.calories), 0);

  if (goalMode === "fat_loss") {
    return {
      title: "減脂訓練策略",
      body: "今天建議重訓 30-60 分鐘，搭配 20-30 分鐘低中強度有氧。避免只靠少吃製造赤字。",
      note: extraCalories > 0 ? "已超標時以低中強度活動平衡，不需要做懲罰式運動。" : "優先建立穩定赤字與高蛋白攝取。",
    };
  }

  if (goalMode === "fitness_daily") {
    return {
      title: "健人日常策略",
      body: "今天適合安排 45-70 分鐘重訓。訓練前可補 40-60g 碳水，訓練後補 25-35g 蛋白質。",
      note: caloriePercent > 100 ? "小幅超標先看本週平均，重點放在恢復與訓練表現。" : "訓練日前後碳水可以更有彈性。",
    };
  }

  return {
    title: "維持體態策略",
    body: "今天建議安排 20-30 分鐘快走或簡單活動，重點是穩定習慣，不需要過度訓練。",
    note: caloriePercent > 100 ? "超標時可以用散步或隔日微調平衡。" : "維持規律活動，讓飲食節奏穩定。",
  };
}

export function generateModeAwareMealSuggestion(goalMode, summary, targets) {
  const proteinPercent = getProgressPercent(summary.protein, targets.protein);
  const fatPercent = getProgressPercent(summary.fat, targets.fat);
  const caloriePercent = getProgressPercent(summary.calories, targets.calories);
  const carbsPercent = getProgressPercent(summary.carbs, targets.carbs);
  const overCalories = caloriePercent > 100;

  if (overCalories) {
    return {
      title: "下一餐清淡或停止加餐",
      direction: "高飽足、低熱量",
      recommended: ["清湯", "燙青菜", "豆腐湯", "無糖茶"],
      avoid: AVOID_FOODS.slice(0, 5),
      reason: "今天熱量已超標，下一餐建議清淡，或先停止加餐。",
    };
  }

  if (proteinPercent < 55 || goalMode === "fitness_daily") {
    return {
      title: "下一餐補高蛋白",
      direction: goalMode === "fat_loss" ? "高蛋白、低脂、500-700 kcal" : "高蛋白、搭配適量主食",
      recommended: HIGH_PROTEIN_FOODS.slice(0, 6),
      avoid: fatPercent > 80 ? AVOID_FOODS.slice(0, 5) : ["奶茶", "炸物", "高油醬料"],
      reason: "蛋白質完成度偏低，下一餐優先補蛋白質會比單純補熱量更有幫助。",
    };
  }

  if (fatPercent > 80) {
    return {
      title: "下一餐降低油脂",
      direction: "低脂、清淡、保留蛋白質",
      recommended: LOW_FAT_FOODS.slice(0, 6),
      avoid: AVOID_FOODS.slice(0, 6),
      reason: "脂肪已接近目標，下一餐避開炸物與高油醬料。",
    };
  }

  if (carbsPercent < 40 && caloriePercent < 85) {
    return {
      title: "下一餐可補適量主食",
      direction: "均衡碳水與蛋白質",
      recommended: [...CARB_FOODS.slice(0, 4), "茶葉蛋", "無糖豆漿"],
      avoid: ["奶茶", "甜點", "炸物"],
      reason: "碳水仍偏低且熱量空間足夠，可以補一份主食維持精神與訓練表現。",
    };
  }

  return {
    title: "下一餐維持均衡",
    direction: "蛋白質 + 主食 + 蔬菜",
    recommended: ["雞胸便當", "豆腐蛋花湯", "飯糰搭配無糖豆漿", "牛肉湯", "燙青菜"],
    avoid: ["奶茶", "鹽酥雞", "高油醬料"],
    reason: "目前進度穩定，下一餐維持均衡即可。",
  };
}

export function estimateExerciseMinutes(extraCalories, weightKg, met) {
  const calories = Math.max(toNumber(extraCalories), 0);
  const weight = toNumber(weightKg) > 0 ? toNumber(weightKg) : 70;
  const kcalPerMinute = (toNumber(met) * 3.5 * weight) / 200;
  return kcalPerMinute > 0 ? Math.ceil(calories / kcalPerMinute) : 0;
}

export function estimateCaloriesBurned(durationMinutes, weightKg, met) {
  const weight = toNumber(weightKg) > 0 ? toNumber(weightKg) : 70;
  return Math.round(((toNumber(met) * 3.5 * weight) / 200) * toNumber(durationMinutes));
}

export function getExerciseIntensityLabel(met) {
  if (met >= 8) return "高強度";
  if (met >= 6) return "中強度";
  return "低強度";
}

export function calculateExerciseCredit(burnedCalories, ratio = 0.5) {
  return Math.round(toNumber(burnedCalories) * ratio);
}

export function calculateNetCalories(todayCalories, burnedCalories) {
  return Math.max(0, Math.round(toNumber(todayCalories) - calculateExerciseCredit(burnedCalories)));
}

export function generateExerciseRecoveryPlan(goalMode, summary, targets, weightKg) {
  const calories = toNumber(summary.calories);
  const target = toNumber(targets.calories);
  const extraCalories = Math.max(calories - target, 0);
  const caloriePercent = getProgressPercent(calories, target);
  const shouldShow = extraCalories > 0 || caloriePercent >= 85;
  const effectiveWeight = toNumber(weightKg) > 0 ? toNumber(weightKg) : 70;

  return {
    shouldShow,
    extraCalories,
    caloriePercent,
    usesDefaultWeight: !(toNumber(weightKg) > 0),
    message:
      extraCalories > 0
        ? `今天已超出 ${formatAmount(extraCalories, "千卡")}，可以選擇輕量活動或明天小幅微調。`
        : "今天接近熱量目標，飯後安排輕量活動可以幫助維持節奏。",
    options: EXERCISE_OPTIONS.slice(0, goalMode === "fitness_daily" ? 4 : 3).map((option) => ({
      ...option,
      minutes: estimateExerciseMinutes(extraCalories || 120, effectiveWeight, option.met),
    })),
  };
}

export function generatePostLogImpact(entry, goalMode) {
  if (!entry) return null;
  const nutrition = normalizeNutrition(entry);
  return {
    foodName: entry.food_name || "最近一筆餐點",
    nutrition,
    message:
      goalMode === "fat_loss"
        ? "已更新今日進度。接下來優先高蛋白、低油餐點，維持熱量赤字。"
        : "已更新今日進度。下一餐可以依照目前缺口調整蛋白質與主食。",
  };
}

export function generateWeeklyCoachReview(entries, targets) {
  const byDate = new Map();
  entries.forEach((entry) => {
    const key = entry.date_key || "";
    if (!key) return;
    const bucket = byDate.get(key) || [];
    bucket.push(entry);
    byDate.set(key, bucket);
  });

  if (byDate.size < 3) {
    return {
      ready: false,
      message: "累積 3 天以上紀錄後，會產生本週飲食回顧。",
    };
  }

  const daySummaries = Array.from(byDate.values()).map((items) =>
    items.reduce(
      (summary, item) => {
        const nutrition = normalizeNutrition(item);
        summary.calories += nutrition.calories;
        summary.protein += nutrition.protein;
        summary.fat += nutrition.fat;
        return summary;
      },
      { calories: 0, protein: 0, fat: 0 }
    )
  );
  const averageCalories = Math.round(daySummaries.reduce((sum, day) => sum + day.calories, 0) / daySummaries.length);
  const proteinDays = daySummaries.filter((day) => day.protein >= toNumber(targets.protein)).length;
  const fatOverDays = daySummaries.filter((day) => day.fat > toNumber(targets.fat)).length;

  return {
    ready: true,
    averageCalories,
    proteinDays,
    fatOverDays,
    totalDays: daySummaries.length,
    message:
      proteinDays < Math.ceil(daySummaries.length / 2)
        ? "本週策略：早餐或下一餐先補蛋白質，晚餐減少油炸。"
        : "本週蛋白質節奏不錯，繼續維持穩定餐次與活動量。",
  };
}
