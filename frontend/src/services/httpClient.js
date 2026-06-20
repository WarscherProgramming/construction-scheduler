const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

let accessToken = null;
let unauthorizedHandler = null;


export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}


export function configureAuthentication({ token, onUnauthorized }) {
  accessToken = token;
  unauthorizedHandler = onUnauthorized;
}


function getAuthHeaders() {
  return {
    "Content-Type": "application/json",
    ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
  };
}


async function parseResponseBody(response) {
  if (response.status === 204) return null;

  const text = await response.text();
  if (!text) return null;

  const contentType = response.headers.get("content-type") || "";

  if (contentType.includes("application/json")) {
    try {
      return JSON.parse(text);
    } catch {
      return text;
    }
  }

  return text;
}


function getErrorMessage(body, status) {
  if (typeof body?.detail === "string") {
    return body.detail;
  }

  if (Array.isArray(body?.detail)) {
    return body.detail
      .map((error) => error.msg)
      .filter(Boolean)
      .join(", ");
  }

  return `Request failed with status ${status}`;
}


async function fetchResponse(path, options) {
  try {
    return await fetch(`${API_URL}${path}`, options);
  } catch (error) {
    throw new ApiError("Unable to connect to the API", 0, error);
  }
}


async function handleErrorResponse(response) {
  const body = await parseResponseBody(response);

  if (response.status === 401) {
    unauthorizedHandler?.();
  }

  throw new ApiError(
    getErrorMessage(body, response.status),
    response.status,
    body
  );
}


export async function request(path, options = {}) {
  const response = await fetchResponse(path, options);
  const body = await parseResponseBody(response);

  if (!response.ok) {
    if (response.status === 401) {
      unauthorizedHandler?.();
    }

    throw new ApiError(
      getErrorMessage(body, response.status),
      response.status,
      body
    );
  }

  return body;
}


export function authenticatedRequest(path, options = {}) {
  return request(path, {
    ...options,
    headers: {
      ...getAuthHeaders(),
      ...options.headers,
    },
  });
}


export function jsonRequest(path, method, body) {
  return authenticatedRequest(path, {
    method,
    body: JSON.stringify(body),
  });
}


export async function downloadAuthenticatedFile(path) {
  const response = await fetchResponse(path, {
    headers: getAuthHeaders(),
  });

  if (!response.ok) {
    await handleErrorResponse(response);
  }

  return response.blob();
}
