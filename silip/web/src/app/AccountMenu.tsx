import { ChevronDown, Loader2 } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { useAuth } from "../shared/auth";
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../shared/ui/components/alert-dialog";
import { Button } from "../shared/ui/components/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../shared/ui/components/dropdown-menu";
import { useTheme, type ThemeChoice } from "../shared/ui/theme";
import { ThemeToggle } from "../shared/ui/ThemeToggle";

const GROUP_NAME: Record<string, string> = { engineers: "Engineer", households: "Household" };
const THEMES: { value: ThemeChoice; label: string }[] = [
  { value: "light", label: "Light" },
  { value: "dark", label: "Dark" },
  { value: "system", label: "System" },
];

function groupLabel(groups: string[]): string {
  const names = groups.map((g) => GROUP_NAME[g]).filter((n): n is string => n !== undefined);
  const [first, ...rest] = names;
  if (first === undefined) return "No group";
  return `${[first, ...rest.map((n) => n.toLowerCase())].join(" and ")} account`;
}

/** Confirms sign-out, the one costly action in the app (signing in again needs the invitation account). */
function SignOutDialog({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }) {
  const { signOut } = useAuth();
  const navigate = useNavigate();
  const [pending, setPending] = useState(false);

  const confirm = async () => {
    setPending(true);
    try {
      await signOut();
      onOpenChange(false);
      navigate("/");
      toast.success("Signed out");
    } finally {
      setPending(false);
    }
  };

  return (
    <AlertDialog open={open} onOpenChange={(next) => !pending && onOpenChange(next)}>
      <AlertDialogContent size="sm" onOverlayClick={() => !pending && onOpenChange(false)}>
        <AlertDialogHeader>
          <AlertDialogTitle className="font-display text-xl">Sign out?</AlertDialogTitle>
          <AlertDialogDescription>You will need your invitation account to sign in again.</AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          {/* Radix focuses Cancel first, so Enter or Escape keeps the session. */}
          <AlertDialogCancel className="min-h-11 rounded-full" disabled={pending}>
            Cancel
          </AlertDialogCancel>
          <Button className="min-h-11 rounded-full" disabled={pending} onClick={() => void confirm()}>
            {pending && <Loader2 aria-hidden="true" className="animate-spin" />}
            {pending ? "Signing out…" : "Sign out"}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}

/** Signed in: name, group, theme and sign-out behind the username. Signed out: a theme toggle and Sign in. */
export function AccountMenu() {
  const { user, signIn } = useAuth();
  const { choice, setChoice } = useTheme();
  const [confirming, setConfirming] = useState(false);

  if (user === null) {
    return (
      <>
        <ThemeToggle />
        <Button variant="outline" className="min-h-11 rounded-full sm:min-h-9 pointer-coarse:min-h-11" onClick={() => void signIn()}>
          Sign in
        </Button>
      </>
    );
  }
  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            className="min-h-11 max-w-48 rounded-full sm:min-h-9"
            aria-label={`Account: ${user.username}`}
          >
            <span className="truncate">{user.username}</span>
            <ChevronDown aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel className="grid font-normal">
            <span className="truncate font-semibold">{user.username}</span>
            <span className="text-sm text-muted-foreground">{groupLabel(user.groups)}</span>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuLabel className="text-sm font-normal text-muted-foreground">Theme</DropdownMenuLabel>
          <DropdownMenuRadioGroup
            value={choice}
            onValueChange={(v) => {
              const picked = THEMES.find((t) => t.value === v);
              if (picked !== undefined) setChoice(picked.value);
            }}
          >
            {THEMES.map((t) => (
              <DropdownMenuRadioItem key={t.value} value={t.value} className="min-h-11 sm:min-h-9">
                {t.label}
              </DropdownMenuRadioItem>
            ))}
          </DropdownMenuRadioGroup>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="min-h-11 sm:min-h-9" onSelect={() => setConfirming(true)}>
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
      <SignOutDialog open={confirming} onOpenChange={setConfirming} />
    </>
  );
}
