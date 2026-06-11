const AUTH_SESSION_STORAGE_KEY = "ai_meal_scanner_auth_session";

function safeParse(value) {
  try {
    return JSON.parse(value);
  } catch {
    return null;
  }
}

export function loadStoredAuthSession() {
  const raw = localStorage.getItem(AUTH_SESSION_STORAGE_KEY);
  if (!raw) {
    return null;
  }

  const parsed = safeParse(raw);
  if (!parsed || typeof parsed !== "object") {
    return null;
  }

  const token = String(parsed.token || "").trim();
  const user = parsed.user && typeof parsed.user === "object" ? parsed.user : null;

  if (!token || !user) {
    return null;
  }

  return { token, user };
}

export function saveStoredAuthSession(session) {
  localStorage.setItem(AUTH_SESSION_STORAGE_KEY, JSON.stringify(session));
}

export function clearStoredAuthSession() {
  localStorage.removeItem(AUTH_SESSION_STORAGE_KEY);
}

export function getStoredAuthToken() {
  return loadStoredAuthSession()?.token || "";
}
