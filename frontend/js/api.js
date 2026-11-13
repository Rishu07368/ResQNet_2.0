const API_ROOT = "/api";

export async function api(path, options = {}) {
  const response = await fetch(`${API_ROOT}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options.headers || {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(payload.message || `Request failed (${response.status})`);
    error.status = response.status;
    error.code = payload.code || "HTTP_ERROR";
    throw error;
  }
  return payload;
}

export function post(path, body) {
  return api(path, { method: "POST", body: JSON.stringify(body) });
}

export function patch(path, body) {
  return api(path, { method: "PATCH", body: JSON.stringify(body) });
}

export function put(path, body) {
  return api(path, { method: "PUT", body: JSON.stringify(body) });
}
