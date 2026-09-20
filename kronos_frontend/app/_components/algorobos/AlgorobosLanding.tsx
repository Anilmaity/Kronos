"use client";

import React from "react";
import Link from "next/link";
import "./algorobos.css";

type Pillar = { rom: string; title: string; lede: string; body: string; tenets: string[] };
type Reading = { rom: string; title: string; body: string };

const GLYPH = "❦";

const PILLARS: Pillar[] = [
  {
    rom: "I", title: "Risk Management",
    lede: "Protect your capital. Every trade, every time.",
    body: "The first commandment of every trader who endures: never let one trade undo many. We teach position sizing, stop discipline, and the silent art of saying no — because the trade you skip is often the one that would have ruined you.",
    tenets: ["Define risk before entry", "One percent, not one hope", "Stops are vows, not suggestions"],
  },
  {
    rom: "II", title: "Strategy & Edge",
    lede: "Build a system that works — and trust it completely.",
    body: "An edge is not a secret. It is a small, repeatable advantage you have measured and verified. We help you find yours, write it down, backtest it honestly, and follow it without flinching when the screen turns red.",
    tenets: ["Backtest with cruelty", "Document the rules", "A bad month is not a broken edge"],
  },
  {
    rom: "III", title: "Trading Psychology",
    lede: "Emotions lose money. Discipline makes it. We train both.",
    body: "The market is a mirror. Greed, fear, hope, regret — they will all come to you, sometimes within a single candle. We teach you to see them, name them, and trade anyway. Mastery is not the absence of feeling but the choice to follow process instead.",
    tenets: ["Name the feeling", "Process over outcome", "Tomorrow's trades depend on today's calm"],
  },
  {
    rom: "IV", title: "Capital Management",
    lede: "Size your positions right. Grow steadily. Last long.",
    body: "Compounding rewards the patient. We show you how to size each trade so that your capital curve climbs slowly but never collapses — how to scale up after winning streaks and pull back after losses, so the math is always on your side.",
    tenets: ["Risk a fraction, never the whole", "Scale with proof, not pride", "Survive first; thrive second"],
  },
  {
    rom: "V", title: "Market Understanding",
    lede: "Know the why behind every move.",
    body: "Charts are footprints. We trace them back to liquidity, narrative, and time — three forces that move every market. Understand context and the noise begins to quiet, until the next move feels less like a guess and more like a sentence you've read before.",
    tenets: ["Liquidity, narrative, time", "Context before pattern", "Listen before predicting"],
  },
  {
    rom: "VI", title: "Process & Journaling",
    lede: "Track. Reflect. Improve. Repeat.",
    body: "Memory lies. The journal does not. We give you templates and prompts to turn every trade into a teacher — entries, exits, emotion, conviction — until your weekly review becomes the most profitable hour of your week.",
    tenets: ["Write before you trade", "Review without mercy", "Patterns appear in pages"],
  },
  {
    rom: "VII", title: "Execution",
    lede: "Precision entries. Clean exits. No second-guessing.",
    body: "When the signal arrives, the work is already done. Execution is where preparation meets the moment without hesitation — orders placed, stops set, hands off the keyboard. The trade plays out. The trader stays still.",
    tenets: ["Click without flinching", "Plan beats reaction", "Stillness is a skill"],
  },
];

const READINGS: Reading[] = [
  { rom: "III", title: "On Stillness", body: "The trader who waits for the perfect setup outlives the trader who chases. Stillness is not absence — it is patience trained into a posture." },
  { rom: "I", title: "On Capital", body: "You will not get rich on the trade you take today. You will get poor on the trade that should not have been taken. Choose accordingly." },
  { rom: "V", title: "On Liquidity", body: "Price does not move. Liquidity moves. Once you see the difference, you stop predicting candles and start reading intent." },
  { rom: "VII", title: "On Execution", body: "A plan unexecuted is a wish. A plan executed half-heartedly is a wound. Place the order. Trust the work that came before." },
  { rom: "II", title: "On The Edge", body: "An edge whispered is an edge lost. Document it. Follow it. Iterate slowly. Conviction is built not from belief but from receipts." },
];

const MANIFESTO_VERSES: { n: string; text: React.ReactNode }[] = [
  { n: "i.", text: <>The market does not reward effort. It rewards <b>edge</b>, applied with <b>discipline</b>, over a long enough horizon for the math to declare itself.</> },
  { n: "ii.", text: <>We do not believe in noise, hot tips, or hero trades. We believe in <em>systems</em> — small, repeatable advantages, written down, executed without flinching.</> },
  { n: "iii.", text: <>We treat each trade as a sentence in a longer story. The journal is the manuscript. The capital curve is the only review that matters.</> },
  { n: "iv.", text: <>An algorithm cannot replace conviction; it can only sharpen it. Algorobos is the marriage of <b>algorithmic thinking</b> and <em>human discipline</em> — neither, alone, is enough.</> },
  { n: "v.", text: <>We do not promise riches. We promise a method, a community, and a craft. The market will decide the rest, as it always does.</> },
];

