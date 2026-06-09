"use client";

export function ResultHeader({ label = "Result", title, subtitle }) {
  return (
    <div className="rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 shadow-[0_18px_48px_rgba(2,6,23,0.28)]">
      <p className="text-base font-black uppercase tracking-[0.14em] text-indigo-200/70">{label}</p>
      <h2 className="mt-2 break-words text-2xl font-black leading-tight tracking-normal text-white">{title}</h2>
      {subtitle && (
        <p className="mt-2 break-words text-base font-semibold leading-7 text-white/50">
          {subtitle}
        </p>
      )}
    </div>
  );
}

export function ResultShell({ label = "Result", title, subtitle, children }) {
  return (
    <article className="rounded-3xl border border-white/10 bg-slate-950/35 p-5 shadow-[0_24px_70px_rgba(2,6,23,0.32)] ring-1 ring-indigo-300/5 backdrop-blur-md sm:p-7">
      <ResultHeader label={label} title={title} subtitle={subtitle} />
      <div className="mt-6 space-y-5">{children}</div>
    </article>
  );
}

export function ResultCard({ title, children, tone = "indigo", className = "" }) {
  const toneClass = {
    amber: "text-amber-200",
    emerald: "text-emerald-200",
    red: "text-red-200",
    violet: "text-violet-200",
    indigo: "text-indigo-200",
  }[tone] || "text-indigo-200";

  return (
    <section
      className={`rounded-2xl border border-white/10 bg-[#070d20]/90 p-6 text-white shadow-[0_18px_48px_rgba(2,6,23,0.3)] ring-1 ring-indigo-300/5 backdrop-blur-md ${className}`}
    >
      <h3 className={`text-xl font-black tracking-normal ${toneClass}`}>{title}</h3>
      <div className="mt-4 text-base font-semibold leading-8 text-white/72">{children}</div>
    </section>
  );
}


export function FallbackText({ children = "目前沒有可顯示的資料。" }) {
  return (
    <p className="rounded-xl border border-white/10 bg-white/[0.035] px-4 py-3 text-base font-semibold leading-7 text-white/48">
      {children}
    </p>
  );
}

export function InfoTile({ label, value, tone = "default" }) {
  const toneClass = {
    amber: "border-amber-300/15 bg-amber-400/8 text-amber-200",
    emerald: "border-emerald-300/15 bg-emerald-400/8 text-emerald-200",
    red: "border-red-300/15 bg-red-400/8 text-red-200",
    indigo: "border-indigo-300/15 bg-indigo-400/8 text-indigo-200",
    default: "border-white/10 bg-white/[0.04] text-white/88",
  }[tone] || "border-white/10 bg-white/[0.04] text-white/88";

  return (
    <div className={`rounded-xl border px-4 py-3 ring-1 ring-white/5 ${toneClass}`}>
      <p className="text-base font-bold text-white/42">{label}</p>
      <p className="mt-1 break-words text-base font-black">{String(value)}</p>
    </div>
  );
}

export function ResultFooter({ children }) {
  return <footer className="border-t border-white/10 pt-4 text-base font-semibold leading-7 text-white/45">{children}</footer>;
}
