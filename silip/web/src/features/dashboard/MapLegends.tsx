import { CSS_VAR_COLORS, TIERS, chargerPinSvg, transformerPinSvg } from "./pinIcons";

const ICON_PX = 22;

/** The map's own pin, drawn inline with theme tokens. Decorative: the words beside it carry the meaning. */
function PinIcon({ svg }: { svg: string }) {
  return <span aria-hidden="true" className="inline-flex shrink-0" dangerouslySetInnerHTML={{ __html: svg }} />;
}

/** Risk overlay key: each pin with its tier word, the Critical mark in words, and what shading means. */
export function RiskLegend() {
  return (
    <div className="grid gap-1 rounded-xl bg-card/90 px-2.5 py-1.5 text-xs text-muted-foreground">
      <span className="flex flex-wrap items-center gap-x-3 gap-y-1">
        {TIERS.map((tier) => (
          <span key={tier} className="flex items-center gap-1 font-semibold text-foreground">
            <PinIcon svg={transformerPinSvg(tier, CSS_VAR_COLORS, { sizePx: ICON_PX })} />
            {tier}
          </span>
        ))}
      </span>
      <span>Critical pins carry a ! mark.</span>
      <span>Shaded: estimated service area</span>
    </div>
  );
}

/** EV overlay key: the charger pin, the DC tag and the reach ring, each in words. */
export function EvLegend({ reach }: { reach: string }) {
  return (
    <>
      <span className="flex items-center gap-2">
        <PinIcon svg={chargerPinSvg(false, CSS_VAR_COLORS, { sizePx: ICON_PX })} />
        Public EV charger, source: DOE
      </span>
      <span className="flex items-center gap-2">
        <PinIcon svg={chargerPinSvg(true, CSS_VAR_COLORS, { sizePx: ICON_PX })} />
        DC tag: has DC fast charging
      </span>
      <span className="flex items-center gap-2">
        <span
          aria-hidden="true"
          className="mx-[3px] size-4 shrink-0 rounded-full border-2 border-dashed border-foreground"
        />
        {reach}
      </span>
    </>
  );
}