function useReveal() {
  React.useEffect(() => {
    const els = document.querySelectorAll(".algorobos-root .reveal, .algorobos-root .lm, .algorobos-root .sup");
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => {
        if (e.isIntersecting) {
          e.target.classList.add("in");
          io.unobserve(e.target);
        }
      });
    }, { threshold: 0.12 });
    els.forEach((e) => io.observe(e));
    return () => io.disconnect();
  }, []);
}

function ScrollThread() {
  const fillRef = React.useRef<HTMLDivElement>(null);
  const numRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const onScroll = () => {
      const docH = Math.max(1, document.documentElement.scrollHeight - window.innerHeight);
      const p = Math.min(1, Math.max(0, window.scrollY / docH));
      const trackH = Math.max(0, window.innerHeight - 160);
      if (fillRef.current) fillRef.current.style.height = p * trackH + "px";
      if (numRef.current) numRef.current.textContent = String(Math.round(p * 100)).padStart(3, "0") + " · ALGOROBOS";
    };
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    window.addEventListener("resize", onScroll);
    return () => {
      window.removeEventListener("scroll", onScroll);
      window.removeEventListener("resize", onScroll);
    };
  }, []);
  return (
    <>
      <div className="thread" aria-hidden="true"><div ref={fillRef} className="thread-fill" /></div>
      <div ref={numRef} className="thread-num">000 · ALGOROBOS</div>
    </>
  );
}

function RevealLine({ children, delay = 0 }: { children: React.ReactNode; delay?: number }) {
  const cls = "lm" + (delay ? ` d${delay}` : "");
  return <span className={cls}><span className="lm-inner">{children}</span></span>;
}

function Ornament({ style, className }: { style?: React.CSSProperties; className?: string }) {
  return (
    <div className={"orn" + (className ? " " + className : "")} style={style}>
      <div className="orn-rule" />
      <span className="orn-glyph">{GLYPH}</span>
      <div className="orn-rule" />
    </div>
  );
}

function SectionLabel({ num, label }: { num: string; label: string }) {
  return (
    <div className="section-num">
      <span className="bar" />
      <span><b>{num}</b> &nbsp;—&nbsp; {label}</span>
      <span className="bar" />
    </div>
  );
}

function Counter({ to }: { to: number }) {
  const [val, setVal] = React.useState(0);
  const ref = React.useRef<HTMLSpanElement>(null);
  React.useEffect(() => {
    const el = ref.current;
    if (!el) return;
    const io = new IntersectionObserver(([e]) => {
      if (!e.isIntersecting) return;
      io.disconnect();
      const dur = 1400, t0 = performance.now();
      const tick = (t: number) => {
        const k = Math.min(1, (t - t0) / dur);
        const eased = 1 - Math.pow(1 - k, 3);
        setVal(Math.round(to * eased));
        if (k < 1) requestAnimationFrame(tick);
      };
      requestAnimationFrame(tick);
    }, { threshold: 0.4 });
    io.observe(el);
    return () => io.disconnect();
  }, [to]);
  return <span ref={ref}>{val.toLocaleString()}</span>;
}

function Nav() {
  const go = (id: string) => (e: React.MouseEvent) => {
    e.preventDefault();
    document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "start" });
  };
  return (
    <nav className="top">
      <div className="wrap nav-row">
        <a href="#top" className="brand" onClick={go("top")}>
          <span className="brand-mark" />
          <span className="brand-name">Algorobos</span>
        </a>
        <div className="nav-links">
          <a href="#about" onClick={go("about")}>About</a>
          <a href="#manifesto" onClick={go("manifesto")}>Manifesto</a>
          <a href="#pillars" onClick={go("pillars")}>The Seven</a>
          <a href="#why" onClick={go("why")}>Why Us</a>
          <a href="#rule" onClick={go("rule")}>The Rule</a>
        </div>
        <Link href="/login" className="btn btn-ghost" style={{ padding: "10px 18px" }}>
          Login Now <span className="arr">→</span>
        </Link>
      </div>
    </nav>
  );
}

