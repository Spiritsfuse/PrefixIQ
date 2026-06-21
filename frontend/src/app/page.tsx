"use client";

import React, { useState } from "react";
import SearchBar from "../components/SearchBar";
import TrendingWidget from "../components/TrendingWidget";
import Dashboard from "../components/Dashboard";

export default function Home() {
  const [mode, setMode] = useState<"basic" | "enhanced">("basic");
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [searchKey, setSearchKey] = useState(0); // Used to force-reset SearchBar query

  // Triggered when a search is successfully submitted
  const handleSearchSubmitted = () => {
    setRefreshTrigger((prev) => prev + 1);
  };

  // Triggered when a trending keyword is clicked
  const handleTrendingItemClick = (query: string) => {
    // We increment searchKey to tell SearchBar to update or we can just change query state
    // Let's pass it to SearchBar by force-updating the SearchBar key or similar.
    // To make it simple, we can render the SearchBar with key={searchKey} and when it resets, we pass initial value.
    // But a cleaner way is to just let the user know we set the search bar value.
    // Let's force-remount SearchBar with a preset query or pass it dynamically.
    // Let's pass a custom key to force-mount SearchBar with the query pre-filled!
    // Yes, we can keep a state variable `searchQuery` and render SearchBar with it.
    // To keep it simple, we'll remount the search bar with the clicked query:
    setPreloadedQuery(query);
    setSearchKey((prev) => prev + 1);
  };

  const [preloadedQuery, setPreloadedQuery] = useState("");

  return (
    <main className="min-h-screen bg-glow-gradient px-4 py-8 sm:px-6 lg:px-8">
      
      {/* Title Header */}
      <header className="max-w-6xl mx-auto text-center mb-10">
        <div className="inline-flex items-center gap-2.5 px-3 py-1 bg-violet-950/40 border border-violet-850 rounded-full text-xs font-semibold text-violet-300 mb-4 animate-slide-down">
          <span className="w-2 h-2 rounded-full bg-violet-400 animate-pulse" />
          System Design Project: Distributed Systems Semesters
        </div>
        <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-2 animate-slide-down">
          Prefix<span className="text-violet-400">IQ</span>
        </h1>
        <p className="text-base text-zinc-400 max-w-xl mx-auto leading-relaxed animate-slide-down">
          A production-quality Search Typeahead & Autocomplete system implementing 
          Consistent Hashing, Exponential Decay Trending, and Asynchronous Batching.
        </p>
      </header>

      {/* Main Grid Workspace */}
      <div className="max-w-6xl mx-auto space-y-8">
        
        {/* Row 1: Search Bar Input */}
        <section className="glow-card p-6 sm:p-8 bg-zinc-900/40 border border-zinc-800 rounded-3xl">
          <div className="text-center mb-6">
            <h2 className="text-lg font-bold text-white">Search Autocomplete Engine</h2>
            <p className="text-xs text-zinc-500 mt-1">
              Start typing below to see consistent-hashing routed cached suggestions. Press enter to submit.
            </p>
          </div>
          
          <SearchBar
            key={`${searchKey}-${mode}`}
            mode={mode}
            onSearchSubmitted={handleSearchSubmitted}
          />
        </section>

        {/* Row 2: Trending & Educational Helper Column */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          
          {/* Column 1: Trending Searches (w/ basic vs enhanced toggler) */}
          <div className="lg:col-span-2">
            <TrendingWidget
              mode={mode}
              setMode={setMode}
              onItemClick={handleTrendingItemClick}
              refreshTrigger={refreshTrigger}
            />
          </div>

          {/* Column 2: Quick System Viva Prep guide */}
          <div className="glow-card p-6 bg-zinc-900/40 border border-zinc-800 rounded-2xl flex flex-col justify-between">
            <div>
              <h3 className="text-md font-bold text-white mb-3 flex items-center gap-1.5">
                <span className="text-violet-400">
                  <svg className="w-4.5 h-4.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </span>
                Viva Quick Tests
              </h3>
              <p className="text-xs text-zinc-400 leading-relaxed mb-4">
                Verify implementation mechanisms visually:
              </p>
              
              <ul className="text-[11px] text-zinc-500 space-y-3">
                <li className="flex gap-2">
                  <span className="text-violet-400">✓</span>
                  <span>
                    <strong>Consistent Hashing</strong>: Type different prefixes like <code>iph</code> and <code>rust</code>, and observe the resolved Redis node sharding in the dashboard.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-violet-400">✓</span>
                  <span>
                    <strong>Batching Writes</strong>: Submit multiple searches quickly. Watch the dashboard's <em>Pending Write Queue</em> increment, then flush to DB, displaying write reduction logs.
                  </span>
                </li>
                <li className="flex gap-2">
                  <span className="text-violet-400">✓</span>
                  <span>
                    <strong>Recency-decay Spikes</strong>: Click <em>Enhanced</em> mode on Trending Widget. Watch synthetic spike queries like <code>chatgpt 5 release date</code> bubble to the top!
                  </span>
                </li>
              </ul>
            </div>

            <div className="mt-6 pt-4 border-t border-zinc-850 flex items-center justify-between text-[11px] text-zinc-500">
              <span>Architecture: <strong>Clean (DDD)</strong></span>
              <span className="text-emerald-400">System Ready</span>
            </div>
          </div>
        </section>

        {/* Row 3: Live System Metrics Dashboard */}
        <section>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-white">Live System Observability</h2>
            <p className="text-xs text-zinc-500 mt-0.5">Real-time cache performance, write aggregated states, and database logs</p>
          </div>
          <Dashboard refreshTrigger={refreshTrigger} />
        </section>

      </div>

      {/* Footer */}
      <footer className="max-w-6xl mx-auto text-center mt-16 pt-8 border-t border-zinc-900 text-xs text-zinc-650">
        <p>© 2026 PrefixIQ. Shipped with Microsoft ORCAS Dataset. Built for System Design Viva Presentation.</p>
      </footer>
    </main>
  );
}
export const dynamic = 'force-dynamic';
