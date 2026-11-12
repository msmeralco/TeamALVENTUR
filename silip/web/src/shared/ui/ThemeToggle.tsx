import { Monitor, Moon, Sun } from "lucide-react";
import { Button } from "./components/button";
import { useTheme, type ThemeChoice } from "./theme";

const NEXT: Record<ThemeChoice, ThemeChoice> = { system: "light", light: "dark", dark: "system" };
const ICON = { system: Monitor, light: Sun, dark: Moon };
const WORD = { system: "System", light: "Light", dark: "Dark" };

/** One button that cycles system, light and dark. `withWord` shows the current choice beside the icon. */
export function ThemeToggle({ withWord = false }: { withWord?: boolean }) {
  const { choice, setChoice } = useTheme();
  const Icon = ICON[choice];
  return (
    <Button
      variant="ghost"
      size={withWord ? "default" : "icon"}
      className={withWord ? "min-h-11 rounded-full px-3 text-muted-foreground sm:min-h-9 pointer-coarse:min-h-11" : "size-11 rounded-full sm:size-9 pointer-coarse:size-11"}
      aria-label={`Theme: ${choice}`}
      onClick={() => setChoice(NEXT[choice])}
    >
      <Icon aria-hidden="true" />
      {withWord && <span aria-hidden="true">{WORD[choice]}</span>}
    </Button>
  );
}