function Hero() {
  const [readingIdx, setReadingIdx] = React.useState(0);
  const [dateStr, setDateStr] = React.useState("");
  React.useEffect(() => {
    setDateStr(new Date().toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }).toUpperCase());
  }, []);
  const r = READINGS[readingIdx];
  const next = () => setReadingIdx((i) => (i + 1) % READINGS.length);
  return (
    <section id="top" className="hero wrap reveal">
      <div className="hero-grid">
        <div>
          <div className="eyebrow">Est. 2026 · Algorithmic Thinking · Human Discipline</div>
          <h1>
            <RevealLine>Trade <em>Smarter</em></RevealLine>
            <RevealLine delay={1}>with Algorobos<span className="gold">.</span></RevealLine>
          </h1>
          <p className="hero-sub">
            Algorithmic precision. Human discipline. <em>Real results.</em>
            A trading education and strategy platform built for the modern trader who refuses to confuse activity with edge.
          </p>
          <div className="hero-cta">
            <Link href="/login" className="btn btn-primary">
              Login Now <span className="arr">→</span>
            </Link>
            <a className="btn btn-ghost" href="#pillars" onClick={(e) => { e.preventDefault(); document.getElementById("pillars")?.scrollIntoView({ behavior: "smooth" }); }}>
              Read The Seven
            </a>
          </div>
          <div className="hero-meta">
            <span><b>10,247</b> Active traders</span>
            <span><b>1,140+</b> Daily setups logged</span>
            <span><b>0.91%</b> Avg risk per trade</span>
          </div>
        </div>

        <aside className="reading">
          <div className="reading-tag">
            <span><span className="pulse" /> &nbsp;Today&apos;s Reading</span>
            <span>{dateStr}</span>
          </div>
          <div className="reading-roman" key={"r-" + readingIdx}>{r.rom}</div>
          <div className="reading-title" key={"t-" + readingIdx}>{r.title}</div>
          <div className="reading-body" key={"b-" + readingIdx}>{r.body}</div>
          <div className="reading-foot">
            <span>Pillar {r.rom} · Verse {readingIdx + 1}</span>
            <button onClick={next}>Draw another {GLYPH}</button>
          </div>
        </aside>
      </div>
    </section>
  );
}

function About() {
  return (
    <section id="about" className="about wrap reveal">
      <div className="about-inner">
        <SectionLabel num="01" label="Who We Are" />
        <h2 style={{ marginTop: 24 }}><RevealLine>A craft, <em className="ital gold">not a casino.</em></RevealLine></h2>
        <p>
          Algorobos is a trading education and strategy platform built for the modern trader.
          We combine algorithmic precision with proven trading principles to help you build a
          consistent, disciplined approach to the markets — a craft handed down from screen to
          screen, written in process and earned in patience.
        </p>
      </div>
    </section>
  );
}

function Manifesto() {
  return (
    <section id="manifesto" className="manifesto wrap reveal">
      <div className="manifesto-head">
        <SectionLabel num="02" label="The Manifesto" />
        <h2>
          <RevealLine>We do not predict the market.</RevealLine>
          <RevealLine delay={1}>We <em>prepare</em> for it.</RevealLine>
        </h2>
      </div>
      <div className="verses">
        {MANIFESTO_VERSES.map((v, i) => (
          <React.Fragment key={i}>
            <div className="v-num sup" style={{ transitionDelay: i * 0.08 + "s" }}>{v.n}</div>
            <div className="v-body sup" style={{ transitionDelay: i * 0.08 + 0.06 + "s" }}>{v.text}</div>
          </React.Fragment>
        ))}
      </div>
      <div style={{ marginTop: 64, display: "grid", placeItems: "center" }}>
        <Ornament style={{ maxWidth: 240 }} />
      </div>
    </section>
  );
}

function PillarsCodex() {
  const [active, setActive] = React.useState(0);
  const p = PILLARS[active];
  return (
    <section id="pillars" className="pillars wrap reveal">
      <div className="pillars-head">
        <SectionLabel num="03" label="The Seven" />
        <h2 style={{ marginTop: 24 }}><RevealLine>The Seven Pillars of Trading</RevealLine></h2>
        <div className="pillars-sub">— the Algorobos way —</div>
      </div>
      <div className="codex">
        <div className="codex-list">
          {PILLARS.map((pl, i) => (
            <button
              key={i}
              className={"codex-item" + (i === active ? " active" : "")}
              onClick={() => setActive(i)}
              onMouseEnter={() => setActive(i)}
            >
              <span className="ci-rom">{pl.rom}.</span>
              <span className="ci-title">{pl.title}</span>
              <span className="ci-mark">◆</span>
            </button>
          ))}
        </div>
        <div className="codex-detail" key={active}>
          <div className="pillar-rom">{p.rom}</div>
          <h3>{p.title}</h3>
          <div className="lede">{p.lede}</div>
          <div className="body">{p.body}</div>
          <div className="codex-tenets">
            {p.tenets.map((t, i) => <div key={i} className="t">{t}</div>)}
          </div>
        </div>
      </div>
    </section>
  );
}

