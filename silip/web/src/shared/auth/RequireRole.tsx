import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { StateCard } from "../ui";
import { Button } from "../ui/components/button";
import type { Group } from "./backend";
import { useAuth } from "./AuthProvider";

const GROUP_LABEL: Record<Group, string> = { engineers: "an engineer account", households: "a household account" };
const GROUP_PURPOSE: Record<Group, string> = {
  engineers: "The risk map is for Meralco engineers.",
  households: "Usage is shown only to the household that owns the clamp.",
};

/** Shows children only to signed-in users in `role`; otherwise a sign-in prompt or a plain refusal. */
export function RequireRole({ role, children }: { role: Group; children: ReactNode }) {
  const { status, user, sessionEnded, hasGroup, signIn } = useAuth();
  if (status === "loading") {
    return <p className="mt-10 text-center text-sm text-muted-foreground">Checking sign-in…</p>;
  }
  if (user === null && sessionEnded) {
    return (
      <StateCard title="Your session ended">
        <p className="text-sm text-muted-foreground">Sign in again to continue where you were.</p>
        <Button className="mt-2 min-h-11 rounded-full" onClick={() => void signIn()}>
          Sign in
        </Button>
      </StateCard>
    );
  }
  if (user === null) {
    return (
      <StateCard title="Sign in to continue">
        <p className="text-sm text-muted-foreground">
          {GROUP_PURPOSE[role]} Accounts are by invitation only, so there is no sign-up.
        </p>
        <Button className="mt-2 min-h-11 rounded-full" onClick={() => void signIn()}>
          Sign in
        </Button>
        <Link
          to="/"
          className="inline-flex min-h-11 items-center text-sm text-muted-foreground underline-offset-4 hover:underline"
        >
          Or see current outages
        </Link>
      </StateCard>
    );
  }
  if (!hasGroup(role)) {
    return (
      <StateCard title="Not available for this account">
        <p className="text-sm text-muted-foreground">
          You are signed in, but this is not {GROUP_LABEL[role]}. {GROUP_PURPOSE[role]}
        </p>
        <Button asChild variant="outline" className="mt-2 min-h-11 rounded-full">
          <Link to="/">See current outages</Link>
        </Button>
      </StateCard>
    );
  }
  return <>{children}</>;
}
