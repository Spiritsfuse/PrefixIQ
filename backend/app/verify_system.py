import urllib.request
import json
import time
import sys

API_URL = "http://localhost:8000"

def get_json(url):
    t0 = time.time()
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            latency = (time.time() - t0) * 1000
            return data, latency
    except Exception as e:
        print(f"Error requesting {url}: {e}")
        return None, 0

def post_json(url, payload):
    t0 = time.time()
    try:
        req = urllib.request.Request(
            url, 
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            latency = (time.time() - t0) * 1000
            return data, latency
    except Exception as e:
        print(f"Error posting to {url}: {e}")
        return None, 0

def run_verification():
    print("=" * 60)
    print("PREFIXIQ SYSTEM VERIFICATION")
    print("=" * 60)
    
    # 1. Verify Trending Searches Latency & Results
    print("\n[1] Verifying Trending Searches...")
    basic_trending, t_basic = get_json(f"{API_URL}/trending?mode=basic")
    if basic_trending:
        print(f"Basic Trending (Counts) - Latency: {t_basic:.2f}ms")
        for i, item in enumerate(basic_trending.get('suggestions', [])[:5]):
            print(f"  {i+1}. {item['query']} (clicks: {item['count']})")
            
    enhanced_trending, t_enhanced = get_json(f"{API_URL}/trending?mode=enhanced")
    if enhanced_trending:
        print(f"\nEnhanced Trending (Recency) - Latency: {t_enhanced:.2f}ms")
        for i, item in enumerate(enhanced_trending.get('suggestions', [])[:5]):
            print(f"  {i+1}. {item['query']} (clicks: {item['count']}, score: {item['score']:.2f})")
            
    # 2. Verify Autocomplete Suggest Pipeline
    print("\n[2] Verifying Autocomplete Prefix matching...")
    prefixes = ["a", "ap", "iph", "java", "python", "data", "machine"]
    for pref in prefixes:
        # Check cache status using cache/debug
        debug_data, _ = get_json(f"{API_URL}/cache/debug?prefix={pref}&mode=basic")
        status = debug_data.get('cache_status', 'UNKNOWN') if debug_data else 'UNKNOWN'
        assigned = debug_data.get('assigned_node', 'UNKNOWN') if debug_data else 'UNKNOWN'
        
        # Get suggestions
        sugs, t_sug = get_json(f"{API_URL}/suggest?q={pref}&mode=basic")
        count = len(sugs.get('suggestions', [])) if sugs else 0
        print(f"Prefix '{pref}': {count} suggestions returned in {t_sug:.2f}ms | Cache: {status} on {assigned}")
        
    # 3. Verify End-to-End Search count updates and Cache Invalidation
    print("\n[3] Verifying End-to-End Search Submission Flow...")
    test_prefix = f"xyzzy{int(time.time())}" # unique prefix each run
    test_query = f"{test_prefix} query"
    
    # Initial state (warm up cache as empty)
    print(f"  1. Fetch suggestions for '{test_prefix}' before search...")
    sugs_before, _ = get_json(f"{API_URL}/suggest?q={test_prefix}&mode=basic")
    print(f"     Suggestions before search: {sugs_before.get('suggestions', [])}")
    
    # Verify cache is now warmed up as empty
    debug_data, _ = get_json(f"{API_URL}/cache/debug?prefix={test_prefix}&mode=basic")
    print(f"     Cache status of '{test_prefix}': {debug_data.get('cache_status')} (TTL: {debug_data.get('ttl')}s)")
    
    # Post search
    print(f"  2. Submit POST /search for '{test_query}'...")
    post_res, t_post = post_json(f"{API_URL}/search", {"query": test_query})
    print(f"     Submitted in {t_post:.2f}ms. Response: {post_res}")
    
    # Check cache status immediately
    debug_data, _ = get_json(f"{API_URL}/cache/debug?prefix={test_prefix}&mode=basic")
    print(f"     Immediate cache status of '{test_prefix}' after search: {debug_data.get('cache_status')} (TTL: {debug_data.get('ttl')}s)")
    
    # Sleep to allow BatchWriter to flush (flush interval is 5 seconds)
    print("  3. Waiting 6 seconds for BatchWriter periodic flush to complete...")
    time.sleep(6.0)
    
    # Fetch suggestions again
    print(f"  4. Fetch suggestions for '{test_prefix}' after batch flush...")
    sugs_after, _ = get_json(f"{API_URL}/suggest?q={test_prefix}&mode=basic")
    print(f"     Suggestions after search: {sugs_after.get('suggestions', [])}")
    
    # Check if cache was invalidated and count updated
    debug_data, _ = get_json(f"{API_URL}/cache/debug?prefix={test_prefix}&mode=basic")
    print(f"     Cache status of '{test_prefix}' after flush: {debug_data.get('cache_status')} (TTL: {debug_data.get('ttl')}s)")
    
    matching_after = [s for s in sugs_after.get('suggestions', []) if s['query'] == test_query]
    if matching_after:
        print("  => SUCCESS: Search count incremented and cache successfully invalidated & refreshed!")
    else:
        print("  => FAILURE: Search count did not increment or cache was not refreshed.")

if __name__ == "__main__":
    run_verification()
