import type { ReactNode } from "react";
import type { Group } from "./backend";
import { useAuth } from "./AuthProvider";

const GROUP_LABEL: Record<Group, string> = { engineers: "an engineer", households: "a household" };

/** Shows children only to signed-in users in `role`; otherwise a sign-in prompt or a plain refusal. */
export function RequireRole({ role, children }: { role: Group; children: ReactNode }) {
  const { status, user, hasGroup, signIn } = useAuth();
  if (status === "loading") return <p className="muted">Checking sign-in…</p>;
  if (user === null) {
    return (
      <section>
        <h2>Sign in required</h2>
        <p className="muted">This view is for {GROUP_LABEL[role]} account. Accounts are by invitation.</p>
        <button onClick={() => void signIn()}>Sign in</button>
      </section>
    );
  }
  if (!hasGroup(role)) {
    return <p>Your account is not {GROUP_LABEL[role]} account, so this view is not available.</p>;
  }
  return <>{children}</>;
}
