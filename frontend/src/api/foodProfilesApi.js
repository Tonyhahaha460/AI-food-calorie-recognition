import { getStoredAuthToken } from "../utils/authSession";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

export { API_BASE_URL };

async function readJson(response) {
  const data = await response.json();

  if (!response.ok) {
    throw new Error(data.error || "Request failed.");
  }

  return data;
}

function buildAuthHeaders(extra = {}) {
  const token = getStoredAuthToken();
  const headers = { ...extra };
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

export async function fetchFoodProfiles() {
  const response = await fetch(`${API_BASE_URL}/api/food-profiles`, {
    headers: buildAuthHeaders(),
  });
  const data = await readJson(response);
  return data.items || [];
}

export async function createFoodProfile(payload) {
  const response = await fetch(`${API_BASE_URL}/api/food-profiles`, {
    method: "POST",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  return readJson(response);
}

export async function updateFoodProfile(label, payload) {
  const response = await fetch(`${API_BASE_URL}/api/food-profiles/${encodeURIComponent(label)}`, {
    method: "PUT",
    headers: buildAuthHeaders({
      "Content-Type": "application/json",
    }),
    body: JSON.stringify(payload),
  });

  return readJson(response);
}

export async function deleteFoodProfile(label) {
  const response = await fetch(`${API_BASE_URL}/api/food-profiles/${encodeURIComponent(label)}`, {
    method: "DELETE",
    headers: buildAuthHeaders(),
  });

  return readJson(response);
}

export async function uploadTrainingImages(label, files) {
  const formData = new FormData();
  Array.from(files).forEach((file) => {
    formData.append("images", file);
  });

  const response = await fetch(
    `${API_BASE_URL}/api/food-profiles/${encodeURIComponent(label)}/images`,
    {
      method: "POST",
      headers: buildAuthHeaders(),
      body: formData,
    }
  );

  return readJson(response);
}

export async function uploadTrainingFeedback({ label, foodName, image }) {
  const formData = new FormData();
  formData.append("label", label || "");
  formData.append("food_name", foodName || "");
  formData.append("image", image);

  const response = await fetch(`${API_BASE_URL}/api/training-feedback`, {
    method: "POST",
    headers: buildAuthHeaders(),
    body: formData,
  });

  return readJson(response);
}

export async function fetchTrainingImages(label) {
  const response = await fetch(
    `${API_BASE_URL}/api/food-profiles/${encodeURIComponent(label)}/images`,
    {
      headers: buildAuthHeaders(),
    }
  );

  return readJson(response);
}

export async function deleteTrainingImage(label, filename) {
  const response = await fetch(
    `${API_BASE_URL}/api/food-profiles/${encodeURIComponent(label)}/images/${encodeURIComponent(filename)}`,
    {
      method: "DELETE",
      headers: buildAuthHeaders(),
    }
  );

  return readJson(response);
}

export async function fetchTrainingStatus() {
  const response = await fetch(`${API_BASE_URL}/api/train/status`, {
    headers: buildAuthHeaders(),
  });
  return readJson(response);
}

export async function trainModel() {
  const response = await fetch(`${API_BASE_URL}/api/train`, {
    method: "POST",
    headers: buildAuthHeaders(),
  });
  return readJson(response);
}
