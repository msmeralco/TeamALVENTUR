import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { StateCard } from "../ui";
import { Button } from "../ui/components/button";
import { useDocumentTitle } from "../ui/feedback";
import type { Group } from "./backend";
import { useAuth } from "./AuthProvider";

const GROUP_LABEL: Record<Group, string> = { engineers: "an engineer account", households: "a household account" };
const GROUP_PURPOSE: Record<Group, string> = {
  engineers: "The risk map is for Meralco engineers.",
  households: "Usage is shown only to the household that owns the clamp.",
};

function SignInCard({ role, sessionEnded }: { role: Group; sessionEnded: boolean }) {
  const { signIn } = useAuth();
  useDocumentTitle("Sign in");
  return (
    <StateCard
      title={sessionEnded ? "Your session ended" : "Sign in to continue"}
      actions={
        <>
          <Button className="min-h-11 rounded-full" onClick={() => void signIn()}>
            Sign in
          </Button>
          <Button asChild variant="outline" className="min-h-11 rounded-full">
            <Link to="/outages">See current outages</Link>
          </Button>
        </>
      }
    >
      <p className="text-sm text-muted-foreground">
        {sessionEnded
          ? "Sign in again to continue where you were."
          : `${GROUP_PURPOSE[role]} Accounts are by invitation only, so there is no sign-up.`}
      </p>
    </StateCard>
  );
}

function NoAccessCard({ role }: { role: Group }) {
  useDocumentTitle("No access");
  return (
    <StateCard
      title="Not available for this account"
      actions={
        <Button asChild className="min-h-11 rounded-full">
          <Link to="/outages">See current outages</Link>
        </Button>
      }
    >
      <p className="text-sm text-muted-foreground">
        You are signed in, but this is not {GROUP_LABEL[role]}. {GROUP_PURPOSE[role]}
      </p>
    </StateCard>
  );
}

/** Shows children only to signed-in users in `role`; otherwise a sign-in prompt or a plain refusal. */
export function RequireRole({ role, children }: { role: Group; children: ReactNode }) {
  const { status, user, sessionEnded, hasGroup } = useAuth();
  if (status === "loading") {
    return <p className="mt-10 text-center text-sm text-muted-foreground">Checking sign-in…</p>;
  }
  if (user === null) return <SignInCard role={role} sessionEnded={sessionEnded} />;
  if (!hasGroup(role)) return <NoAccessCard role={role} />;
  return <>{children}</>;
}
