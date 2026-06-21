import pytest
from app.consistent_hashing import ConsistentHashRing

def test_hash_ring_initialization():
    nodes = ["redis-1:6379", "redis-2:6379", "redis-3:6379"]
    # Initialize with 10 replicas per physical node
    ring = ConsistentHashRing(nodes=nodes, replica_count=10)
    
    # Verify virtual nodes creation (10 * 3 = 30)
    assert len(ring.ring) == 30
    assert len(ring.sorted_keys) == 30
    assert "redis-1:6379" in ring.redis_clients
    assert "redis-2:6379" in ring.redis_clients
    assert "redis-3:6379" in ring.redis_clients

def test_hash_ring_routing_consistency():
    nodes = ["redis-1:6379", "redis-2:6379", "redis-3:6379"]
    ring = ConsistentHashRing(nodes=nodes, replica_count=50)
    
    # Multiple lookups for the same key should resolve to the same node deterministically
    node1, hash1 = ring.get_node("iphone charger")
    node2, hash2 = ring.get_node("iphone charger")
    
    assert node1 == node2
    assert hash1 == hash2
    assert node1 in nodes

def test_hash_ring_node_removal_failover():
    nodes = ["redis-1:6379", "redis-2:6379", "redis-3:6379"]
    ring = ConsistentHashRing(nodes=nodes, replica_count=20)
    
    # Resolve node for a target query prefix
    target_prefix = "python roadmap"
    primary_node, _ = ring.get_node(target_prefix)
    
    # Remove that specific node from the ring
    ring.remove_node(primary_node)
    
    assert primary_node not in ring.redis_clients
    assert len(ring.ring) == 40  # 60 - 20 = 40
    
    # Query should route to one of the remaining active hosts
    fallback_node, _ = ring.get_node(target_prefix)
    assert fallback_node != primary_node
    assert fallback_node in ring.redis_clients.keys()
