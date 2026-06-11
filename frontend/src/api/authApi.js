const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

function buildAuthHeaders(token, extra = {}) {
  const headers = { ...extra };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function loginRequest(account, password) {
  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ account, password }),
  });

  return readJson(response);
}

export async function registerRequest(payload) {
  const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  return readJson(response);
}

export async function fetchCurrentUser(token) {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    headers: buildAuthHeaders(token),
  });

  return readJson(response);
}

export async function updateCurrentUser(token, payload) {
  const response = await fetch(`${API_BASE_URL}/api/auth/me`, {
    method: "PUT",
    headers: buildAuthHeaders(token, {
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  return readJson(response);
}
