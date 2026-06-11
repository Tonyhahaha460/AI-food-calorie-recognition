export const ACTIVITY_LEVEL_OPTIONS = [
  { value: "sedentary", label: "久坐 / 幾乎不運動", multiplier: 1.2 },
  { value: "light", label: "輕度活動 / 每週 1-3 天", multiplier: 1.375 },
  { value: "moderate", label: "中度活動 / 每週 3-5 天", multiplier: 1.55 },
  { value: "active", label: "高度活動 / 每週 6-7 天", multiplier: 1.725 },
  { value: "very_active", label: "非常活躍 / 高強度勞動", multiplier: 1.9 },
];

export function calculateBmr({ gender, weightKg, heightCm, age }) {
  const weight = Number(weightKg || 0);
  const height = Number(heightCm || 0);
  const ageValue = Number(age || 0);

  if (!weight || !height || !ageValue) {
    return 0;
  }

  const base = 10 * weight + 6.25 * height - 5 * ageValue;
  return Math.round(base + (gender === "female" ? -161 : 5));
}

export function getActivityOption(value) {
  return ACTIVITY_LEVEL_OPTIONS.find((option) => option.value === value) || ACTIVITY_LEVEL_OPTIONS[0];
}

export function calculateTdee(profile) {
  const bmr = calculateBmr(profile);
  if (!bmr) {
    return 0;
  }

  const activity = getActivityOption(profile.activityLevel);
  return Math.round(bmr * activity.multiplier);
}

export function calculateFatLossTarget(profile) {
  const tdee = calculateTdee(profile);
  if (!tdee) {
    return 0;
  }

  return Math.max(calculateBmr(profile), tdee - 300);
}
