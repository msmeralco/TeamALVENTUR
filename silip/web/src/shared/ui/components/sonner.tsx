import { CircleCheckIcon, InfoIcon } from "lucide-react";
import type { CSSProperties } from "react";
import { Toaster as Sonner, type ToasterProps } from "sonner";
import { useTheme } from "@/shared/ui/theme";

/** Toasts only confirm results the user caused off-screen. Errors that need action stay inline. */
const Toaster = (props: ToasterProps) => {
  const { resolved } = useTheme();
  return (
    <Sonner
      theme={resolved}
      className="toaster group"
      icons={{ success: <CircleCheckIcon className="size-4" />, info: <InfoIcon className="size-4" /> }}
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
          "--border-radius": "var(--radius)",
        } as CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
