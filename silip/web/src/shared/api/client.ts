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

// Same origin: Vite proxies /api in dev, CloudFront routes /api to the API Lambda in AWS.
export const api = createClient<paths>({
  baseUrl: window.location.origin,
  fetch: (request) => globalThis.fetch(request),
});

api.use({
  onRequest({ request }) {
    const token = getAccessToken();
    if (token !== null) request.headers.set("Authorization", `Bearer ${token}`);
    return request;
  },
});

/** Thrown for any non-2xx answer, so TanStack Query shows the error state. */
export class ApiError extends Error {
  constructor(readonly status: number) {
    super(status === 401 ? "Sign in required" : status === 403 ? "No access" : `Request failed (${status})`);
  }
}

/** Unwraps an openapi-fetch result or throws `ApiError`. */
export function unwrap<T>(result: { data?: T; response: Response }): T {
  if (!result.response.ok || result.data === undefined) throw new ApiError(result.response.status);
  return result.data;
}
