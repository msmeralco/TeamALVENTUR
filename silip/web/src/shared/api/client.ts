import createClient from "openapi-fetch";
import type { components, paths } from "./schema";

export type Schemas = components["schemas"];

/** How the client learns the current access token. The auth provider registers it. */
let getAccessToken: () => string | null = () => null;

/** Registers the token source; returns a function that removes it. */
export function setTokenSource(source: () => string | null): () => void {
  getAccessToken = source;
  return () => {
    if (getAccessToken === source) getAccessToken = () => null;
  };
}

/** Called when the API answers 401 to a request: the session ended. The auth provider registers it. */
let onSessionEnded: () => void = () => {};

export function setSessionEndedHandler(handler: () => void): () => void {
  onSessionEnded = handler;
  return () => {
    if (onSessionEnded === handler) onSessionEnded = () => {};
  };
}

/** How often open views refetch in the background (also on window focus). */
export const REFRESH_INTERVAL_MS = 5 * 60_000;

// Same origin: Vite proxies /api in dev, CloudFront routes /api to the API Lambda in AWS.
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: (request) => globalThis.fetch(request),
});

api.use({
  onRequest({ request }) {
    const token = getAccessToken();
    // Not Authorization: CloudFront replaces that header with its own SigV4 signature for the API Lambda.
    // The API reads this one (see CLIENT_AUTH_HEADER in api/src/silip/shared/auth/api.py).
    if (token !== null) request.headers.set("X-Silip-Authorization", `Bearer ${token}`);
    return request;
  },
  onResponse({ response }) {
    if (response.status === 401) onSessionEnded();
    return response;
  },
});

/** Thrown for any non-2xx answer, so TanStack Query shows the error state. */
export class ApiError extends Error {
  constructor(readonly status: number) {
    super(
      status === 401
        ? "Sign in required."
        : status === 403
          ? "No access."
          : status === 404
            ? "Not found."
            : status >= 500
              ? "The server had a problem. Try again in a moment."
              : `Request failed (${status}).`,
    );
  }
}

/** Unwraps an openapi-fetch result or throws `ApiError`. */
export function unwrap<T>(result: { data?: T; response: Response }): T {
  if (!result.response.ok || result.data === undefined) throw new ApiError(result.response.status);
  return result.data;
}

const NO_RETRY_STATUS = new Set([401, 403, 404]);

/** Retry once, but not for answers a retry cannot change (signed out, no access, not found). */
export function shouldRetry(failureCount: number, error: Error): boolean {
  if (error instanceof ApiError && NO_RETRY_STATUS.has(error.status)) return false;
  return failureCount < 1;
}
