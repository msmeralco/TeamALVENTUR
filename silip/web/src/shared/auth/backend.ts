import { UserManager, WebStorageStateStore, type User } from "oidc-client-ts";

export type Group = "engineers" | "households";

export interface AuthUser {
  username: string;
  groups: string[];
  /** Sent as a bearer token; null in dev mode (the API runs with AUTH_DISABLED=true). */
  accessToken: string | null;
}

/** The sign-in mechanism behind AuthProvider: Cognito when deployed, a fake user in dev. */
export interface AuthBackend {
  load(): Promise<AuthUser | null>;
  signIn(): Promise<AuthUser | null>;
  completeSignIn(url: string): Promise<AuthUser>;
  signOut(): Promise<void>;
}

export const devUser: AuthUser = { username: "dev", groups: ["engineers", "households"], accessToken: null };

export function createDevBackend(): AuthBackend {
  let signedIn = true;
  return {
    load: async () => (signedIn ? devUser : null),
    signIn: async () => {
      signedIn = true;
      return devUser;
    },
    completeSignIn: async () => devUser,
    signOut: async () => {
      signedIn = false;
    },
  };
}

function toAuthUser(user: User): AuthUser {
  const groups = user.profile["cognito:groups"];
  return {
    username: String(user.profile["cognito:username"] ?? user.profile.sub),
    groups: Array.isArray(groups) ? groups.filter((g): g is string => typeof g === "string") : [],
    accessToken: user.access_token,
  };
}

/** Authorization code + PKCE through Cognito managed login. Sessions live in sessionStorage. */
export function createCognitoBackend(authority: string, clientId: string, domain: string): AuthBackend {
  const origin = window.location.origin;
  const manager = new UserManager({
    authority,
    client_id: clientId,
    redirect_uri: `${origin}/auth/callback`,
    post_logout_redirect_uri: `${origin}/`,
    response_type: "code",
    scope: "openid email profile",
    userStore: new WebStorageStateStore({ store: window.sessionStorage }),
  });
  return {
    load: async () => {
      const user = await manager.getUser();
      return user === null || user.expired ? null : toAuthUser(user);
    },
    signIn: async () => {
      await manager.signinRedirect();
      return null;
    },
    completeSignIn: async (url) => toAuthUser(await manager.signinRedirectCallback(url)),
    signOut: async () => {
      await manager.removeUser();
      // Cognito has no standard end_session endpoint; its logout takes client_id + logout_uri.
      const params = new URLSearchParams({ client_id: clientId, logout_uri: `${origin}/` });
      window.location.assign(`${domain.replace(/\/+$/, "")}/logout?${params.toString()}`);
    },
  };
}

export function backendFromEnv(): AuthBackend {
  const env = import.meta.env;
  if (
    env.VITE_AUTH_MODE === "cognito" &&
    env.VITE_COGNITO_AUTHORITY &&
    env.VITE_COGNITO_CLIENT_ID &&
    env.VITE_COGNITO_DOMAIN
  ) {
    return createCognitoBackend(env.VITE_COGNITO_AUTHORITY, env.VITE_COGNITO_CLIENT_ID, env.VITE_COGNITO_DOMAIN);
  }
  return createDevBackend();
}
