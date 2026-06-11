import { getStoredAuthToken } from "./authSession";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

function buildDateKey(value = new Date()) {
  const year = value.getFullYear();
  const month = String(value.getMonth() + 1).padStart(2, "0");
  const day = String(value.getDate()).padStart(2, "0");
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
  const response = await fetch(`${API_BASE_URL}/api/journal`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  const data = await readJson(response);
  return data.item;
}

export async function listTodayJournalEntries(_memberAccount) {
  const todayKey = buildDateKey(new Date());
  const response = await fetch(`${API_BASE_URL}/api/journal?date_key=${encodeURIComponent(todayKey)}`, {
    headers: buildAuthHeaders(),
  });
  const data = await readJson(response);
  return data.items || [];
}

export async function listMemberJournalEntries(_memberAccount) {
  const response = await fetch(`${API_BASE_URL}/api/journal`, {
    headers: buildAuthHeaders(),
  });
  const data = await readJson(response);
  return data.items || [];
}

export function summarizeJournalEntries(entries) {
  return entries.reduce(
    (summary, entry) => {
      summary.count += 1;
      summary.calories += Number(entry.nutrition?.calories || 0);
      summary.protein += Number(entry.nutrition?.protein || 0);
      summary.fat += Number(entry.nutrition?.fat || 0);
      summary.carbs += Number(entry.nutrition?.carbs || 0);
      return summary;
    },
    { count: 0, calories: 0, protein: 0, fat: 0, carbs: 0 }
  );
}

export function summarizeTodayJournal(entries) {
  return summarizeJournalEntries(entries);
}

export async function removeJournalEntry(_memberAccount, entryId) {
  const response = await fetch(`${API_BASE_URL}/api/journal/${encodeURIComponent(entryId)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });
  await readJson(response);
}

export async function updateJournalEntry(_memberAccount, entryId, patch = {}) {
  const response = await fetch(`${API_BASE_URL}/api/journal/${encodeURIComponent(entryId)}`, {
    method: "PUT",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(patch),
  });
  const data = await readJson(response);
  return data.item;
}
