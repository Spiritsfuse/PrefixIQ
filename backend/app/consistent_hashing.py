import hashlib
import bisect
import logging
from typing import List, Dict, Tuple, Optional
import redis.asyncio as async_redis
from .config import settings

logger = logging.getLogger(__name__)

class ConsistentHashRing:
    def __init__(self, nodes: List[str] = None, replica_count: int = 100):
        """
        Initializes the Consistent Hash Ring.
        
        :param nodes: List of physical nodes in 'host:port' format
        :param replica_count: Number of virtual nodes (replicas) per physical node to ensure uniform key distribution
        """
        self.replica_count = replica_count
        self.ring: Dict[int, str] = {}  # Map of virtual node hash -> physical node name
        self.sorted_keys: List[int] = []  # Sorted list of virtual node hashes
        self.redis_clients: Dict[str, async_redis.Redis] = {}
        
        if nodes:
            for node in nodes:
                self.add_node(node)
                
    def _hash(self, key: str) -> int:
        """
        Hashes a key (prefix or node replica) and maps it to a 32-bit unsigned integer.
        We use SHA-256 to ensure low hash collision and high uniformity.
        """
        hash_hex = hashlib.sha256(key.encode('utf-8')).hexdigest()
        # Extract first 8 hex characters (32 bits) and convert to integer
        return int(hash_hex[:8], 16)
        
    def add_node(self, node: str):
        """
        Adds a physical node to the ring, generating virtual replicas and mapping them,
        and initializing its async Redis connection pool.
        """
        if node in self.redis_clients:
            return  # Already added
            
        host, port = node.split(":")
        # Instantiate async Redis client with decode_responses=True to handle strings directly
        self.redis_clients[node] = async_redis.Redis(
            host=host, 
            port=int(port), 
            decode_responses=True,
            socket_timeout=2.0,
            socket_connect_timeout=2.0
        )
        
        for i in range(self.replica_count):
            virtual_key = f"{node}-replica-{i}"
            val = self._hash(virtual_key)
            self.ring[val] = node
            self.sorted_keys.append(val)
            
        # Re-sort virtual node hashes to enable binary search lookups
        self.sorted_keys.sort()
        logger.info(f"[ConsistentHashRing] Added physical node: {node} with {self.replica_count} virtual replicas.")
        
    def remove_node(self, node: str):
        """
        Removes a physical node and its virtual replicas from the hash ring,
        and closes its Redis client connections.
        """
        if node not in self.redis_clients:
            return
            
        # Close connection
        client = self.redis_clients.pop(node)
        
        # Remove virtual nodes
        for i in range(self.replica_count):
            virtual_key = f"{node}-replica-{i}"
            val = self._hash(virtual_key)
            if val in self.ring:
                del self.ring[val]
                self.sorted_keys.remove(val)
                
        logger.info(f"[ConsistentHashRing] Removed physical node: {node}.")

    def get_node(self, key: str) -> Tuple[str, int]:
        """
        Maps a search prefix or cache key to its corresponding physical node in the hash ring.
        Uses binary search (bisect) for O(log N) routing complexity.
        """
        if not self.ring:
            raise ValueError("Consistent Hash Ring is empty. Cannot route keys.")
            
        key_hash = self._hash(key)
        
        # Find index of the first virtual node hash greater than or equal to key_hash
        idx = bisect.bisect_right(self.sorted_keys, key_hash)
        
        # Wrap around to the start of the ring (first element) if we hit the end
        if idx == len(self.sorted_keys):
            idx = 0
            
        assigned_hash = self.sorted_keys[idx]
        assigned_node = self.ring[assigned_hash]
        return assigned_node, key_hash

    async def get_client(self, key: str) -> Tuple[async_redis.Redis, str, str]:
        """
        Helper method to retrieve the active Redis client, physical node name,
        and the hexadecimal hash value for a search key.
        """
        node, key_hash = self.get_node(key)
        return self.redis_clients[node], node, f"{key_hash:08x}"
        
    def get_ring_distribution(self) -> Dict[str, int]:
        """
        Returns stats about virtual node distribution across physical nodes
        to verify mapping uniformity.
        """
        stats = {node: 0 for node in self.redis_clients}
        for node in self.ring.values():
            if node in stats:
                stats[node] += 1
        return stats

# Global singleton instance of the Hash Ring
ring = ConsistentHashRing(nodes=settings.redis_node_list)
