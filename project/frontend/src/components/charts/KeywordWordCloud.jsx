"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useWordcloud } from "@visx/wordcloud";

const WORD_COLORS = {
  zh: "#fcd34d",
  en: "#7dd3fc",
  mixed: "#c4b5fd",
  unknown: "#d1d5db",
};

const LANGUAGE_LABELS = {
  zh: "中文",
  en: "英文",
  mixed: "混合",
  unknown: "未知",
};

const fixedRandom = () => 0.5;
const fontSize = (word) => word.size;
const fontWeight = () => 900;

function normalizeWords(data) {
  const words = data
    .map((item, index) => {
      const text = String(item.text || item.keyword || item.label || "").trim();
      const value = Number(item.value ?? item.count ?? 0) || 0;

      return {
        text,
        value,
        language: item.language || "mixed",
        index,
      };
    })
    .filter((item) => item.text)
    .slice(0, 40);

  const maxValue = Math.max(...words.map((item) => item.value), 1);

  const totalValue = words.reduce((sum, item) => sum + item.value, 0) || 1;

  return words.map((item, rankIndex) => {
    const weight = item.value / maxValue;

    return {
      ...item,
      size: 20 + weight * 56,
      opacity: 0.62 + weight * 0.34,
      ratio: item.value / totalValue,
      rank: rankIndex + 1,
      color: WORD_COLORS[item.language] || WORD_COLORS.mixed,
    };
  });
}

function fmtPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

function rotateWord(word) {
  return 0;
}

function useElementSize() {
  const ref = useRef(null);
  const [size, setSize] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const element = ref.current;
    if (!element) return undefined;

    const updateSize = () => {
      const rect = element.getBoundingClientRect();
      const nextSize = {
        width: Math.floor(rect.width),
        height: Math.floor(rect.height),
      };

      setSize((currentSize) => {
        if (
          currentSize.width === nextSize.width
          && currentSize.height === nextSize.height
        ) {
          return currentSize;
        }

        return nextSize;
      });
    };

    updateSize();

    const observer = new ResizeObserver(updateSize);
    observer.observe(element);

    return () => observer.disconnect();
  }, []);

  return [ref, size];
}

function fallbackLayout(words, width, height) {
  const padding = 18;
  const maxWidth = Math.max(120, width - padding * 2);
  let x = padding;
  let y = padding + 34;
  let lineHeight = 0;

  return words
    .map((word) => {
      const textWidth = Math.min(maxWidth, word.text.length * word.size * 0.56 + 20);

      if (x + textWidth > width - padding) {
        x = padding;
        y += lineHeight + 10;
        lineHeight = 0;
      }

      const positioned = {
        ...word,
        x: x + textWidth / 2 - width / 2,
        y: y - height / 2,
        rotate: 0,
      };

      x += textWidth + 10;
      lineHeight = Math.max(lineHeight, word.size * 1.2);

      return positioned;
    })
    .filter((word) => word.y < height / 2 - padding);
}

function estimateWordBounds(word) {
  const rotate = Math.abs(Number(word.rotate || 0));
  const width = String(word.text || "").length * Number(word.size || 0) * 0.62;
  const height = Number(word.size || 0) * 1.15;
  const pad = rotate > 0 ? 14 : 8;

  return {
    x0: Number(word.x || 0) - width / 2 - pad,
    x1: Number(word.x || 0) + width / 2 + pad,
    y0: Number(word.y || 0) - height / 2 - pad,
    y1: Number(word.y || 0) + height / 2 + pad,
  };
}

function getCloudTransform(words, width, height, compact) {
  if (!words.length || width <= 0 || height <= 0) {
    return { x: width / 2, y: height / 2, scale: 1 };
  }

  const bounds = words.reduce(
    (acc, word) => {
      const wordBounds = estimateWordBounds(word);
      return {
        x0: Math.min(acc.x0, wordBounds.x0),
        x1: Math.max(acc.x1, wordBounds.x1),
        y0: Math.min(acc.y0, wordBounds.y0),
        y1: Math.max(acc.y1, wordBounds.y1),
      };
    },
    { x0: Infinity, x1: -Infinity, y0: Infinity, y1: -Infinity },
  );

  const cloudWidth = Math.max(1, bounds.x1 - bounds.x0);
  const cloudHeight = Math.max(1, bounds.y1 - bounds.y0);
  const availableWidth = width * (compact ? 0.88 : 0.76);
  const availableHeight = height * (compact ? 0.9 : 0.8);
  const scale = Math.min(compact ? 1.9 : 1.7, availableWidth / cloudWidth, availableHeight / cloudHeight);
  const centerX = (bounds.x0 + bounds.x1) / 2;
  const centerY = (bounds.y0 + bounds.y1) / 2;

  return {
    x: width / 2 - centerX * scale,
    y: height / 2 - centerY * scale,
    scale,
  };
}

