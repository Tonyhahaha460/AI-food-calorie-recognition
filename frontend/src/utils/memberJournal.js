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

export function getLocalDateTimeInputValue(date = new Date()) {
  const value = date instanceof Date && !Number.isNaN(date.getTime()) ? date : new Date();
  const pad = (part) => String(part).padStart(2, "0");
  return `${value.getFullYear()}-${pad(value.getMonth() + 1)}-${pad(value.getDate())}T${pad(value.getHours())}:${pad(
    value.getMinutes()
  )}`;
}

export function getEntryLocalDate(entry = {}) {
  const raw =
    entry.localDateTime ||
    entry.local_date_time ||
    entry.recordedDateTime ||
    entry.recorded_date_time ||
    entry.date ||
    entry.local_date ||
    entry.date_key ||
    entry.createdAt ||
    entry.created_at ||
    entry.recordedAt ||
    entry.recorded_at ||
    entry.recordDate;

  if (!raw) {
    return "";
  }

  const text = String(raw).trim();
  if (!text) {
    return "";
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) {
    return text;
  }

  if (text.includes("T") && !/[zZ]|[+-]\d{2}:?\d{2}$/.test(text)) {
    return text.slice(0, 10);
  }

  const date = new Date(text);
  if (Number.isNaN(date.getTime())) {
    return text.slice(0, 10);
  }

  return buildDateKey(date);
}

export function getEntryDateTimeInputValue(entry = {}) {
  const localValue =
    entry.localDateTime || entry.local_date_time || entry.recordedDateTime || entry.recorded_date_time || "";
  if (localValue && String(localValue).includes("T")) {
    return String(localValue).slice(0, 16);
  }

  const raw = entry.createdAt || entry.created_at || entry.recordedAt || entry.recorded_at || entry.date || entry.date_key;
  if (!raw) {
    return getLocalDateTimeInputValue();
  }

  if (/^\d{4}-\d{2}-\d{2}$/.test(String(raw).trim())) {
    return `${String(raw).trim()}T00:00`;
  }

  const parsed = new Date(raw);
  if (Number.isNaN(parsed.getTime())) {
    const fallbackDate = getEntryLocalDate(entry);
    return fallbackDate ? `${fallbackDate}T00:00` : getLocalDateTimeInputValue();
  }

  return getLocalDateTimeInputValue(parsed);
}

export function buildJournalDateTimePayload(localDateTime = getLocalDateTimeInputValue()) {
  const value = String(localDateTime || "").trim() || getLocalDateTimeInputValue();
  const date = value.slice(0, 10);
  const parsed = new Date(value);
  const createdAt = Number.isNaN(parsed.getTime()) ? new Date().toISOString() : parsed.toISOString();

  return {
    localDateTime: value,
    local_date_time: value,
    date,
    local_date: date,
    date_key: date,
    createdAt,
    created_at: createdAt,
    recordedAt: createdAt,
    recorded_at: createdAt,
  };
}

export function normalizeJournalEntry(entry = {}) {
  const source = entry && typeof entry === "object" ? entry : {};
  const dateKey = getEntryLocalDate(source) || buildDateKey(new Date());
  const localDateTime =
    source.localDateTime ||
    source.local_date_time ||
    source.recordedDateTime ||
    source.recorded_date_time ||
    getEntryDateTimeInputValue(source);
  const normalized = {
    ...source,
    created_at: source.created_at || source.createdAt || source.recorded_at || source.recordedAt,
    createdAt: source.createdAt || source.created_at || source.recordedAt || source.recorded_at,
    localDateTime,
    local_date_time: localDateTime,
    date: source.date || source.local_date || dateKey,
    local_date: source.local_date || source.date || dateKey,
    date_key: dateKey,
    nutrition: normalizeNutrition(source),
  };

  if (!normalized.created_at && localDateTime) {
    normalized.created_at = buildJournalDateTimePayload(localDateTime).created_at;
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
