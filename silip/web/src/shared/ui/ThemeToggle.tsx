import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "./components/button";
import { useTheme, type ThemeChoice } from "./theme";

const NEXT: Record<ThemeChoice, ThemeChoice> = { system: "light", light: "dark", dark: "system" };
const ICON = { system: Monitor, light: Sun, dark: Moon };

/** One icon button that cycles system, light and dark. */
export function ThemeToggle() {
  const { choice, setChoice } = useTheme();
  const Icon = ICON[choice];
  return (
    <Button
      variant="ghost"
      size="icon"
      className="size-11 rounded-full sm:size-9"
      aria-label={`Theme: ${choice}`}
      onClick={() => setChoice(NEXT[choice])}
    >
      <Icon aria-hidden="true" />
    </Button>
  );
}
