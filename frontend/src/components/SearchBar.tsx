import React, { useState, useEffect, useRef } from "react";
import useDebounce from "../hooks/useDebounce";

interface SuggestionItem {
  query: string;
  count: number;
  score: number;
}

interface SearchBarProps {
  mode: "basic" | "enhanced";
  onSearchSubmitted: () => void;
}

export default function SearchBar({ mode, onSearchSubmitted }: SearchBarProps) {
  const [query, setQuery] = useState("");
  const [suggestions, setSuggestions] = useState<SuggestionItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(-1);
  
  // Dummy Search Submission Results
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [searchResult, setSearchResult] = useState<string | null>(null);

  const debouncedQuery = useDebounce(query, 300);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  // Fetch suggestions when debounced query shifts
  useEffect(() => {
    async function fetchSuggestions() {
      const trimmed = debouncedQuery.trim();
      if (!trimmed) {
        setSuggestions([]);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const res = await fetch(`${API_URL}/suggest?q=${encodeURIComponent(trimmed)}&mode=${mode}`);
        if (!res.ok) throw new Error(`HTTP Error ${res.status}`);
        const data = await res.json();
        setSuggestions(data.suggestions || []);
      } catch (err: any) {
        console.error("Fetch suggest error:", err);
        setError("Failed to fetch suggestions. Backend might be down.");
      } finally {
        setLoading(false);
      }
    }

    fetchSuggestions();
  }, [debouncedQuery, mode, API_URL]);

  // Click outside listener to collapse dropdown overlay
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Keyboard navigation logic
  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!isOpen) return;

    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActiveIndex((prev) => (prev < suggestions.length - 1 ? prev + 1 : 0));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActiveIndex((prev) => (prev > 0 ? prev - 1 : suggestions.length - 1));
    } else if (e.key === "Enter") {
      e.preventDefault();
      if (activeIndex >= 0 && activeIndex < suggestions.length) {
        // Submit search with active selection
        submitSearch(suggestions[activeIndex].query);
      } else {
        // Submit what's currently typed
        submitSearch(query);
      }
    } else if (e.key === "Escape") {
      setIsOpen(false);
      setActiveIndex(-1);
    }
  };

  // Submit search request to backend
  const submitSearch = async (searchTerm: string) => {
    const trimmed = searchTerm.trim();
    if (!trimmed) return;

    setQuery(trimmed);
    setIsOpen(false);
    setActiveIndex(-1);
    setSubmittedQuery(trimmed);
    setSearchResult("loading");

    try {
      const res = await fetch(`${API_URL}/search`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: trimmed }),
      });

      if (!res.ok) throw new Error("Search submission rejected");
      
      const data = await res.json();
      setSearchResult(data.message || "Searched");
      
      // Notify parent dashboard component to refresh metrics (like queue size/database logs)
      onSearchSubmitted();
    } catch (err) {
      console.error("Search submission error:", err);
      setSearchResult("Error: Submission failed.");
    }
  };

  return (
    <div className="w-full max-w-2xl mx-auto flex flex-col items-center">
      
      {/* Search Input Container */}
      <div ref={dropdownRef} className="relative w-full z-30">
        <div className="relative flex items-center">
          <span className="absolute left-4 text-zinc-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
          
          <input
            type="text"
            className="w-full bg-zinc-900 border border-zinc-700 hover:border-zinc-500 focus:border-violet-500 rounded-xl py-3.5 pl-12 pr-12 text-white placeholder-zinc-400 focus:outline-none focus:ring-2 focus:ring-violet-500/20 transition-all duration-200"
            placeholder="Type query to get suggestions..."
            value={query}
            onChange={(e) => {
              setQuery(e.target.value);
              setIsOpen(true);
              setActiveIndex(-1);
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsOpen(true)}
          />

          {/* Spinner and Clear buttons */}
          <div className="absolute right-4 flex items-center gap-2">
            {loading && (
              <span className="animate-spin rounded-full h-5 w-5 border-2 border-zinc-400 border-t-violet-500" />
            )}
            {query && (
              <button
                onClick={() => {
                  setQuery("");
                  setSuggestions([]);
                  setIsOpen(false);
                }}
                className="text-zinc-400 hover:text-white focus:outline-none"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            )}
          </div>
        </div>

        {/* Error notification */}
        {error && (
          <div className="mt-2 text-rose-500 text-sm flex items-center gap-1.5 px-1 animate-slide-down">
            <svg className="w-4 h-4 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span>{error}</span>
          </div>
        )}

        {/* Suggestion Dropdown Overlay */}
        {isOpen && (query.trim().length > 0) && (suggestions.length > 0 || !loading) && (
          <div className="absolute w-full mt-2 glass-dropdown rounded-xl overflow-hidden shadow-2xl animate-slide-down">
            {suggestions.length === 0 ? (
              <div className="p-4 text-zinc-500 text-sm text-center">No matching suggestions found</div>
            ) : (
              <ul className="py-1">
                {suggestions.map((item, index) => (
                  <li
                    key={index}
                    onClick={() => submitSearch(item.query)}
                    className={`flex items-center justify-between px-5 py-3 cursor-pointer select-none transition-colors duration-150 ${
                      index === activeIndex
                        ? "bg-zinc-800 text-white"
                        : "text-zinc-300 hover:bg-zinc-850 hover:text-white"
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-zinc-500">
                        <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                        </svg>
                      </span>
                      <span className="font-medium text-[15px]">{item.query}</span>
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="bg-zinc-850 text-zinc-400 px-2 py-0.5 rounded border border-zinc-800">
                        count: {item.count}
                      </span>
                      {mode === "enhanced" && (
                        <span className="bg-violet-900/30 text-violet-400 px-2 py-0.5 rounded border border-violet-800/30 font-mono">
                          score: {item.score.toFixed(2)}
                        </span>
                      )}
                    </div>
                  </li>
                ))}
              </ul>
            )}
            
            {/* Legend / Keyboard Tip */}
            <div className="bg-zinc-950 px-5 py-2 text-[11px] text-zinc-500 border-t border-zinc-850 flex justify-between">
              <span>Use ↑↓ keys to select, Esc to close</span>
              <span>Mode: <strong className="text-violet-400 capitalize">{mode}</strong></span>
            </div>
          </div>
        )}
      </div>

      {/* Simulated Search Results panel */}
      {searchResult && (
        <div className="w-full mt-8 p-6 glow-card bg-zinc-900/40 border border-zinc-800 rounded-2xl animate-slide-down">
          {searchResult === "loading" ? (
            <div className="flex flex-col items-center py-6 gap-3">
              <span className="animate-spin rounded-full h-8 w-8 border-2 border-zinc-500 border-t-violet-500" />
              <span className="text-sm text-zinc-400">Executing search routing...</span>
            </div>
          ) : (
            <div>
              <div className="flex items-center justify-between border-b border-zinc-800 pb-3 mb-4">
                <h3 className="text-sm font-semibold text-zinc-400">Search Results</h3>
                <span className="text-xs text-emerald-400 bg-emerald-950/40 px-2.5 py-1 rounded-full border border-emerald-800/30 font-mono flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  API Response: "{searchResult}"
                </span>
              </div>
              
              <h2 className="text-xl font-bold text-white mb-1.5">
                Results for: <span className="text-violet-400">"{submittedQuery}"</span>
              </h2>
              
              <p className="text-sm text-zinc-400 mb-5 leading-relaxed">
                Your search has been successfully captured and routed to the backend memory buffer. 
                The asynchronous <strong>BatchWriter</strong> will aggregate this count and commit it to PostgreSQL.
              </p>
              
              {/* Mock Search Result Cards */}
              <div className="space-y-4">
                <div className="p-4 bg-zinc-950/60 border border-zinc-850 rounded-xl hover:border-zinc-700 transition-colors">
                  <span className="text-xs text-blue-400 hover:underline cursor-pointer">prefixiq.edu/{submittedQuery.replace(/\s+/g, '-')}</span>
                  <h4 className="text-[15px] font-semibold text-violet-300 mt-1 cursor-pointer hover:underline">
                    Mastering {submittedQuery}: Complete Reference Documentation
                  </h4>
                  <p className="text-xs text-zinc-500 mt-1.5 line-clamp-2">
                    Explore comprehensive articles, benchmarks, and community guides about {submittedQuery}. 
                    Includes installation tutorials, production examples, and common error fixes.
                  </p>
                </div>
                
                <div className="p-4 bg-zinc-950/60 border border-zinc-850 rounded-xl hover:border-zinc-700 transition-colors">
                  <span className="text-xs text-blue-400 hover:underline cursor-pointer">github.com/prefixiq/{submittedQuery.replace(/\s+/g, '-')}</span>
                  <h4 className="text-[15px] font-semibold text-violet-300 mt-1 cursor-pointer hover:underline">
                    GitHub - prefixiq/{submittedQuery.replace(/\s+/g, '')}
                  </h4>
                  <p className="text-xs text-zinc-500 mt-1.5 line-clamp-2">
                    Open-source template repository for {submittedQuery}. Highly optimized code samples, 
                    Docker setups, and testing frameworks ready for staging and deployment.
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

    </div>
  );
}
