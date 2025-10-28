"""Rate Limiter Implementation.

Provides rate limiting functionality to prevent backend overload and ensure
fair resource distribution. Supports multiple rate limiting algorithms including
token bucket and sliding window.

Author: UltraBalancer Team
Version: 1.0.0
"""

import time
import threading
from typing import Dict, Optional
from collections import deque
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    requests_per_second: float = 100.0  # Maximum requests per second
    burst_size: int = 10  # Maximum burst size above rate limit


class TokenBucketRateLimiter:
    """Token bucket algorithm for rate limiting.
    
    Tokens are added to the bucket at a constant rate. Each request consumes
    one token. If no tokens are available, the request is rejected.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize token bucket rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.capacity = self.config.burst_size
        self.tokens = float(self.capacity)
        self.rate = self.config.requests_per_second
        self.last_update = time.time()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "accepted_requests": 0,
            "rejected_requests": 0
        }

    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_update
        
        # Add tokens based on time elapsed
        tokens_to_add = elapsed * self.rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_update = now

    def allow_request(self, tokens: int = 1) -> bool:
        """Check if request should be allowed.
        
        Args:
            tokens: Number of tokens to consume (default: 1)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        with self.lock:
            self.stats["total_requests"] += 1
            self._refill_tokens()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.stats["accepted_requests"] += 1
                return True
            else:
                self.stats["rejected_requests"] += 1
                return False

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.lock:
            rejection_rate = (
                self.stats["rejected_requests"] / self.stats["total_requests"] * 100
                if self.stats["total_requests"] > 0 else 0
            )
            
            return {
                "algorithm": "token_bucket",
                "total_requests": self.stats["total_requests"],
                "accepted_requests": self.stats["accepted_requests"],
                "rejected_requests": self.stats["rejected_requests"],
                "rejection_rate": f"{rejection_rate:.2f}%",
                "current_tokens": f"{self.tokens:.2f}",
                "capacity": self.capacity,
                "rate": self.rate
            }


class SlidingWindowRateLimiter:
    """Sliding window algorithm for rate limiting.
    
    Tracks requests in a sliding time window. Requests are allowed if the count
    within the window doesn't exceed the limit.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize sliding window rate limiter.
        
        Args:
            config: Rate limit configuration
        """
        self.config = config or RateLimitConfig()
        self.window_size = 1.0  # 1 second window
        self.max_requests = int(self.config.requests_per_second)
        self.request_times: deque = deque()
        self.lock = threading.Lock()
        
        # Statistics
        self.stats = {
            "total_requests": 0,
            "accepted_requests": 0,
            "rejected_requests": 0,
            "windows_processed": 0
        }

    def _clean_old_requests(self) -> None:
        """Remove requests outside the current window."""
        now = time.time()
        window_start = now - self.window_size
        
        while self.request_times and self.request_times[0] < window_start:
            self.request_times.popleft()

    def allow_request(self) -> bool:
        """Check if request should be allowed.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        with self.lock:
            self.stats["total_requests"] += 1
            self._clean_old_requests()
            
            if len(self.request_times) < self.max_requests:
                self.request_times.append(time.time())
                self.stats["accepted_requests"] += 1
                return True
            else:
                self.stats["rejected_requests"] += 1
                return False

    def get_current_rate(self) -> float:
        """Get current request rate.
        
        Returns:
            Current requests per second
        """
        with self.lock:
            self._clean_old_requests()
            return len(self.request_times) / self.window_size

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        with self.lock:
            self._clean_old_requests()
            rejection_rate = (
                self.stats["rejected_requests"] / self.stats["total_requests"] * 100
                if self.stats["total_requests"] > 0 else 0
            )
            
            return {
                "algorithm": "sliding_window",
                "total_requests": self.stats["total_requests"],
                "accepted_requests": self.stats["accepted_requests"],
                "rejected_requests": self.stats["rejected_requests"],
                "rejection_rate": f"{rejection_rate:.2f}%",
                "current_rate": f"{self.get_current_rate():.2f} req/s",
                "requests_in_window": len(self.request_times),
                "max_requests": self.max_requests,
                "window_size": self.window_size
            }


class AdaptiveRateLimiter:
    """Adaptive rate limiter that adjusts based on backend health.
    
    Automatically reduces rate limits when backends show signs of stress
    and increases limits when performance is good.
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """Initialize adaptive rate limiter.
        
        Args:
            config: Initial rate limit configuration
        """
        self.base_config = config or RateLimitConfig()
        self.current_rate = self.base_config.requests_per_second
        self.min_rate = self.base_config.requests_per_second * 0.1  # 10% of base
        self.max_rate = self.base_config.requests_per_second * 2.0  # 200% of base
        
        # Use token bucket internally
        self.limiter = TokenBucketRateLimiter(self.base_config)
        self.lock = threading.Lock()
        
        # Performance tracking
        self.recent_failures = deque(maxlen=100)
        self.adjustment_interval = 10.0  # seconds
        self.last_adjustment = time.time()

    def record_response(self, success: bool, response_time: float) -> None:
        """Record backend response for adaptive adjustment.
        
        Args:
            success: Whether request succeeded
            response_time: Response time in seconds
        """
        with self.lock:
            self.recent_failures.append((not success, response_time))
            self._adjust_rate()

    def _adjust_rate(self) -> None:
        """Adjust rate limit based on recent performance."""
        now = time.time()
        if now - self.last_adjustment < self.adjustment_interval:
            return
        
        if len(self.recent_failures) < 10:
            return  # Not enough data
        
        # Calculate failure rate and average response time
        failures = sum(1 for failed, _ in self.recent_failures if failed)
        failure_rate = failures / len(self.recent_failures)
        avg_response_time = sum(rt for _, rt in self.recent_failures) / len(self.recent_failures)
        
        # Adjust rate based on health metrics
        if failure_rate > 0.1 or avg_response_time > 1.0:
            # Reduce rate by 20%
            self.current_rate = max(self.min_rate, self.current_rate * 0.8)
        elif failure_rate < 0.01 and avg_response_time < 0.1:
            # Increase rate by 10%
            self.current_rate = min(self.max_rate, self.current_rate * 1.1)
        
        # Update internal limiter
        self.limiter.rate = self.current_rate
        self.last_adjustment = now

    def allow_request(self) -> bool:
        """Check if request should be allowed.
        
        Returns:
            True if request is allowed, False if rate limited
        """
        return self.limiter.allow_request()

    def get_stats(self) -> Dict:
        """Get rate limiter statistics."""
        stats = self.limiter.get_stats()
        stats["algorithm"] = "adaptive"
        stats["current_rate"] = self.current_rate
        stats["base_rate"] = self.base_config.requests_per_second
        stats["min_rate"] = self.min_rate
        stats["max_rate"] = self.max_rate
        return stats
