import React, { useState, useEffect } from "react";

interface TrendingItem {
  query: str;
  count: number;
  score: number;
}

interface TrendingWidgetProps {
  mode: "basic" | "enhanced";
  setMode: (mode: "basic" | "enhanced") => void;
  onItemClick: (query: str) => void;
  refreshTrigger: number;
}

export default function TrendingWidget({ mode, setMode, onItemClick, refreshTrigger }: TrendingWidgetProps) {
  const [trending, setTrending] = useState<TrendingItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch trending queries when mode or refresh trigger changes
  useEffect(() => {
    async function fetchTrending() {
      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_URL}/trending?mode=${mode}`);
        if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
        const data = await res.json();
        setTrending(data.suggestions || []);
      } catch (err) {
        console.error("Fetch trending error:", err);
        setError("Failed to load trending queries.");
      } finally {
        setLoading(false);
      }
    }

    fetchTrending();
  }, [mode, refreshTrigger, API_URL]);

  return (
    <div className="glow-card p-6 bg-zinc-900/40 border border-zinc-800 rounded-2xl w-full">
      {/* Header and Toggle */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-800 pb-4 mb-4">
        <div>
          <h2 className="text-lg font-bold text-white flex items-center gap-2">
            <span className="text-violet-400">
              <svg className="w-5 h-5 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
              </svg>
            </span>
            Trending Searches
          </h2>
          <p className="text-xs text-zinc-500 mt-0.5">Top queries currently driving system traffic</p>
        </div>

        {/* Toggle Mode */}
        <div className="flex p-0.5 bg-zinc-950 rounded-lg border border-zinc-850 self-start">
          <button
            onClick={() => setMode("basic")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 ${
              mode === "basic"
                ? "bg-zinc-800 text-white shadow"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Basic (Counts)
          </button>
          <button
            onClick={() => setMode("enhanced")}
            className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-all duration-150 ${
              mode === "enhanced"
                ? "bg-violet-950/50 text-violet-300 border border-violet-800/30 shadow"
                : "text-zinc-500 hover:text-zinc-300"
            }`}
          >
            Enhanced (Recency)
          </button>
        </div>
      </div>

      {/* Seeder check / Error info */}
      {error && (
        <div className="py-8 text-center text-sm text-rose-500">{error}</div>
      )}

      {loading && trending.length === 0 ? (
        <div className="flex justify-center items-center py-16">
          <span className="animate-spin rounded-full h-7 w-7 border-2 border-zinc-700 border-t-violet-500" />
        </div>
      ) : trending.length === 0 ? (
        <div className="text-center py-12 text-zinc-500 text-sm">No trending searches found. Start typing above.</div>
      ) : (
        <div className="space-y-2">
          {trending.map((item, index) => (
            <div
              key={index}
              onClick={() => onItemClick(item.query)}
              className="flex items-center justify-between p-3 rounded-lg bg-zinc-950/40 hover:bg-zinc-800/50 border border-zinc-850 hover:border-zinc-700 cursor-pointer select-none transition-all duration-150 group"
            >
              <div className="flex items-center gap-3">
                <span className={`w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold ${
                  index === 0 ? "bg-violet-950/80 text-violet-300 border border-violet-800/30" :
                  index === 1 ? "bg-zinc-800 text-zinc-300" :
                  index === 2 ? "bg-zinc-900 text-zinc-400" : "text-zinc-650"
                }`}>
                  {index + 1}
                </span>
                <span className="text-zinc-300 group-hover:text-white font-medium text-[14px]">
                  {item.query}
                </span>
              </div>
              
              <div className="flex items-center gap-3">
                <span className="text-xs text-zinc-500 bg-zinc-950 px-2 py-0.5 rounded border border-zinc-900">
                  {item.count.toLocaleString()} clicks
                </span>
                {mode === "enhanced" && (
                  <span className="text-[11px] text-violet-400 font-mono bg-violet-950/30 px-1.5 py-0.5 rounded border border-violet-800/20">
                    score: {item.score.toFixed(1)}
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Explanatory helper box */}
      <div className="mt-5 p-3.5 bg-zinc-950/60 border border-zinc-850 rounded-xl">
        <h4 className="text-xs font-bold text-zinc-400 flex items-center gap-1.5">
          <svg className="w-3.5 h-3.5 text-violet-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          Algorithm Spotlight: {mode === "basic" ? "Historical Count" : "Recency Decay"}
        </h4>
        <p className="text-[11px] text-zinc-500 mt-1 leading-relaxed">
          {mode === "basic" 
            ? "Ordered by flat historical frequency. Top baseline queries like 'iphone' remain permanently locked at the top."
            : "Recency algorithm: Score = 0.8 * LN(historical_count + 1) + 0.2 * SUM(e^(-lambda * dt)). Search 'nextjs 15 features' or 'chatgpt 5 release date' a few times to watch them jump to the top."}
        </p>
      </div>

    </div>
  );
}