function WordCloudCanvas({ data, compact = false }) {
  const [containerRef, size] = useElementSize();
  const [tooltip, setTooltip] = useState(null);
  const width = size.width;
  const height = size.height;
  const words = useMemo(() => normalizeWords(data), [data]);
  const cloudWords = useWordcloud({
    words,
    width,
    height,
    font: "Arial",
    fontSize,
    fontWeight,
    padding: 3,
    rotate: rotateWord,
    spiral: "archimedean",
    random: fixedRandom,
  });

  const visibleWords = cloudWords.length > 0
    ? cloudWords
    : fallbackLayout(words, width, height);
  const cloudTransform = getCloudTransform(visibleWords, width, height, compact);

  const updateTooltip = useCallback((event, word) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (!rect) return;

    setTooltip({
      word,
      x: event.clientX - rect.left,
      y: event.clientY - rect.top,
    });
  }, [containerRef]);

  const renderWord = useCallback((word) => {
    const isActive = tooltip?.word?.index === word.index;

    return (
      <text
        key={`${word.text}-${word.index}`}
        className="cursor-default transition-opacity duration-150"
        fill={word.color}
        fontSize={word.size}
        fontWeight="900"
        opacity={isActive ? 1 : word.opacity}
        textAnchor="middle"
        dominantBaseline="middle"
        transform={`translate(${word.x}, ${word.y}) rotate(${word.rotate || 0})`}
        onMouseEnter={(event) => updateTooltip(event, word)}
        onMouseMove={(event) => updateTooltip(event, word)}
        onMouseLeave={() => setTooltip(null)}
      >
        {word.text}
      </text>
    );
  }, [tooltip, updateTooltip]);

  const tooltipWidth = 224;
  const tooltipHeight = 160;
  const tooltipLeft = tooltip
    ? Math.min(Math.max(16, tooltip.x + 18), Math.max(16, width - tooltipWidth - 16))
    : 0;
  const tooltipTop = tooltip
    ? tooltip.y + tooltipHeight + 24 > height
      ? Math.max(16, tooltip.y - tooltipHeight - 18)
      : tooltip.y + 18
    : 0;

  return (
    <div
      ref={containerRef}
      className="relative h-full w-full overflow-visible rounded-[18px] border border-white/10 bg-white/[0.035]"
      role="img"
      aria-label="關鍵詞文字雲"
    >
      {width > 0 && height > 0 && words.length > 0 && (
        <svg className="overflow-hidden rounded-[18px]" width={width} height={height}>
          <g transform={`translate(${cloudTransform.x}, ${cloudTransform.y}) scale(${cloudTransform.scale})`}>
            {visibleWords.map(renderWord)}
          </g>
        </svg>
      )}
      {tooltip && (
        <div
          className="pointer-events-none absolute z-10 w-56 rounded-xl border border-white/12 bg-slate-900/95 px-4 py-3 text-slate-100 shadow-[0_18px_40px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/10 backdrop-blur-md"
          style={{
            left: tooltipLeft,
            top: tooltipTop,
          }}
        >
          <p className="text-base font-black text-white">關鍵詞：{tooltip.word.text}</p>
          <div className="mt-2 space-y-1 text-base font-semibold text-indigo-200">
            <p>出現次數：{tooltip.word.value} 則</p>
            <p>占比：{fmtPercent(tooltip.word.ratio)}</p>
            <p>排名：#{tooltip.word.rank}</p>
            <p>語言：{LANGUAGE_LABELS[tooltip.word.language] || tooltip.word.language}</p>
          </div>
        </div>
      )}
    </div>
  );
}

function WordCloudLegend() {
  return (
    <div className="mt-4 flex flex-wrap gap-2 text-sm font-bold text-white/52">
      <span className="inline-flex items-center gap-2 rounded-full border border-amber-300/15 bg-amber-300/8 px-3 py-1">
        <span className="h-2.5 w-2.5 rounded-full bg-amber-300" />
        中文
      </span>
      <span className="inline-flex items-center gap-2 rounded-full border border-sky-300/15 bg-sky-300/8 px-3 py-1">
        <span className="h-2.5 w-2.5 rounded-full bg-sky-300" />
        英文
      </span>
      <span className="inline-flex items-center gap-2 rounded-full border border-violet-300/15 bg-violet-300/8 px-3 py-1">
        <span className="h-2.5 w-2.5 rounded-full bg-violet-300" />
        混合/未知
      </span>
    </div>
  );
}

export function KeywordWordCloud({ data = [], compact = false }) {
  const words = normalizeWords(data);

  if (words.length === 0) return null;

  return (
    <section className="overflow-visible rounded-2xl border border-white/10 bg-[#070d20]/90 p-7 text-white shadow-[0_22px_60px_rgba(2,6,23,0.36)] ring-1 ring-indigo-300/5 backdrop-blur-md">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="text-xl font-black tracking-normal text-indigo-200">文字雲</h3>
          <p className="mt-2 text-base font-semibold text-white/45">字越大代表出現在越多留言中</p>
          {!compact && <WordCloudLegend />}
        </div>
        <div className="rounded-xl border border-sky-300/15 bg-sky-400/8 px-3 py-2 text-right">
          <p className="text-sm font-bold text-white/38">詞項數</p>
          <p className="mt-1 text-xl font-black text-sky-200">{words.length}</p>
        </div>
      </div>

      {compact && <WordCloudLegend />}

      <div className={`${compact ? "mt-5 h-[400px] min-h-[400px]" : "mt-6 h-[430px] min-h-[430px]"} min-w-0`}>
        <WordCloudCanvas data={data} compact={compact} />
      </div>
    </section>
  );
}
