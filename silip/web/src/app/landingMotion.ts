/**
 * Scroll motion for the landing page, loaded only on "/" and only without prefers-reduced-motion.
 * Lenis smooths the native scroll (keyboard, find-in-page and anchors keep working); GSAP ScrollTrigger
 * drives the beats. Only transform, opacity, clip-path and stroke dash offsets change.
 */
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import Lenis from "lenis";

gsap.registerPlugin(ScrollTrigger);

const MOTION = "(prefers-reduced-motion: no-preference)";
// Pinned beats only on wide screens with a mouse; touch and narrow screens reveal in place.
const PIN = `${MOTION} and (min-width: 64rem) and (pointer: fine)`;
const SCRAMBLE_CHARS = "abcdefghijklmnopqrstuvwxyz";
// Short, so the random letters are gone almost as soon as they appear.
const SCRAMBLE_MS = 360;

/** Pins sit just under the sticky header, not behind it. */
function pinStart(): string {
  return `top ${document.querySelector("header")?.getBoundingClientRect().height ?? 0}px`;
}

/** Shows random letters that settle, left to right, into the element's real text (its data-decode). */
function decode(el: Element | null) {
  if (!(el instanceof HTMLElement)) return;
  const text = el.dataset.decode ?? "";
  const start = performance.now();
  const tick = (now: number) => {
    const p = Math.min(1, (now - start) / SCRAMBLE_MS);
    const fixed = Math.floor(p * text.length);
    el.textContent =
      text.slice(0, fixed) +
      Array.from(text.slice(fixed), (c) => (c === " " ? " " : SCRAMBLE_CHARS[Math.floor(Math.random() * 26)])).join("");
    if (p < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

/** Square blocks over the map; the ones nearest the edges come first, so the map dissolves inward. */
function makeBlocks(host: HTMLElement): HTMLElement[] {
  const { width, height } = host.getBoundingClientRect();
  const size = Math.max(40, Math.round(width / 20));
  const cols = Math.ceil(width / size);
  const rows = Math.ceil(height / size);
  const blocks: { el: HTMLElement; edge: number }[] = [];
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      // 0 at the center, 1 at the edge, with jitter so the edge breaks up unevenly.
      const edge = Math.max(Math.abs((c + 0.5) / cols - 0.5), Math.abs((r + 0.5) / rows - 0.5)) * 2;
      const jittered = edge + Math.random() * 0.3;
      if (jittered < 0.75) continue;
      const el = document.createElement("div");
      el.className = "absolute bg-stage opacity-0";
      Object.assign(el.style, { left: `${c * size}px`, top: `${r * size}px`, width: `${size}px`, height: `${size}px` });
      host.append(el);
      blocks.push({ el, edge: jittered });
    }
  }
  return blocks.sort((a, b) => b.edge - a.edge).map((b) => b.el);
}

function heroTimeline(hero: HTMLElement, pinned: boolean) {
  const q = gsap.utils.selector(hero);
  const blocksHost = q("[data-hero-blocks]")[0] as HTMLElement;
  const blocks = makeBlocks(blocksHost);
  gsap.set(q("[data-hud-line]"), { strokeDasharray: 1, strokeDashoffset: 1, opacity: 1 });
  gsap.set(q("[data-hud-dot]"), { scale: 0, transformOrigin: "50% 50%", opacity: 1 });
  let decoded = false;
  const tl = gsap.timeline({
    defaults: { ease: "none" },
    scrollTrigger: {
      trigger: hero,
      start: pinned ? pinStart : "top top",
      // Unpinned, the beat ends while the map is still on screen.
      end: pinned ? "+=110%" : "bottom 60%",
      pin: pinned,
      scrub: 0.6,
      onUpdate: (self) => {
        if (!decoded && self.progress > 0.6) {
          decoded = true;
          decode(hero.querySelector("[data-hud-label] [data-decode]"));
        }
      },
    },
  });
  tl.to(q("[data-hero-lift]"), { y: -64, autoAlpha: 0, duration: 0.3 }, 0)
    .to(q("[data-hero-mono]"), { opacity: 1, duration: 0.35 }, 0.1)
    .to(q("[data-hero-map]"), { scale: 0.94, duration: 0.6 }, 0.2)
    .to(blocks, { opacity: 1, duration: 0.05, stagger: { amount: 0.45 } }, 0.2)
    .to(q("[data-hero-dots]"), { opacity: 1, duration: 0.3 }, 0.3)
    .to(q("[data-hud-line]"), { strokeDashoffset: 0, duration: 0.3, stagger: 0.05 }, 0.45)
    .to(q("[data-hud-dot]"), { scale: 1, duration: 0.1, stagger: 0.05 }, 0.6)
    .to(q("[data-hud-pulse], [data-hud-tag], [data-hud-label]"), { opacity: 1, duration: 0.15, stagger: 0.05 }, 0.65)
    .to({}, { duration: 0.05 });
  return () => blocks.forEach((b) => b.remove());
}

function howItWorks(section: HTMLElement, pinned: boolean) {
  const q = gsap.utils.selector(section);
  const groups = q("[data-draw-step]");
  const steps = q("[data-step]");
  gsap.set(q("[data-draw-step] > *"), { strokeDasharray: 1, strokeDashoffset: 1 });
  if (pinned) {
    gsap.set(steps, { opacity: 0.2 });
    let shown = -1;
    const tl = gsap.timeline({
      defaults: { ease: "none" },
      scrollTrigger: {
        trigger: section,
        start: pinStart,
        end: "+=240%",
        pin: true,
        scrub: 0.6,
        onUpdate: (self) => {
          const at = Math.min(steps.length - 1, Math.floor(self.progress * steps.length * 1.05));
          if (at > shown) {
            for (let i = shown + 1; i <= at; i++) decode(steps[i]?.querySelector("[data-decode]") ?? null);
            shown = at;
          }
        },
      },
    });
    groups.forEach((group, i) => {
      tl.to(group.children, { strokeDashoffset: 0, duration: 0.8, stagger: 0.1 }, i).to(
        steps[i] ?? [],
        { opacity: 1, duration: 0.3 },
        i,
      );
    });
    tl.to({}, { duration: 0.4 });
    return;
  }
  gsap.to(q("[data-draw-step] > *"), {
    strokeDashoffset: 0,
    ease: "none",
    stagger: 0.1,
    scrollTrigger: { trigger: section, start: "top 75%", end: "bottom 60%", scrub: 0.6 },
  });
  steps.forEach((step) => {
    gsap.from(step, {
      y: 24,
      autoAlpha: 0,
      duration: 0.6,
      ease: "power2.out",
      scrollTrigger: { trigger: step, start: "top 85%", once: true },
      onStart: () => decode(step.querySelector("[data-decode]")),
    });
  });
}

function cream(root: HTMLElement) {
  const q = gsap.utils.selector(root);
  const curtain = q("[data-curtain]")[0];
  if (curtain !== undefined) {
    gsap.fromTo(
      curtain,
      { clipPath: "inset(0% 6% 0% 6%)" },
      {
        clipPath: "inset(0% 0% 0% 0%)",
        ease: "none",
        scrollTrigger: { trigger: curtain, start: "top bottom", end: "top 25%", scrub: 0.6 },
      },
    );
  }
  const card = q("[data-example-card]")[0];
  if (card !== undefined) {
    gsap
      .timeline({ scrollTrigger: { trigger: card, start: "top 85%", once: true } })
      .from(card, { y: 64, autoAlpha: 0, duration: 0.8, ease: "power3.out" })
      .fromTo(
        q("[data-example-chart] svg"),
        { clipPath: "inset(0% 100% 0% 0%)" },
        { clipPath: "inset(0% 0% 0% 0%)", duration: 1.4, ease: "power1.inOut" },
        0.3,
      );
  }
  const privacy = q("[data-privacy] li");
  gsap.from(privacy, {
    y: 16,
    autoAlpha: 0,
    duration: 0.5,
    ease: "power2.out",
    stagger: 0.15,
    scrollTrigger: { trigger: privacy[0], start: "top 85%", once: true },
  });
}

function chrome() {
  const wordmark = document.querySelector("[data-wordmark] svg");
  if (wordmark !== null) {
    gsap.fromTo(
      wordmark,
      { yPercent: 60 },
      {
        yPercent: 0,
        ease: "none",
        scrollTrigger: { trigger: wordmark.parentElement, start: "top bottom", end: "bottom bottom", scrub: 0.6 },
      },
    );
  }
  const bar = document.querySelector("[data-scroll-progress] [data-fill]");
  if (bar !== null) {
    gsap.fromTo(
      bar,
      { scaleY: 0 },
      { scaleY: 1, ease: "none", scrollTrigger: { start: 0, end: "max", scrub: true } },
    );
  }
}

/** Starts the landing motion inside root. Returns a cleanup that restores the page as rendered. */
export function startLandingMotion(root: HTMLElement): () => void {
  const mm = gsap.matchMedia();
  mm.add({ motion: MOTION, pinned: PIN }, (context) => {
    const { motion, pinned } = context.conditions as { motion: boolean; pinned: boolean };
    if (!motion) return;
    const lenis = new Lenis({ autoRaf: false });
    lenis.on("scroll", ScrollTrigger.update);
    const raf = (time: number) => lenis.raf(time * 1000);
    gsap.ticker.add(raf);
    gsap.ticker.lagSmoothing(0);
    document.documentElement.classList.add("lenis");

    const hero = root.querySelector<HTMLElement>("[data-hero]");
    const how = root.querySelector<HTMLElement>("[data-how]");
    const removeBlocks = hero === null ? undefined : heroTimeline(hero, pinned);
    if (how !== null) howItWorks(how, pinned);
    cream(root);
    chrome();

    // Content above the fold can change height (the outage list loads); keep trigger positions true.
    let pending = 0;
    const observer = new ResizeObserver(() => {
      window.clearTimeout(pending);
      pending = window.setTimeout(() => ScrollTrigger.refresh(), 150);
    });
    observer.observe(root);
    // Pins add space above later sections, so a deep link such as /#how-it-works is re-aimed once ready.
    ScrollTrigger.refresh();
    const target = window.location.hash === "" ? null : document.getElementById(window.location.hash.slice(1));
    target?.scrollIntoView({ block: "start" });

    return () => {
      observer.disconnect();
      window.clearTimeout(pending);
      gsap.ticker.remove(raf);
      lenis.destroy();
      document.documentElement.classList.remove("lenis");
      removeBlocks?.();
    };
  });
  return () => mm.revert();
}
