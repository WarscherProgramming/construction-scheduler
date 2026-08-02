const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const AUTH_REQUEST_TIMEOUT_MS = Number(
  import.meta.env.VITE_AUTH_REQUEST_TIMEOUT_MS || 10_000
);

if (
  !Number.isInteger(AUTH_REQUEST_TIMEOUT_MS) ||
  AUTH_REQUEST_TIMEOUT_MS < 1_000 ||
  AUTH_REQUEST_TIMEOUT_MS > 60_000
) {
  throw new Error(
    "VITE_AUTH_REQUEST_TIMEOUT_MS must be an integer from 1000 to 60000"
  );
}

let accessToken = null;
let unauthorizedHandler = null;
let refreshPromise = null;
let authGeneration = 0;
let sessionInvalidated = false;


export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}


export function configureAuthentication({ token, onUnauthorized }) {
  if (token !== undefined) {
    accessToken = token;
    if (token) sessionInvalidated = false;
  }
  unauthorizedHandler = onUnauthorized;
}


export function adoptAuthentication(data) {
  if (!data || typeof data.access_token !== "string" || !data.access_token) {
    throw new ApiError("The authentication response was invalid", 401, data);
  }
  accessToken = data.access_token;
  sessionInvalidated = false;
  return data;
}


export function clearAuthentication() {
  authGeneration += 1;
  accessToken = null;
}


function invalidateAuthentication() {
  clearAuthentication();
  if (sessionInvalidated) return;
  sessionInvalidated = true;
  unauthorizedHandler?.();
}


function getAuthHeaders({ includeContentType = true, token = accessToken } = {}) {
  return {
    ...(includeContentType ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
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
  if (typeof body?.detail === "string") return body.detail;
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
    if (error?.name === "AbortError") throw error;
    throw new ApiError("Unable to connect to the API", 0, error);
  }
}


async function responseError(response) {
  const body = await parseResponseBody(response);
  return new ApiError(
    getErrorMessage(body, response.status),
    response.status,
    body
  );
}


async function authRequest(path, options = {}) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(
    () => controller.abort(),
    AUTH_REQUEST_TIMEOUT_MS
  );
  let response;
  try {
    response = await fetchResponse(path, {
      ...options,
      credentials: "include",
      signal: controller.signal,
    });
  } catch (error) {
    if (controller.signal.aborted && error?.name === "AbortError") {
      throw new ApiError("Authentication request timed out", 0);
    }
    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
  const body = await parseResponseBody(response);
  if (!response.ok) {
    throw new ApiError(
      getErrorMessage(body, response.status),
      response.status,
      body
    );
  }
  return body;
}


export function authenticationRequest(path, options = {}) {
  return authRequest(path, options);
}


async function performRefresh() {
  const generation = authGeneration;
  const csrf = await authRequest("/auth/csrf");
  if (typeof csrf?.csrf_token !== "string" || !csrf.csrf_token) {
    throw new ApiError("The authentication response was invalid", 0, csrf);
  }

  const data = await authRequest("/auth/refresh", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf.csrf_token },
  });
  if (generation !== authGeneration) {
    throw new ApiError("Authentication changed while refreshing", 0);
  }
  return adoptAuthentication(data);
}


function withCrossTabRefreshLock(callback) {
  if (typeof navigator !== "undefined" && navigator.locks?.request) {
    return navigator.locks.request("fieldflow-auth-refresh", callback);
  }
  return callback();
}


export function refreshAuthentication({ notify = true } = {}) {
  if (refreshPromise) return refreshPromise;

  const current = Promise.resolve()
    .then(() => withCrossTabRefreshLock(performRefresh))
    .catch((error) => {
      if (error instanceof ApiError && [401, 403].includes(error.status)) {
        if (notify) {
          invalidateAuthentication();
        } else {
          clearAuthentication();
        }
      }
      throw error;
    })
    .finally(() => {
      if (refreshPromise === current) refreshPromise = null;
    });
  refreshPromise = current;
  return current;
}


export function restoreAuthentication() {
  return refreshAuthentication({ notify: false });
}


export async function prepareForLogin() {
  clearAuthentication();
  if (refreshPromise) {
    try {
      await refreshPromise;
    } catch {
      // A stale refresh cannot prevent an explicit login.
    }
  }
}


export async function logoutAuthentication() {
  clearAuthentication();
  if (refreshPromise) {
    try {
      await refreshPromise;
    } catch {
      // Logout still clears browser cookies after a failed refresh.
    }
  }

  const csrf = await authRequest("/auth/csrf");
  return authRequest("/auth/logout", {
    method: "POST",
    headers: { "X-CSRF-Token": csrf.csrf_token },
  });
}


export async function request(path, options = {}) {
  const response = await fetchResponse(path, options);
  const body = await parseResponseBody(response);
  if (!response.ok) {
    throw new ApiError(
      getErrorMessage(body, response.status),
      response.status,
      body
    );
  }
  return body;
}


async function authenticatedResponse(path, options = {}, retried = false) {
  const isMultipart =
    typeof FormData !== "undefined" && options.body instanceof FormData;
  const requestToken = accessToken;
  const response = await fetchResponse(path, {
    ...options,
    headers: {
      ...getAuthHeaders({
        includeContentType: !isMultipart,
        token: requestToken,
      }),
      ...options.headers,
    },
  });

  if (response.status !== 401 || retried) {
    if (response.status === 401 && retried) {
      invalidateAuthentication();
    }
    return response;
  }

  if (accessToken && accessToken !== requestToken) {
    return authenticatedResponse(path, options, true);
  }

  await refreshAuthentication();
  if (options.signal?.aborted) {
    throw new DOMException("The operation was aborted", "AbortError");
  }
  return authenticatedResponse(path, options, true);
}


export async function authenticatedRequest(path, options = {}) {
  const response = await authenticatedResponse(path, options);
  if (!response.ok) throw await responseError(response);
  return parseResponseBody(response);
}


export function jsonRequest(path, method, body, options = {}) {
  return authenticatedRequest(path, {
    ...options,
    method,
    body: JSON.stringify(body),
  });
}


export async function downloadAuthenticatedResponse(path, options = {}) {
  const response = await authenticatedResponse(path, options);
  if (!response.ok) throw await responseError(response);
  return {
    blob: await response.blob(),
    headers: response.headers,
  };
}


export async function downloadAuthenticatedFile(path, options = {}) {
  const { blob } = await downloadAuthenticatedResponse(path, options);
  return blob;
}
