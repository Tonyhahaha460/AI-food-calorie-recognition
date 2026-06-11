import { getStoredAuthToken } from "../utils/authSession";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

function buildAuthHeaders() {
  const token = getStoredAuthToken();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function readJson(response) {
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }
  return data;
}

export async function predictMeal(file) {
  const formData = new FormData();
  formData.append("image", file);

  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: formData,
  });

  return readJson(response);
}

export async function fetchHistory(options = {}) {
  const params = new URLSearchParams();

  if (options.memberAccount) {
    params.set("member_account", options.memberAccount);
  }

  if (options.includeAll) {
    params.set("include_all", "1");
  }

  const query = params.toString();
  const response = await fetch(`${API_BASE_URL}/history${query ? `?${query}` : ""}`, {
    headers: buildAuthHeaders(),
  });
  const data = await readJson(response);
  return data.items || [];
}
