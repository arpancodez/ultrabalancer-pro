"""Circuit Breaker Pattern Implementation.

Provides fault tolerance by preventing cascading failures when backends become
unhealthy. The circuit breaker monitors failure rates and can temporarily block
requests to failing backends, allowing them time to recover.

Author: UltraBalancer Team
Version: 1.0.0
"""

import time
import threading
from enum import Enum
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass


class CircuitState(Enum):
    """States of the circuit breaker."""
    CLOSED = "closed"  # Normal operation, requests pass through
    OPEN = "open"  # Circuit broken, requests blocked
    HALF_OPEN = "half_open"  # Testing if backend has recovered


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker behavior."""
    failure_threshold: int = 5  # Failures before opening circuit
    success_threshold: int = 2  # Successes in half-open before closing
    timeout: float = 60.0  # Seconds before trying half-open
    window_size: int = 10  # Number of recent calls to track


class CircuitBreaker:
    """Circuit breaker for protecting against cascading failures."""

    def __init__(self, backend_id: str, config: Optional[CircuitBreakerConfig] = None):
        """Initialize circuit breaker for a specific backend.
        
        Args:
            backend_id: Identifier for the backend being protected
            config: Circuit breaker configuration
        """
        self.backend_id = backend_id
        self.config = config or CircuitBreakerConfig()
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = 0.0
        self.call_history: list[bool] = []  # True for success, False for failure
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_calls": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "rejected_calls": 0,
            "state_changes": 0
        }

    def _change_state(self, new_state: CircuitState) -> None:
        """Change circuit breaker state.
        
        Args:
            new_state: New state to transition to
        """
        if self.state != new_state:
            print(f"Circuit breaker for {self.backend_id}: {self.state.value} -> {new_state.value}")
            self.state = new_state
            self.stats["state_changes"] += 1
            
            if new_state == CircuitState.OPEN:
                self.last_failure_time = time.time()
            elif new_state == CircuitState.CLOSED:
                self.failure_count = 0
                self.success_count = 0
                self.call_history.clear()

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset.
        
        Returns:
            True if circuit breaker should try half-open state
        """
        if self.state != CircuitState.OPEN:
            return False
        
        time_since_failure = time.time() - self.last_failure_time
        return time_since_failure >= self.config.timeout

    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Positional arguments for function
            **kwargs: Keyword arguments for function
            
        Returns:
            Result of function call
            
        Raises:
            Exception: If circuit is open or function fails
        """
        with self.lock:
            self.stats["total_calls"] += 1
            
            # Check if we should attempt reset
            if self._should_attempt_reset():
                self._change_state(CircuitState.HALF_OPEN)
            
            # Reject calls if circuit is open
            if self.state == CircuitState.OPEN:
                self.stats["rejected_calls"] += 1
                raise Exception(f"Circuit breaker is OPEN for {self.backend_id}")
        
        # Execute the function
        try:
            result = func(*args, **kwargs)
            self._record_success()
            return result
        except Exception as e:
            self._record_failure()
            raise e

    def _record_success(self) -> None:
        """Record a successful call."""
        with self.lock:
            self.stats["successful_calls"] += 1
            self.call_history.append(True)
            
            # Trim history to window size
            if len(self.call_history) > self.config.window_size:
                self.call_history.pop(0)
            
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.config.success_threshold:
                    self._change_state(CircuitState.CLOSED)
            elif self.state == CircuitState.CLOSED:
                # Reset failure count on success
                self.failure_count = 0

    def _record_failure(self) -> None:
        """Record a failed call."""
        with self.lock:
            self.stats["failed_calls"] += 1
            self.call_history.append(False)
            
            # Trim history to window size
            if len(self.call_history) > self.config.window_size:
                self.call_history.pop(0)
            
            self.failure_count += 1
            
            # Check if we should open the circuit
            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open immediately opens circuit
                self._change_state(CircuitState.OPEN)
            elif self.failure_count >= self.config.failure_threshold:
                self._change_state(CircuitState.OPEN)

    def get_state(self) -> CircuitState:
        """Get current circuit breaker state."""
        with self.lock:
            return self.state

    def is_available(self) -> bool:
        """Check if requests can pass through.
        
        Returns:
            True if circuit is closed or half-open
        """
        with self.lock:
            if self._should_attempt_reset():
                return True
            return self.state != CircuitState.OPEN

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state."""
        with self.lock:
            self._change_state(CircuitState.CLOSED)

    def get_stats(self) -> Dict:
        """Get circuit breaker statistics."""
        with self.lock:
            failure_rate = (
                self.stats["failed_calls"] / self.stats["total_calls"] * 100
                if self.stats["total_calls"] > 0 else 0
            )
            
            return {
                "backend_id": self.backend_id,
                "state": self.state.value,
                "total_calls": self.stats["total_calls"],
                "successful_calls": self.stats["successful_calls"],
                "failed_calls": self.stats["failed_calls"],
                "rejected_calls": self.stats["rejected_calls"],
                "failure_rate": f"{failure_rate:.2f}%",
                "current_failure_count": self.failure_count,
                "state_changes": self.stats["state_changes"],
                "config": {
                    "failure_threshold": self.config.failure_threshold,
                    "success_threshold": self.config.success_threshold,
                    "timeout": self.config.timeout
                }
            }
