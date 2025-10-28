"""IP Hash Load Balancing Plugin.

This plugin implements IP hash algorithm for consistent client-to-backend mapping.
The same client IP will always be routed to the same backend server, enabling
session persistence without additional state management.

Author: UltraBalancer Team
Version: 1.0.0
"""

import hashlib
import threading
from typing import Dict, Optional, List


class IPHashPlugin:
    """IP Hash load balancing algorithm.
    
    Routes clients to backends based on their IP address hash, ensuring
    the same client always connects to the same backend server.
    """

    def __init__(self):
        """Initialize the IP hash plugin."""
        self.backend_cache: Dict[str, str] = {}  # IP -> backend mapping
        self.lock = threading.Lock()
        self.stats = {
            "total_requests": 0,
            "cache_hits": 0,
            "unique_clients": 0
        }

    def _hash_ip(self, client_ip: str, backend_count: int) -> int:
        """Hash client IP to a backend index.
        
        Args:
            client_ip: Client IP address
            backend_count: Number of available backends
            
        Returns:
            Backend index (0 to backend_count-1)
        """
        # Use MD5 hash for consistent distribution
        hash_obj = hashlib.md5(client_ip.encode('utf-8'))
        hash_value = int(hash_obj.hexdigest(), 16)
        return hash_value % backend_count

    def select_backend(self, backends: List[str], client_ip: str) -> Optional[str]:
        """Select backend based on client IP hash.
        
        Args:
            backends: List of available backend identifiers
            client_ip: IP address of the client making the request
            
        Returns:
            Selected backend ID or None if no backends available
        """
        if not backends:
            return None
            
        if not client_ip:
            # Fallback to first backend if no IP provided
            return backends[0]
        
        with self.lock:
            self.stats["total_requests"] += 1
            
            # Check if we have a cached mapping
            if client_ip in self.backend_cache:
                cached_backend = self.backend_cache[client_ip]
                # Verify the cached backend is still available
                if cached_backend in backends:
                    self.stats["cache_hits"] += 1
                    return cached_backend
                else:
                    # Remove stale cache entry
                    del self.backend_cache[client_ip]
            
            # Calculate new mapping
            backend_index = self._hash_ip(client_ip, len(backends))
            selected_backend = backends[backend_index]
            
            # Cache the mapping
            if client_ip not in self.backend_cache:
                self.stats["unique_clients"] += 1
            self.backend_cache[client_ip] = selected_backend
            
            return selected_backend

    def remove_backend(self, backend_id: str) -> None:
        """Remove a backend and clear associated cache entries.
        
        Args:
            backend_id: Backend identifier to remove
        """
        with self.lock:
            # Remove all cache entries pointing to this backend
            clients_to_remove = [
                ip for ip, backend in self.backend_cache.items() 
                if backend == backend_id
            ]
            for ip in clients_to_remove:
                del self.backend_cache[ip]

    def clear_cache(self) -> None:
        """Clear all cached IP-to-backend mappings."""
        with self.lock:
            self.backend_cache.clear()
            self.stats["unique_clients"] = 0

    def get_name(self) -> str:
        """Return the name of this load balancing algorithm."""
        return "ip_hash"

    def get_stats(self) -> Dict:
        """Return statistics about IP hash operations."""
        with self.lock:
            cache_hit_rate = (
                self.stats["cache_hits"] / self.stats["total_requests"] * 100
                if self.stats["total_requests"] > 0 else 0
            )
            return {
                "algorithm": self.get_name(),
                "total_requests": self.stats["total_requests"],
                "cache_hits": self.stats["cache_hits"],
                "cache_hit_rate": f"{cache_hit_rate:.2f}%",
                "unique_clients": self.stats["unique_clients"],
                "cached_mappings": len(self.backend_cache)
            }
