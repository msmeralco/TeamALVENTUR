import { PageHead } from "../shared/ui";
import { useDocumentTitle } from "../shared/ui/feedback";

// Copied from docs/SPEC.md#sources. Keep the two in step.
const SOURCES: { label: string; href?: string; note: string }[] = [
  { label: "powerphilippines.com/?p=25747", href: "https://powerphilippines.com/?p=25747", note: "smart meters" },
  { label: "powerphilippines.com/?p=23852", href: "https://powerphilippines.com/?p=23852", note: "8.2M customers" },
  { label: "powerphilippines.com/?p=23268", href: "https://powerphilippines.com/?p=23268", note: "GEOCC 2030" },
  { label: "ABS-CBN, 1 May 2024", note: "268 to 732 reports" },
  { label: "Daily Tribune, 23 Sep 2026", note: "EVs 24.7%" },
];

export function SourcesPage() {
  useDocumentTitle("Data sources");
  return (
    <>
      <PageHead title="Data sources" lede="Public reports behind the figures SILIP cites." />
      <ul className="grid gap-3 text-base">
        {SOURCES.map((source) => (
          <li key={source.label}>
            {source.href === undefined ? (
              source.label
            ) : (
              <a href={source.href} target="_blank" rel="noreferrer" className="underline-offset-4 hover:underline">
                {source.label}
              </a>
            )}{" "}
            <span className="text-muted-foreground">({source.note})</span>
          </li>
        ))}
      </ul>
    </>
  );
}
