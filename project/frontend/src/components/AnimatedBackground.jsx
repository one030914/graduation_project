"use client";

export function AnimatedBackground() {
  return (
    <div className="pointer-events-none fixed inset-0 overflow-hidden" aria-hidden="true">
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,#312e81_0%,#120f2a_42%,#070b18_100%)]" />
      <div className="bg-grid-motion absolute inset-0 opacity-50" />
      <div className="bg-light-beam bg-light-beam-one absolute left-[-12%] top-[10%] h-[34rem] w-[18rem]" />
      <div className="bg-light-beam bg-light-beam-two absolute right-[4%] top-[32%] h-[28rem] w-[16rem]" />
      <div className="bg-aurora bg-aurora-one absolute -left-24 top-[-10%] h-[28rem] w-[28rem]" />
      <div className="bg-aurora bg-aurora-two absolute right-[-8rem] top-[22%] h-[24rem] w-[24rem]" />
      <div className="bg-aurora bg-aurora-three absolute bottom-[-8rem] left-[18%] h-[26rem] w-[26rem]" />
      <div className="bg-orbit absolute left-1/2 top-1/2 h-[42rem] w-[42rem] -translate-x-1/2 -translate-y-1/2" />
      <div className="bg-shape bg-shape-diamond absolute left-[8%] top-[18%] h-28 w-28" />
      <div className="bg-shape bg-shape-ring absolute right-[12%] top-[16%] h-40 w-40" />
      <div className="bg-shape bg-shape-triangle absolute bottom-[18%] right-[18%] h-36 w-36" />
      <div className="bg-shape bg-shape-square absolute bottom-[12%] left-[10%] h-24 w-24" />
    </div>
  );
}
