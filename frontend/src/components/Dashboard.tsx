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
    nodes_health: Record<string, { status: string; cached_keys: number }>;
    ring_distribution: Record<string, number>;
  };
  queue_metrics: {
    background_queue_length: number;
  };
}

interface DebugData {
  key: string;
  hash: string;
  assigned_node: string;
  virtual_node: string;
  cache_hit: boolean;
  cache_status: string;
  ttl: number;
  suggestions: { query: string; count: number; score: number }[];
  ring_distribution: Record<string, string>;
  hash_distribution_percentage: Record<string, number>;
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
    const prefix = debugPrefix.trim().toLowerCase();
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

        {debugResult && (() => {
          const keyHashInt = parseInt(debugResult.hash, 16);
          const activeNodeAngle = isNaN(keyHashInt) ? null : (keyHashInt / 0xFFFFFFFF) * 2 * Math.PI - Math.PI / 2;
          const highlightedNode = debugResult.assigned_node.split(":")[0];

          return (
            <div className="bg-zinc-950/60 border border-zinc-850 rounded-xl p-5 space-y-5 animate-slide-down">
              <div className="flex flex-col lg:flex-row gap-6 items-center">
                
                {/* Left Column: Consistent Hash Ring Diagram */}
                <div className="flex flex-col items-center p-4 bg-zinc-950/60 border border-zinc-850 rounded-xl w-full lg:w-72">
                  <span className="text-[11px] font-bold text-zinc-400 mb-3 uppercase tracking-wider">Dynamic Hashing Uniformity</span>
                  <div className="w-full flex justify-between text-[10px] text-zinc-500 mb-4 font-mono">
                    {Object.entries(debugResult.hash_distribution_percentage).map(([node, pct]) => {
                      const nodeShort = node.split(":")[0];
                      const isActive = highlightedNode === nodeShort;
                      return (
                        <div key={node} className={`px-2 py-0.5 rounded border ${
                          isActive 
                            ? "text-violet-300 bg-violet-950/40 border-violet-800/40 font-bold" 
                            : "border-zinc-900 bg-zinc-950"
                        }`}>
                          {nodeShort}: {pct}%
                        </div>
                      );
                    })}
                  </div>

                  <svg viewBox="0 0 300 300" className="w-56 h-56">
                    {/* Hashing circle ring */}
                    <circle cx="150" cy="150" r="90" fill="none" stroke="#27272a" strokeWidth="4" />
                    
                    {/* Render virtual node replicas */}
                    {Array.from({ length: 60 }).map((_, i) => {
                      const angle = (i * 360) / 60;
                      const rad = (angle * Math.PI) / 180;
                      const x = 150 + 90 * Math.cos(rad);
                      const y = 150 + 90 * Math.sin(rad);
                      return <circle key={i} cx={x} cy={y} r="1.5" fill="#52525b" opacity="0.6" />;
                    })}

                    {/* Active key position pointer line */}
                    {activeNodeAngle !== null && (
                      <>
                        <line 
                          x1="150" y1="150" 
                          x2={150 + 90 * Math.cos(activeNodeAngle)} 
                          y2={150 + 90 * Math.sin(activeNodeAngle)} 
                          stroke="#8b5cf6" strokeWidth="2.5" strokeDasharray="3,3"
                        />
                        <circle 
                          cx={150 + 90 * Math.cos(activeNodeAngle)} 
                          cy={150 + 90 * Math.sin(activeNodeAngle)} 
                          r="6" fill="#a78bfa" 
                        />
                        <line 
                          x1="150" y1="150" 
                          x2={150 + 90 * Math.cos(activeNodeAngle)} 
                          y2={150 + 90 * Math.sin(activeNodeAngle)} 
                          stroke="#8b5cf6" strokeWidth="6" opacity="0.25"
                        />
                      </>
                    )}

                    {/* Node 1: Top (redis-1) */}
                    <g>
                      <circle 
                        cx="150" cy="60" r="18" 
                        fill={highlightedNode === "redis-1" ? "#4c1d95" : "#09090b"} 
                        stroke={highlightedNode === "redis-1" ? "#a78bfa" : "#27272a"} 
                        strokeWidth="2.5"
                      />
                      <text x="150" y="64" fill="#fff" fontSize="9" textAnchor="middle" fontWeight="bold">R1</text>
                    </g>

                    {/* Node 2: Bottom Right (redis-2) */}
                    <g>
                      <circle 
                        cx="228" cy="195" r="18" 
                        fill={highlightedNode === "redis-2" ? "#4c1d95" : "#09090b"} 
                        stroke={highlightedNode === "redis-2" ? "#a78bfa" : "#27272a"} 
                        strokeWidth="2.5"
                      />
                      <text x="228" y="199" fill="#fff" fontSize="9" textAnchor="middle" fontWeight="bold">R2</text>
                    </g>

                    {/* Node 3: Bottom Left (redis-3) */}
                    <g>
                      <circle 
                        cx="72" cy="195" r="18" 
                        fill={highlightedNode === "redis-3" ? "#4c1d95" : "#09090b"} 
                        stroke={highlightedNode === "redis-3" ? "#a78bfa" : "#27272a"} 
                        strokeWidth="2.5"
                      />
                      <text x="72" y="199" fill="#fff" fontSize="9" textAnchor="middle" fontWeight="bold">R3</text>
                    </g>

                    {/* Ring Center */}
                    <circle cx="150" cy="150" r="22" fill="#09090b" stroke="#27272a" strokeWidth="1" />
                    <text x="150" y="153" fill="#a78bfa" fontSize="8" textAnchor="middle" fontWeight="extrabold">RING</text>
                  </svg>
                </div>

                {/* Right Column: Routing Metadata details */}
                <div className="flex-1 space-y-4 w-full">
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                    <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl">
                      <span className="text-[10px] text-zinc-500 uppercase font-semibold block">Current Prefix</span>
                      <span className="font-bold text-sm text-zinc-200 mt-1 block">"{debugPrefix}"</span>
                    </div>

                    <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl">
                      <span className="text-[10px] text-zinc-500 uppercase font-semibold block">Cache Key</span>
                      <span className="font-mono text-xs text-violet-300 font-bold mt-1 block truncate" title={debugResult.key}>
                        {debugResult.key}
                      </span>
                    </div>

                    <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl">
                      <span className="text-[10px] text-zinc-500 uppercase font-semibold block">SHA-256 Key Hash</span>
                      <span className="font-mono text-xs text-cyan-400 font-bold mt-1 block">
                        {debugResult.hash}
                      </span>
                    </div>

                    <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl">
                      <span className="text-[10px] text-zinc-500 uppercase font-semibold block">Cache Status</span>
                      <div className="mt-1 flex items-center">
                        <span className={`text-xs font-extrabold px-2.5 py-0.5 rounded border ${
                          debugResult.cache_status === "HIT"
                            ? "text-emerald-400 bg-emerald-950/40 border-emerald-800/30"
                            : "text-amber-500 bg-amber-950/40 border-amber-800/30"
                        }`}>
                          {debugResult.cache_status}
                        </span>
                      </div>
                    </div>

                    <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl">
                      <span className="text-[10px] text-zinc-500 uppercase font-semibold block">Assigned Redis Node</span>
                      <span className="text-xs text-zinc-300 font-bold mt-1 block flex items-center gap-1.5">
                        <span className="w-1.5 h-1.5 rounded-full bg-violet-400 animate-pulse" />
                        {debugResult.assigned_node}
                      </span>
                    </div>

                    <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl">
                      <span className="text-[10px] text-zinc-500 uppercase font-semibold block">Virtual Node Replica</span>
                      <span className="font-mono text-xs text-zinc-400 mt-1 block truncate" title={debugResult.virtual_node}>
                        {debugResult.virtual_node}
                      </span>
                    </div>
                  </div>

                  <div className="p-3.5 bg-zinc-950/80 border border-zinc-850 rounded-xl flex items-center justify-between">
                    <span className="text-[10px] text-zinc-500 uppercase font-semibold">Cache TTL (seconds remaining)</span>
                    <span className="font-mono text-sm text-cyan-400 font-extrabold">
                      {debugResult.ttl === -2 ? "N/A (MISS)" : debugResult.ttl === -1 ? "Infinite" : `${debugResult.ttl}s`}
                    </span>
                  </div>
                </div>

              </div>

              {debugResult.suggestions.length > 0 && (
                <div className="pt-2">
                  <span className="text-[10px] text-zinc-500 uppercase font-semibold block mb-2">Suggestions Currently Cached</span>
                  <div className="flex flex-wrap gap-2">
                    {debugResult.suggestions.map((item, index) => (
                      <span key={index} className="text-xs bg-zinc-900 text-zinc-300 border border-zinc-800 px-3 py-1.5 rounded-lg">
                        {item.query} <strong className="text-zinc-500 ml-1">({item.count})</strong>
                      </span>
                    ))}
                  </div>
                </div>
              )}
              
              <p className="text-[11px] text-zinc-500 italic leading-relaxed pt-3 border-t border-zinc-900">
                Hashing explanation: The key <code>{debugResult.key}</code> maps to the hexadecimal hash value <code>{debugResult.hash}</code>. 
                The hash ring checks virtual replica nodes clockwise. The first replica node satisfying <code>hash(replica) &gt;= {debugResult.hash}</code> is <strong>{debugResult.virtual_node}</strong> (belonging to host <strong>{debugResult.assigned_node}</strong>), which resolves this query cache location.
              </p>
            </div>
          );
        })()}
      </div>

    </div>
  );
}
