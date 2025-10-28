"""Weighted Round Robin Load Balancing Plugin.

This plugin implements weighted round robin algorithm where backends can be
assigned different weights based on their capacity. Backends with higher weights
receive proportionally more requests.

Author: UltraBalancer Team
Version: 1.0.0
"""

import threading
from typing import Dict, Optional


class WeightedRoundRobinPlugin:
    """Weighted Round Robin load balancing algorithm.
    
    Distributes requests across backends based on their assigned weights.
    A backend with weight 2 receives twice as many requests as one with weight 1.
    """

    def __init__(self):
        """Initialize the weighted round robin plugin."""
        self.current_index = 0
        self.current_weight = 0
        self.max_weight = 0
        self.gcd_weight = 0
        self.backend_weights: Dict[str, int] = {}
        self.lock = threading.Lock()

    def set_backend_weight(self, backend_id: str, weight: int) -> None:
        """Set weight for a specific backend.
        
        Args:
            backend_id: Unique identifier for the backend
            weight: Weight value (higher = more requests)
        """
        if weight <= 0:
            raise ValueError("Weight must be positive")
        
        with self.lock:
            self.backend_weights[backend_id] = weight
            self._recalculate_weights()

    def _recalculate_weights(self) -> None:
        """Recalculate max weight and GCD for current backend set."""
        if not self.backend_weights:
            self.max_weight = 0
            self.gcd_weight = 0
            return
        
        weights = list(self.backend_weights.values())
        self.max_weight = max(weights)
        self.gcd_weight = self._gcd_list(weights)

    def _gcd_list(self, numbers: list) -> int:
        """Calculate GCD of a list of numbers."""
        from math import gcd
        result = numbers[0]
        for num in numbers[1:]:
            result = gcd(result, num)
        return result

    def select_backend(self, backends: list) -> Optional[str]:
        """Select next backend based on weighted round robin.
        
        Args:
            backends: List of available backend identifiers
            
        Returns:
            Selected backend ID or None if no backends available
        """
        if not backends:
            return None
        
        # Ensure all backends have weights
        for backend in backends:
            if backend not in self.backend_weights:
                self.set_backend_weight(backend, 1)  # Default weight
        
        with self.lock:
            while True:
                self.current_index = (self.current_index + 1) % len(backends)
                
                if self.current_index == 0:
                    self.current_weight = self.current_weight - self.gcd_weight
                    if self.current_weight <= 0:
                        self.current_weight = self.max_weight
                    if self.current_weight == 0:
                        return None
                
                backend = backends[self.current_index]
                if self.backend_weights.get(backend, 1) >= self.current_weight:
                    return backend

    def get_name(self) -> str:
        """Return the name of this load balancing algorithm."""
        return "weighted_round_robin"

    def get_stats(self) -> Dict:
        """Return statistics about current backend weights."""
        with self.lock:
            return {
                "algorithm": self.get_name(),
                "backend_weights": self.backend_weights.copy(),
                "max_weight": self.max_weight,
                "gcd_weight": self.gcd_weight,
                "current_index": self.current_index,
                "current_weight": self.current_weight
            }
