"use client";

import React, { useState } from "react";
import SearchBar from "../components/SearchBar";
import TrendingWidget from "../components/TrendingWidget";
import Dashboard from "../components/Dashboard";

export default function Home() {
  const [mode, setMode] = useState<"basic" | "enhanced">("basic");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [searchKey, setSearchKey] = useState(0); // Used to force-reset SearchBar query
  const [preloadedQuery, setPreloadedQuery] = useState("");
  const [showDevTools, setShowDevTools] = useState(false);

  // Triggered when a search is successfully submitted
  const handleSearchSubmitted = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  // Triggered when a trending keyword is clicked
  const handleTrendingItemClick = (query: string) => {
    setPreloadedQuery(query);
    setSearchKey((prev) => prev + 1);
  };

  return (
    <main className="min-h-screen bg-glow-gradient px-4 py-12 sm:px-6 lg:px-8 transition-all duration-350">
      
      {/* Title Header */}
      <header className="max-w-4xl mx-auto text-center mb-10">
        <div className="inline-flex items-center gap-2.5 px-3.5 py-1 bg-violet-950/40 border border-violet-850 rounded-full text-xs font-semibold text-violet-300 mb-5 animate-slide-down">
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          Search Typeahead & Distributed Caching System
        </div>
        <h1 className="text-5xl sm:text-6xl font-extrabold tracking-tight text-white mb-3 animate-slide-down">
          Prefix<span className="text-violet-400">IQ</span>
        </h1>
        <p className="text-base sm:text-lg text-zinc-400 max-w-xl mx-auto leading-relaxed animate-slide-down">
          A production-inspired, ultra-fast Search Typeahead System backed by sharded 
          distributed caching, batch write buffering, and recency-decay trending algorithms.
        </p>
      </header>

      {/* Main Workspace */}
      <div className="max-w-4xl mx-auto space-y-6">
        
        {/* Row 1: Search Bar Input (Dominant Component with z-40 to stack above items below) */}
        <section className="relative z-40 glow-card p-8 sm:p-10 bg-zinc-900/40 border border-zinc-800 rounded-3xl shadow-xl transition-all duration-200">
          <div className="text-center mb-8">
            <h2 className="text-xl font-bold text-white tracking-wide">Search Autocomplete Engine</h2>
            <p className="text-xs text-zinc-400 mt-1 max-w-md mx-auto">
              Start typing below to see suggestions routed across Redis shards via Consistent Hashing. Press Enter to submit.
            </p>
          </div>
          
          <SearchBar
            key={`${searchKey}-${mode}`}
            mode={mode}
            onSearchSubmitted={handleSearchSubmitted}
            initialQuery={preloadedQuery}
          />
        </section>

        {/* Row 2: Trending Searches (directly below the search component with z-30) */}
        <section className="relative z-30 w-full">
          <TrendingWidget
            mode={mode}
            setMode={setMode}
            onItemClick={handleTrendingItemClick}
            refreshTrigger={refreshTrigger}
          />
        </section>

        {/* Progressive Disclosure Section for System Diagnostics */}
        <section className="relative z-20 pt-6 border-t border-zinc-900">
          <div className="flex justify-center mb-6">
            <button
              onClick={() => setShowDevTools((prev) => !prev)}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-zinc-900/60 hover:bg-zinc-850 border border-zinc-800 hover:border-zinc-700 rounded-full text-xs font-bold text-zinc-300 hover:text-white cursor-pointer select-none transition-all duration-150 shadow-md"
            >
              <span className="text-violet-400">
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  {showDevTools ? (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                  ) : (
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9 5l7 7-7 7" />
                  )}
                </svg>
              </span>
              {showDevTools ? "Hide System Diagnostics" : "Show System Diagnostics"}
            </button>
          </div>

          {showDevTools && (
            <div className="space-y-6 animate-slide-down">
              {/* Progressive Disclosure UX Explanation */}
              <div className="p-4.5 bg-violet-950/20 border border-violet-900/30 rounded-2xl text-xs text-violet-300 leading-relaxed shadow-sm">
                💡 <strong>Progressive Disclosure of Engineering Features</strong>: The application follows the principle of progressive disclosure. The primary user workflow (search) is immediately visible, while engineering diagnostics, distributed sharding rings, and performance metrics are available on demand below without distracting from the core typeahead experience.
              </div>

              {/* Diagnostics Grid (Demonstration Guide + Metrics Dashboard) */}
              <div className="grid grid-cols-1 gap-6">
                
                {/* Quick System Demonstration Guide */}
                <div className="glow-card p-6 bg-zinc-900/40 border border-zinc-800 rounded-2xl">
                  <h3 className="text-sm font-bold text-white mb-3 flex items-center gap-1.5">
                    <span className="text-violet-400">
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                      </svg>
                    </span>
                    System Demonstration Guide
                  </h3>
                  <p className="text-xs text-zinc-400 leading-relaxed mb-4">
                    Verify implementation mechanisms visually:
                  </p>
                  
                  <ul className="text-xs text-zinc-500 space-y-2">
                    <li className="flex gap-2">
                      <span className="text-violet-400">✓</span>
                      <span>
                        <strong>Consistent Hashing Routing</strong>: Resolve different prefixes (e.g. <code>iph</code> vs <code>rust</code>) in the Resolver below. Observe which of the three Redis physical nodes receives the key.
                      </span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-violet-400">✓</span>
                      <span>
                        <strong>Asynchronous Write Buffering</strong>: Submit multiple searches quickly. Watch the dashboard's <em>Pending Write Queue</em> increment, then flush to PostgreSQL, showing write reduction metrics.
                      </span>
                    </li>
                    <li className="flex gap-2">
                      <span className="text-violet-400">✓</span>
                      <span>
                        <strong>Recency-decay Spikes</strong>: Toggle <em>Enhanced</em> mode on Trending Widget. Watch recent search activity logs bubble spike queries like <code>chatgpt 5 release date</code> to the top!
                      </span>
                    </li>
                  </ul>
                </div>

                {/* Live System Metrics Dashboard (KPIs, nodes health, consistent hash ring drawer) */}
                <div className="pt-2">
                  <div className="mb-4">
                    <h3 className="text-md font-bold text-white">Live System Observability</h3>
                    <p className="text-xs text-zinc-500 mt-0.5">Real-time cache performance, write aggregated states, and database logs</p>
                  </div>
                  <Dashboard refreshTrigger={refreshTrigger} />
                </div>

              </div>
            </div>
          )}
        </section>

      </div>

      <footer className="max-w-4xl mx-auto text-center mt-16 pt-8 border-t border-zinc-900 text-xs text-zinc-650">
        <p>© 2026 PrefixIQ. Shipped with Synthetic Zipfian Benchmark Dataset. Built for System Design Demonstration.</p>
      </footer>
    </main>
  );
}
export const dynamic = 'force-dynamic';
