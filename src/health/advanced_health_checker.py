"""Advanced Health Checker with Custom Endpoints.

Provides comprehensive health checking capabilities including custom health check
endpoints, response validation, dependency checks, and intelligent health scoring.

Author: UltraBalancer Team
Version: 1.0.0
"""

import time
import asyncio
import aiohttp
import threading
from typing import Dict, Optional, List, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
import re


class HealthStatus(Enum):
    """Health status of a backend."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckConfig:
    """Configuration for health checks."""
    endpoint: str = "/health"  # Health check endpoint
    method: str = "GET"  # HTTP method
    timeout: float = 5.0  # Request timeout in seconds
    interval: float = 30.0  # Check interval in seconds
    expected_status: int = 200  # Expected HTTP status code
    expected_body_pattern: Optional[str] = None  # Regex pattern for body validation
    headers: Dict[str, str] = field(default_factory=dict)  # Custom headers
    
    # Thresholds
    healthy_threshold: int = 2  # Consecutive successes to mark healthy
    unhealthy_threshold: int = 3  # Consecutive failures to mark unhealthy
    
    # Advanced features
    check_dependencies: bool = False  # Check backend dependencies
    response_time_threshold: float = 1.0  # Max acceptable response time


@dataclass
class HealthCheckResult:
    """Result of a health check."""
    status: HealthStatus
    response_time: float
    status_code: Optional[int] = None
    error_message: Optional[str] = None
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class AdvancedHealthChecker:
    """Advanced health checker with custom endpoints and validation."""

    def __init__(self, backend_id: str, backend_url: str, 
                 config: Optional[HealthCheckConfig] = None):
        """Initialize advanced health checker.
        
        Args:
            backend_id: Unique identifier for the backend
            backend_url: Base URL of the backend server
            config: Health check configuration
        """
        self.backend_id = backend_id
        self.backend_url = backend_url.rstrip('/')
        self.config = config or HealthCheckConfig()
        
        # Health state
        self.current_status = HealthStatus.UNKNOWN
        self.consecutive_successes = 0
        self.consecutive_failures = 0
        self.last_check_time = 0.0
        self.last_success_time = 0.0
        
        # History
        self.check_history: List[HealthCheckResult] = []
        self.max_history = 100
        
        # Statistics
        self.stats = {
            "total_checks": 0,
            "successful_checks": 0,
            "failed_checks": 0,
            "average_response_time": 0.0,
            "uptime_percentage": 0.0
        }
        
        self.lock = threading.Lock()
        self.running = False
        self.check_task = None

    async def perform_check(self) -> HealthCheckResult:
        """Perform a single health check.
        
        Returns:
            Health check result
        """
        start_time = time.time()
        health_url = f"{self.backend_url}{self.config.endpoint}"
        
        try:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.request(
                    self.config.method,
                    health_url,
                    headers=self.config.headers
                ) as response:
                    response_time = time.time() - start_time
                    body = await response.text()
                    
                    # Check status code
                    if response.status != self.config.expected_status:
                        return HealthCheckResult(
                            status=HealthStatus.UNHEALTHY,
                            response_time=response_time,
                            status_code=response.status,
                            error_message=f"Unexpected status code: {response.status}"
                        )
                    
                    # Check response body pattern if configured
                    if self.config.expected_body_pattern:
                        if not re.search(self.config.expected_body_pattern, body):
                            return HealthCheckResult(
                                status=HealthStatus.UNHEALTHY,
                                response_time=response_time,
                                status_code=response.status,
                                error_message="Response body doesn't match expected pattern"
                            )
                    
                    # Check response time
                    if response_time > self.config.response_time_threshold:
                        return HealthCheckResult(
                            status=HealthStatus.DEGRADED,
                            response_time=response_time,
                            status_code=response.status,
                            error_message=f"Slow response: {response_time:.2f}s"
                        )
                    
                    # All checks passed
                    return HealthCheckResult(
                        status=HealthStatus.HEALTHY,
                        response_time=response_time,
                        status_code=response.status
                    )
                    
        except asyncio.TimeoutError:
            response_time = time.time() - start_time
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error_message="Health check timeout"
            )
        except Exception as e:
            response_time = time.time() - start_time
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                response_time=response_time,
                error_message=str(e)
            )

    def _update_health_status(self, result: HealthCheckResult) -> None:
        """Update health status based on check result.
        
        Args:
            result: Health check result
        """
        with self.lock:
            self.last_check_time = result.timestamp
            
            # Update statistics
            self.stats["total_checks"] += 1
            
            if result.status == HealthStatus.HEALTHY:
                self.consecutive_successes += 1
                self.consecutive_failures = 0
                self.stats["successful_checks"] += 1
                self.last_success_time = result.timestamp
            else:
                self.consecutive_failures += 1
                self.consecutive_successes = 0
                self.stats["failed_checks"] += 1
            
            # Update average response time
            total_time = (self.stats["average_response_time"] * 
                         (self.stats["total_checks"] - 1) + result.response_time)
            self.stats["average_response_time"] = total_time / self.stats["total_checks"]
            
            # Update uptime percentage
            self.stats["uptime_percentage"] = (
                self.stats["successful_checks"] / self.stats["total_checks"] * 100
            )
            
            # Update current status based on thresholds
            if self.consecutive_successes >= self.config.healthy_threshold:
                self.current_status = HealthStatus.HEALTHY
            elif self.consecutive_failures >= self.config.unhealthy_threshold:
                self.current_status = HealthStatus.UNHEALTHY
            elif result.status == HealthStatus.DEGRADED:
                self.current_status = HealthStatus.DEGRADED
            
            # Add to history
            self.check_history.append(result)
            if len(self.check_history) > self.max_history:
                self.check_history.pop(0)

    async def _health_check_loop(self) -> None:
        """Background health check loop."""
        while self.running:
            try:
                result = await self.perform_check()
                self._update_health_status(result)
            except Exception as e:
                print(f"Error in health check loop for {self.backend_id}: {e}")
            
            await asyncio.sleep(self.config.interval)

    def start(self) -> None:
        """Start periodic health checks."""
        if self.running:
            return
        
        self.running = True
        # Create event loop in background thread
        def run_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._health_check_loop())
        
        thread = threading.Thread(target=run_loop, daemon=True)
        thread.start()

    def stop(self) -> None:
        """Stop health checks."""
        self.running = False

    def is_healthy(self) -> bool:
        """Check if backend is currently healthy.
        
        Returns:
            True if backend is healthy
        """
        with self.lock:
            return self.current_status == HealthStatus.HEALTHY

    def get_status(self) -> HealthStatus:
        """Get current health status.
        
        Returns:
            Current health status
        """
        with self.lock:
            return self.current_status

    def get_health_score(self) -> float:
        """Calculate health score based on recent checks.
        
        Returns:
            Health score between 0.0 (unhealthy) and 1.0 (healthy)
        """
        with self.lock:
            if not self.check_history:
                return 0.0
            
            # Weight recent checks more heavily
            total_score = 0.0
            total_weight = 0.0
            
            for i, result in enumerate(self.check_history[-20:]):
                weight = i + 1  # More recent = higher weight
                score = 0.0
                
                if result.status == HealthStatus.HEALTHY:
                    score = 1.0
                elif result.status == HealthStatus.DEGRADED:
                    score = 0.5
                # UNHEALTHY = 0.0
                
                total_score += score * weight
                total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 0.0

    def get_stats(self) -> Dict:
        """Get health checker statistics.
        
        Returns:
            Dictionary of statistics
        """
        with self.lock:
            return {
                "backend_id": self.backend_id,
                "backend_url": self.backend_url,
                "current_status": self.current_status.value,
                "health_score": f"{self.get_health_score():.2f}",
                "consecutive_successes": self.consecutive_successes,
                "consecutive_failures": self.consecutive_failures,
                "last_check_time": self.last_check_time,
                "last_success_time": self.last_success_time,
                "total_checks": self.stats["total_checks"],
                "successful_checks": self.stats["successful_checks"],
                "failed_checks": self.stats["failed_checks"],
                "uptime_percentage": f"{self.stats['uptime_percentage']:.2f}%",
                "average_response_time": f"{self.stats['average_response_time']:.3f}s",
                "config": {
                    "endpoint": self.config.endpoint,
                    "interval": self.config.interval,
                    "timeout": self.config.timeout,
                    "healthy_threshold": self.config.healthy_threshold,
                    "unhealthy_threshold": self.config.unhealthy_threshold
                }
            }

    def get_recent_results(self, count: int = 10) -> List[Dict]:
        """Get recent health check results.
        
        Args:
            count: Number of recent results to return
            
        Returns:
            List of recent health check results
        """
        with self.lock:
            results = []
            for result in self.check_history[-count:]:
                results.append({
                    "status": result.status.value,
                    "response_time": f"{result.response_time:.3f}s",
                    "status_code": result.status_code,
                    "error_message": result.error_message,
                    "timestamp": result.timestamp
                })
            return results
