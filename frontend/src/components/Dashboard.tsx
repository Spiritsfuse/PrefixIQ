import React, { useState, useEffect } from "react";

interface MetricsData {
  suggest_metrics: {
    total_calls: number;
    cache_hits: number;
    cache_misses: number;
    cache_hit_rate_percentage: number;
    latency_ms: { avg: number; p50: number; p95: number };
  };
  search_metrics: {
    total_calls: number;
    latency_ms: { avg: number; p50: number; p95: number };
  };
  database_metrics: {
    total_queries_in_db: number;
    db_reads: number;
    db_writes: number;
    flush_count: number;
    average_batch_size: number;
    batch_write_reduction_percentage: number;
  };
  redis_metrics: {
    total_cached_keys: number;
    nodes_health: Record<string, { status: str; cached_keys: number }>;
    ring_distribution: Record<string, number>;
  };
  queue_metrics: {
    background_queue_length: number;
  };
}

interface DebugData {
  prefix: str;
  hash_value: str;
  assigned_node: str;
  cache_hit: boolean;
  suggestions: { query: str; count: number; score: number }[];
  ring_distribution: Record<string, str>;
}

interface DashboardProps {
  refreshTrigger: number;
}

export default function Dashboard({ refreshTrigger }: DashboardProps) {
  const [metrics, setMetrics] = useState<MetricsData | null>(null);
  const [loading, setLoading] = useState(true);
  
  // Hash Ring Debugger States
  const [debugPrefix, setDebugPrefix] = useState("");
  const [debugResult, setDebugResult] = useState<DebugData | null>(null);
  const [debugLoading, setDebugLoading] = useState(false);
  const [debugError, setDebugError] = useState("");

  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch metrics on mount and when trigger updates
  const fetchMetrics = async () => {
    try {
      const res = await fetch(`${API_URL}/metrics`);
      if (!res.ok) throw new Error("HTTP error");
      const data = await res.json();
      setMetrics(data);
    } catch (err) {
      console.error("Fetch metrics error:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
    
    // Poll metrics every 3 seconds for real-time dashboard updates
    const interval = setInterval(fetchMetrics, 3000);
    return () => clearInterval(interval);
  }, [refreshTrigger, API_URL]);

  // Resolve prefix cache routing on the Consistent Hashing Ring
  const handleDebugResolve = async (e: React.FormEvent) => {
    e.preventDefault();
    const prefix = debugPrefix.trim().lower();
    if (!prefix) return;

    setDebugLoading(true);
    setDebugError("");
    setDebugResult(null);

    try {
      const res = await fetch(`${API_URL}/cache/debug?prefix=${encodeURIComponent(prefix)}`);
      if (!res.ok) throw new Error("Prefix lookup failed");
      const data = await res.json();
      setDebugResult(data);
    } catch (err) {
      console.error("Debug resolve error:", err);
      setDebugError("Failed to route prefix. Check if backend is active.");
    } finally {
      setDebugLoading(false);
    }
  };

  if (loading || !metrics) {
    return (
      <div className="flex justify-center items-center py-20 w-full">
        <div className="flex flex-col items-center gap-3">
          <span className="animate-spin rounded-full h-9 w-9 border-2 border-zinc-700 border-t-violet-500" />
          <span className="text-sm text-zinc-500">Loading system metrics dashboard...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="w-full space-y-6">
      
      {/* 1. Core KPIs Top Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* KPI 1: Suggest cache hit rate */}
        <div className="glow-card p-5 bg-zinc-900/40 border border-zinc-800 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400">Suggest Cache Hit Rate</span>
          <div className="flex items-baseline gap-2 mt-3">
            <span className="text-3xl font-extrabold text-white font-mono">
              {metrics.suggest_metrics.cache_hit_rate_percentage}%
            </span>
            <span className="text-xs text-zinc-500">hits/misses</span>
          </div>
          <div className="w-full bg-zinc-950 h-1.5 rounded-full mt-4 overflow-hidden border border-zinc-900">
            <div
              className="bg-violet-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${metrics.suggest_metrics.cache_hit_rate_percentage}%` }}
            />
          </div>
        </div>

        {/* KPI 2: Batch Writes Reduction */}
        <div className="glow-card p-5 bg-zinc-900/40 border border-zinc-800 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400">Batch Write Reduction</span>
          <div className="flex items-baseline gap-2 mt-3">
            <span className="text-3xl font-extrabold text-emerald-400 font-mono">
              {metrics.database_metrics.batch_write_reduction_percentage}%
            </span>
            <span className="text-xs text-zinc-500">writes saved</span>
          </div>
          <div className="w-full bg-zinc-950 h-1.5 rounded-full mt-4 overflow-hidden border border-zinc-900">
            <div
              className="bg-emerald-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${metrics.database_metrics.batch_write_reduction_percentage}%` }}
            />
          </div>
        </div>

        {/* KPI 3: P95 Latency */}
        <div className="glow-card p-5 bg-zinc-900/40 border border-zinc-800 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400">Suggest Latency (P95)</span>
          <div className="flex items-baseline gap-2 mt-3">
            <span className={`text-3xl font-extrabold font-mono ${
              metrics.suggest_metrics.latency_ms.p95 < 15 ? "text-cyan-400" : "text-amber-400"
            }`}>
              {metrics.suggest_metrics.latency_ms.p95} <span className="text-sm">ms</span>
            </span>
            <span className="text-xs text-zinc-500">P50: {metrics.suggest_metrics.latency_ms.p50}ms</span>
          </div>
          <div className="text-[11px] text-zinc-500 mt-4 flex justify-between items-center">
            <span>Avg: {metrics.suggest_metrics.latency_ms.avg}ms</span>
            <span className="text-cyan-400 font-semibold bg-cyan-950/30 px-1.5 py-0.5 rounded border border-cyan-800/20">Fast</span>
          </div>
        </div>

        {/* KPI 4: Pending Queue */}
        <div className="glow-card p-5 bg-zinc-900/40 border border-zinc-800 rounded-2xl flex flex-col justify-between">
          <span className="text-xs font-semibold text-zinc-400">Pending Write Queue</span>
          <div className="flex items-baseline gap-2 mt-3">
            <span className={`text-3xl font-extrabold font-mono ${
              metrics.queue_metrics.background_queue_length > 0 ? "text-amber-400" : "text-zinc-400"
            }`}>
              {metrics.queue_metrics.background_queue_length}
            </span>
            <span className="text-xs text-zinc-500">buffered searches</span>
          </div>
          <div className="text-[11px] text-zinc-500 mt-4 flex justify-between items-center">
            <span>Aggregating writes...</span>
            {metrics.queue_metrics.background_queue_length > 0 ? (
              <span className="text-xs text-amber-400 flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-400 animate-ping" />
                Active Buffer
              </span>
            ) : (
              <span className="text-zinc-650">Idle</span>
            )}
          </div>
        </div>
      </div>

      {/* 2. Middle Row: Sharding vs Database stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        
        {/* Consistent Hash Ring Cache Nodes Status */}
        <div className="glow-card p-6 bg-zinc-900/40 border border-zinc-800 rounded-2xl">
          <h3 className="text-md font-bold text-white mb-2 flex items-center gap-2">
            <span className="text-violet-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10" />
              </svg>
            </span>
            Consistent Hashing Shards
          </h3>
          <p className="text-xs text-zinc-500 mb-4">Cache routing mapped via application-level hash ring</p>

          <div className="space-y-4">
            {Object.entries(metrics.redis_metrics.nodes_health).map(([node, details]) => {
              const isHealthy = details.status === "healthy";
              const replicas = metrics.redis_metrics.ring_distribution[node] || 0;
              return (
                <div key={node} className="p-4 bg-zinc-950/60 border border-zinc-850 rounded-xl flex items-center justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <span className={`w-2.5 h-2.5 rounded-full ${isHealthy ? "bg-emerald-400 animate-pulse" : "bg-rose-500"}`} />
                      <span className="font-semibold text-sm text-zinc-200">{node}</span>
                      <span className="text-[10px] text-zinc-500 bg-zinc-900 px-1.5 py-0.5 rounded border border-zinc-800/80">
                        {replicas} Virtual Replicas
                      </span>
                    </div>
                    <p className="text-xs text-zinc-500 mt-1">Logical caching node instance</p>
                  </div>
                  <div className="text-right">
                    <span className="font-mono text-sm text-violet-300 font-semibold">{details.cached_keys}</span>
                    <span className="text-[10px] text-zinc-500 block">cached queries</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* SQL Database writes and Batch flushes */}
        <div className="glow-card p-6 bg-zinc-900/40 border border-zinc-800 rounded-2xl">
          <h3 className="text-md font-bold text-white mb-2 flex items-center gap-2">
            <span className="text-violet-400">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 7v10c0 2.21 3.58 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.58 4 8 4s8-1.79 8-4M4 7c0-2.21 3.58-4 8-4s8 1.79 8 4m0 5c0 2.21-3.58 4-8 4s-8-1.79-8-4" />
              </svg>
            </span>
            Database & Write Buffering
          </h3>
          <p className="text-xs text-zinc-500 mb-4">Relational write operations and buffer performance stats</p>

          <div className="grid grid-cols-2 gap-4">
            <div className="p-3 bg-zinc-950/60 border border-zinc-850 rounded-xl text-center">
              <span className="text-xs text-zinc-500 block">Total Queries in DB</span>
              <span className="text-lg font-bold text-white font-mono">{metrics.database_metrics.total_queries_in_db.toLocaleString()}</span>
            </div>
            
            <div className="p-3 bg-zinc-950/60 border border-zinc-850 rounded-xl text-center">
              <span className="text-xs text-zinc-500 block">Database Reads</span>
              <span className="text-lg font-bold text-white font-mono">{metrics.database_metrics.db_reads}</span>
            </div>
            
            <div className="p-3 bg-zinc-950/60 border border-zinc-850 rounded-xl text-center">
              <span className="text-xs text-zinc-500 block">Database Writes</span>
              <span className="text-lg font-bold text-white font-mono">{metrics.database_metrics.db_writes}</span>
            </div>
            
            <div className="p-3 bg-zinc-950/60 border border-zinc-850 rounded-xl text-center">
              <span className="text-xs text-zinc-500 block">Batch Flush Count</span>
              <span className="text-lg font-bold text-white font-mono">{metrics.database_metrics.flush_count}</span>
            </div>
          </div>
          
          <div className="mt-4 p-3 bg-zinc-950/60 border border-zinc-850 rounded-xl flex items-center justify-between">
            <div>
              <span className="text-xs font-semibold text-zinc-300">Average Flush Batch Size</span>
              <p className="text-[10px] text-zinc-500 mt-0.5">Average count of aggregated searches flushed together</p>
            </div>
            <span className="text-sm font-bold text-emerald-400 font-mono">
              {metrics.database_metrics.average_batch_size} <span className="text-xs text-zinc-500">queries</span>
            </span>
          </div>
        </div>

      </div>

      {/* 3. Bottom Row: Consistent Hashing Ring Interactive Debugger */}
      <div className="glow-card p-6 bg-zinc-900/40 border border-zinc-800 rounded-2xl">
        <h3 className="text-md font-bold text-white mb-2 flex items-center gap-2">
          <span className="text-violet-400">
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4" />
            </svg>
          </span>
          Consistent Hashing Ring Resolver
        </h3>
        <p className="text-xs text-zinc-500 mb-4">Input any prefix to watch how the Consistent Hash Ring maps the key to a specific cache server</p>

        <form onSubmit={handleDebugResolve} className="flex gap-3 mb-5">
          <input
            type="text"
            className="flex-1 bg-zinc-950 border border-zinc-800 hover:border-zinc-700 focus:border-violet-500 rounded-lg px-4 py-2 text-sm text-white placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-violet-500"
            placeholder="E.g., iph, py, weather, c++"
            value={debugPrefix}
            onChange={(e) => setDebugPrefix(e.target.value)}
          />
          <button
            type="submit"
            disabled={debugLoading || !debugPrefix.trim()}
            className="bg-violet-900/50 hover:bg-violet-900 border border-violet-850 hover:border-violet-700 disabled:bg-zinc-850 disabled:border-zinc-900 disabled:text-zinc-650 px-5 py-2 rounded-lg text-sm text-violet-300 font-semibold cursor-pointer select-none transition-all duration-150 flex items-center gap-2"
          >
            {debugLoading && (
              <span className="animate-spin rounded-full h-3.5 w-3.5 border-2 border-zinc-400 border-t-violet-500" />
            )}
            Resolve Node
          </button>
        </form>

        {debugError && (
          <div className="text-sm text-rose-500 mb-4">{debugError}</div>
        )}

        {debugResult && (
          <div className="bg-zinc-950/60 border border-zinc-850 rounded-xl p-5 space-y-4 animate-slide-down">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Key SHA-256 Hash</span>
                <span className="font-mono text-[13px] text-zinc-300 font-bold">{debugResult.hash_value}</span>
              </div>
              
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Assigned Redis Server</span>
                <span className="text-[13px] text-violet-400 font-bold flex items-center gap-1.5 mt-0.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                  {debugResult.assigned_node}
                </span>
              </div>

              <div>
                <span className="text-[10px] text-zinc-500 uppercase block">Cache Status</span>
                {debugResult.cache_hit ? (
                  <span className="text-xs font-bold text-emerald-400 bg-emerald-950/40 px-2 py-0.5 rounded border border-emerald-800/30">
                    HIT
                  </span>
                ) : (
                  <span className="text-xs font-bold text-amber-500 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/30">
                    MISS (DB Fallback)
                  </span>
                )}
              </div>
            </div>

            {debugResult.suggestions.length > 0 && (
              <div>
                <span className="text-[10px] text-zinc-500 uppercase block mb-1.5">Suggestions Currently Cached</span>
                <div className="flex flex-wrap gap-2">
                  {debugResult.suggestions.map((item, index) => (
                    <span key={index} className="text-xs bg-zinc-900 text-zinc-300 border border-zinc-800 px-2.5 py-1 rounded-md">
                      {item.query} <strong className="text-zinc-500 ml-1">({item.count})</strong>
                    </span>
                  ))}
                </div>
              </div>
            )}
            
            <p className="text-[11px] text-zinc-500 italic leading-relaxed pt-1.5 border-t border-zinc-900">
              Hashing explanation: The key <code>suggest:basic:{debugResult.prefix}</code> has a 32-bit hash value of <code>{debugResult.hash_value}</code>. 
              The consistent hash ring checks the virtual nodes of all physical hosts clockwise. The first node on the ring with a hash value $\ge$ <code>{debugResult.hash_value}</code> is a virtual node of <strong>{debugResult.assigned_node}</strong>, routing the request there.
            </p>
          </div>
        )}
      </div>

    </div>
  );
}
