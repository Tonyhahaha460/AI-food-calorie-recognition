import { getStoredAuthToken } from "./authSession.js";

const API_BASE_URL = import.meta.env?.VITE_API_BASE_URL || "http://localhost:5000";

const NUTRITION_KEY_ALIASES = {
  calories: ["calories", "calorie", "kcal", "heat", "熱量", "total_calories"],
  protein: ["protein", "protein_g", "proteins", "蛋白質"],
  fat: ["fat", "fat_g", "fats", "脂肪"],
  carbs: ["carbs", "carb", "carbs_g", "carbohydrate", "carbohydrates", "carbohydrate_g", "碳水", "碳水化合物"],
};

function toNumber(value) {
  if (typeof value === "string") {
    const match = value.replaceAll(",", "").match(/-?\d+(\.\d+)?/);
    if (match) {
      const parsed = Number(match[0]);
      return Number.isFinite(parsed) ? parsed : 0;
    }
  }

  const numeric = Number(value);
  return Number.isFinite(numeric) ? numeric : 0;
}

function pickNutritionValue(field, ...sources) {
  const aliases = NUTRITION_KEY_ALIASES[field] || [field];
  for (const source of sources) {
    if (!source || typeof source !== "object") {
      continue;
    }

    for (const alias of aliases) {
      if (source[alias] !== undefined && source[alias] !== null && source[alias] !== "") {
        return toNumber(source[alias]);
      }
    }

    const lowerCaseMatch = Object.keys(source).find((key) => aliases.includes(String(key).trim().toLowerCase()));
    if (lowerCaseMatch && source[lowerCaseMatch] !== undefined && source[lowerCaseMatch] !== null && source[lowerCaseMatch] !== "") {
      return toNumber(source[lowerCaseMatch]);
    }
  }

  return 0;
}

function hasNutritionFields(source = {}) {
  if (!source || typeof source !== "object") {
    return false;
  }

  if (source.nutrition || source.total_nutrition) {
    return true;
  }

  const aliases = Object.values(NUTRITION_KEY_ALIASES).flat();
  return Object.keys(source).some((key) => aliases.includes(String(key).trim().toLowerCase()));
}

export function normalizeNutrition(entryOrNutrition = {}) {
  const entry = entryOrNutrition && typeof entryOrNutrition === "object" ? entryOrNutrition : {};
  const nutrition = entry.nutrition && typeof entry.nutrition === "object" ? entry.nutrition : entry;
  const totalNutrition =
    entry.total_nutrition && typeof entry.total_nutrition === "object" ? entry.total_nutrition : undefined;

  return {
    calories: pickNutritionValue("calories", nutrition, totalNutrition, entry),
    protein: pickNutritionValue("protein", nutrition, totalNutrition, entry),
    fat: pickNutritionValue("fat", nutrition, totalNutrition, entry),
    carbs: pickNutritionValue("carbs", nutrition, totalNutrition, entry),
  };
}

export function normalizeJournalEntry(entry = {}) {
  const source = entry && typeof entry === "object" ? entry : {};
  const normalized = {
    ...source,
    nutrition: normalizeNutrition(source),
  };

  if (!normalized.date_key && normalized.created_at) {
    normalized.date_key = buildDateKey(new Date(normalized.created_at));
  }

  return normalized;
}

function normalizeJournalEntries(entries) {
  return Array.isArray(entries) ? entries.map(normalizeJournalEntry) : [];
}

function buildDateKey(value = new Date()) {
  const date = value instanceof Date && !Number.isNaN(value.getTime()) ? value : new Date();
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

function buildAuthHeaders(extra = {}) {
  const token = getStoredAuthToken();
  const headers = { ...extra };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

export async function addJournalEntry(_memberAccount, payload) {
  const normalizedPayload = normalizeJournalEntry(payload);
  const response = await fetch(`${API_BASE_URL}/api/journal`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(normalizedPayload),
  });

  const data = await readJson(response);
  return normalizeJournalEntry(data.item);
}

export async function listTodayJournalEntries(_memberAccount) {
  const todayKey = buildDateKey(new Date());
  const response = await fetch(`${API_BASE_URL}/api/journal?date_key=${encodeURIComponent(todayKey)}`, {
    headers: buildAuthHeaders(),
  });
  const data = await readJson(response);
  return normalizeJournalEntries(data.items);
}

export async function listMemberJournalEntries(_memberAccount) {
  const response = await fetch(`${API_BASE_URL}/api/journal`, {
    headers: buildAuthHeaders(),
  });
  const data = await readJson(response);
  return normalizeJournalEntries(data.items);
}

export function calculateDailyNutrition(entries) {
  return normalizeJournalEntries(entries).reduce(
    (summary, entry) => {
      const nutrition = normalizeNutrition(entry);
      summary.count += 1;
      summary.calories += nutrition.calories;
      summary.protein += nutrition.protein;
      summary.fat += nutrition.fat;
      summary.carbs += nutrition.carbs;
      return summary;
    },
    { count: 0, calories: 0, protein: 0, fat: 0, carbs: 0 }
  );
}

export function summarizeJournalEntries(entries) {
  return calculateDailyNutrition(entries);
}

export function summarizeTodayJournal(entries) {
  return calculateDailyNutrition(entries);
}

export async function removeJournalEntry(_memberAccount, entryId) {
  const response = await fetch(`${API_BASE_URL}/api/journal/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });
  await readJson(response);
}

export async function updateJournalEntry(_memberAccount, entryId, patch = {}) {
  const normalizedPatch = hasNutritionFields(patch) ? { ...patch, nutrition: normalizeNutrition(patch) } : patch;
  const response = await fetch(`${API_BASE_URL}/api/journal/${encodeURIComponent(entryId)}`, {
    method: "PUT",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(normalizedPatch),
  });
  const data = await readJson(response);
  return normalizeJournalEntry(data.item);
}