function WhyUs() {
  const items = [
    { rom: "I", num: <><Counter to={94} /><em>%</em></>, label: "Stick With Process", desc: "Members who report following their journal weekly after their first month." },
    { rom: "II", num: <><Counter to={100} /><em>+</em></>, label: "Setups Each Day", desc: "Algo-backed, human-tested ideas surfaced across equities, indices, and crypto." },
    { rom: "III", num: <><Counter to={7} /><em>×</em></>, label: "Pillar Curriculum", desc: "Seven chapters of structured learning — clear, jargon-free, and built for the screen." },
  ];
  return (
    <section id="why" className="why wrap reveal">
      <div className="why-head">
        <SectionLabel num="04" label="Why It Works" />
        <h2 style={{ marginTop: 24 }}><RevealLine>Why Traders Trust Algorobos</RevealLine></h2>
      </div>
      <div className="why-grid">
        {items.map((it, i) => (
          <div key={i} className="why-card">
            <div className="why-rom">{it.rom}</div>
            <div className="why-num">{it.num}</div>
            <div className="why-label">{it.label}</div>
            <div className="why-desc">{it.desc}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

function Marquee() {
  const words = ["Discipline", "Patience", "Process", "Edge", "Stillness", "Capital"];
  const block = (k: number) => (
    <span key={k}>
      {words.map((w, i) => (
        <React.Fragment key={i}>
          <span className={i % 2 === 0 ? "filled" : ""}>{w}</span>
          <span className="dot">{GLYPH}</span>
        </React.Fragment>
      ))}
    </span>
  );
  return (
    <div className="marquee" aria-hidden="true">
      <div className="marquee-track">{block(0)}{block(1)}</div>
    </div>
  );
}

function Testimonial() {
  return (
    <section className="testi wrap reveal">
      <Ornament style={{ maxWidth: 240, margin: "0 auto" }} />
      <p className="testi-quote">
        Algorobos gave me a real system. No noise, no guesswork — just a process that works.
      </p>
      <div className="testi-attrib">— <b>Ravi S.</b> &nbsp;·&nbsp; Ahmedabad</div>
    </section>
  );
}

function GoldenRule() {
  return (
    <section id="rule" className="rule wrap reveal">
      <div className="tablet">
        <div className="eyebrow">The Golden Rule</div>
        <h3><RevealLine>Protect your capital first.</RevealLine></h3>
        <p><RevealLine delay={1}>Profits follow discipline, not luck.</RevealLine></p>
        <div className="seal">{GLYPH}</div>
      </div>
    </section>
  );
}

function Finale() {
  return (
    <section id="cta" className="finale reveal">
      <div className="wrap">
        <SectionLabel num="07" label="Final Verse" />
        <h2>
          <RevealLine>The market has the answer.</RevealLine>
          <RevealLine delay={2}><em>Train to read it.</em></RevealLine>
        </h2>
        <p className="lede">Join thousands of traders who have traded their guesswork for a craft. The first chapter is on us.</p>
        <div style={{ display: "flex", gap: 14, justifyContent: "center", flexWrap: "wrap" }}>
          <Link href="/login" className="btn btn-primary">
            Login Now <span className="arr">→</span>
          </Link>
          <a className="btn btn-ghost" href="#pillars" onClick={(e) => { e.preventDefault(); document.getElementById("pillars")?.scrollIntoView({ behavior: "smooth" }); }}>
            Re-read The Seven
          </a>
        </div>
        <Ornament className="post-orn" style={{ maxWidth: 300, margin: "36px auto 0" }} />
      </div>
    </section>
  );
}

function Footer() {
  return (
    <footer>
      <div className="wrap foot-grid">
        <div className="foot-meta">© 2026 Algorobos · All rights reserved</div>
        <div className="foot-links">
          <a href="#top">Home</a>
          <a href="#about">About</a>
          <a href="#">Blog</a>
          <a href="#">Contact</a>
          <a href="#">Privacy</a>
        </div>
        <div className="foot-meta right">hello@algorobos.com</div>
      </div>
    </footer>
  );
}

export default function AlgorobosLanding() {
  useReveal();
  return (
    <div className="algorobos-root">
      <ScrollThread />
      <Nav />
      <Hero />
      <About />
      <Manifesto />
      <PillarsCodex />
      <WhyUs />
      <Marquee />
      <Testimonial />
      <GoldenRule />
      <Finale />
      <Footer />
    </div>
  );
}
