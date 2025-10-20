"""Prometheus-compatible Metrics Exporter for UltraBalancer Pro.

This module implements an async HTTP server that exposes health and routing
metrics in Prometheus format on the /metrics endpoint.
"""

import asyncio
import time
from typing import Dict, List, Optional, Any
from collections import defaultdict
from aiohttp import web
import logging

# Configure logging
logger = logging.getLogger(__name__)


class MetricsExporter:
    """Async Prometheus-compatible metrics exporter.
    
    Exposes health and routing metrics on /metrics endpoint using aiohttp.
    All operations are async for non-blocking performance monitoring.
    """

    def __init__(self, host: str = '0.0.0.0', port: int = 9090):
        """Initialize the metrics exporter.
        
        Args:
            host: Host address to bind the metrics server (default: '0.0.0.0')
            port: Port number for the metrics endpoint (default: 9090)
        """
        self.host = host
        self.port = port
        self.app = web.Application()
        self.runner: Optional[web.AppRunner] = None
        self.site: Optional[web.TCPSite] = None
        
        # Metrics storage
        self._request_count = defaultdict(int)  # Counter by route
        self._request_duration = defaultdict(list)  # Duration samples by route
        self._active_connections = 0  # Gauge for active connections
        self._backend_health = {}  # Health status by backend
        self._error_count = defaultdict(int)  # Error counter by type
        self._start_time = time.time()  # Server start time
        
        # Setup routes
        self._setup_routes()
        
        logger.info(f"MetricsExporter initialized on {host}:{port}")

    def _setup_routes(self):
        """Configure HTTP routes for the metrics server."""
        self.app.router.add_get('/metrics', self.handle_metrics)
        self.app.router.add_get('/health', self.handle_health)

    async def handle_metrics(self, request: web.Request) -> web.Response:
        """Handle GET requests to /metrics endpoint.
        
        Generates and returns Prometheus-formatted metrics including:
        - Request counters by route
        - Request duration histograms
        - Active connection gauges
        - Backend health status
        - Error counters
        - Uptime metrics
        
        Args:
            request: The aiohttp request object
            
        Returns:
            web.Response with Prometheus-formatted metrics
        """
        metrics_output = []
        
        # Generate uptime metric
        uptime = time.time() - self._start_time
        metrics_output.append("# HELP ultrabalancer_uptime_seconds Server uptime in seconds")
        metrics_output.append("# TYPE ultrabalancer_uptime_seconds gauge")
        metrics_output.append(f"ultrabalancer_uptime_seconds {uptime:.2f}\n")
        
        # Generate request count metrics
        metrics_output.append("# HELP ultrabalancer_requests_total Total number of requests by route")
        metrics_output.append("# TYPE ultrabalancer_requests_total counter")
        for route, count in self._request_count.items():
            metrics_output.append(f'ultrabalancer_requests_total{{route="{route}"}} {count}')
        metrics_output.append("")
        
        # Generate request duration metrics (average)
        metrics_output.append("# HELP ultrabalancer_request_duration_seconds Average request duration by route")
        metrics_output.append("# TYPE ultrabalancer_request_duration_seconds gauge")
        for route, durations in self._request_duration.items():
            if durations:
                avg_duration = sum(durations) / len(durations)
                metrics_output.append(f'ultrabalancer_request_duration_seconds{{route="{route}"}} {avg_duration:.4f}')
        metrics_output.append("")
        
        # Generate active connections metric
        metrics_output.append("# HELP ultrabalancer_active_connections Current number of active connections")
        metrics_output.append("# TYPE ultrabalancer_active_connections gauge")
        metrics_output.append(f"ultrabalancer_active_connections {self._active_connections}\n")
        
        # Generate backend health metrics
        metrics_output.append("# HELP ultrabalancer_backend_health Backend health status (1=healthy, 0=unhealthy)")
        metrics_output.append("# TYPE ultrabalancer_backend_health gauge")
        for backend, is_healthy in self._backend_health.items():
            health_value = 1 if is_healthy else 0
            metrics_output.append(f'ultrabalancer_backend_health{{backend="{backend}"}} {health_value}')
        metrics_output.append("")
        
        # Generate error count metrics
        metrics_output.append("# HELP ultrabalancer_errors_total Total number of errors by type")
        metrics_output.append("# TYPE ultrabalancer_errors_total counter")
        for error_type, count in self._error_count.items():
            metrics_output.append(f'ultrabalancer_errors_total{{type="{error_type}"}} {count}')
        metrics_output.append("")
        
        # Join all metrics with newlines
        metrics_text = "\n".join(metrics_output)
        
        return web.Response(
            text=metrics_text,
            content_type='text/plain; version=0.0.4'
        )

    async def handle_health(self, request: web.Request) -> web.Response:
        """Handle GET requests to /health endpoint.
        
        Provides a simple health check endpoint for the metrics server itself.
        
        Args:
            request: The aiohttp request object
            
        Returns:
            web.Response with health status
        """
        health_data = {
            "status": "healthy",
            "uptime": time.time() - self._start_time,
            "active_connections": self._active_connections,
            "total_requests": sum(self._request_count.values())
        }
        
        return web.json_response(health_data)

    def record_request(self, route: str, duration: float):
        """Record a completed request for metrics.
        
        Args:
            route: The route/endpoint that handled the request
            duration: Request duration in seconds
        """
        self._request_count[route] += 1
        self._request_duration[route].append(duration)
        
        # Keep only last 1000 samples per route to prevent memory growth
        if len(self._request_duration[route]) > 1000:
            self._request_duration[route] = self._request_duration[route][-1000:]
        
        logger.debug(f"Recorded request: route={route}, duration={duration:.4f}s")

    def increment_active_connections(self):
        """Increment the active connections counter."""
        self._active_connections += 1
        logger.debug(f"Active connections: {self._active_connections}")

    def decrement_active_connections(self):
        """Decrement the active connections counter."""
        self._active_connections = max(0, self._active_connections - 1)
        logger.debug(f"Active connections: {self._active_connections}")

    def update_backend_health(self, backend: str, is_healthy: bool):
        """Update the health status of a backend server.
        
        Args:
            backend: Backend server identifier
            is_healthy: True if backend is healthy, False otherwise
        """
        self._backend_health[backend] = is_healthy
        logger.debug(f"Backend health updated: {backend}={is_healthy}")

    def record_error(self, error_type: str):
        """Record an error occurrence.
        
        Args:
            error_type: Type/category of the error
        """
        self._error_count[error_type] += 1
        logger.debug(f"Error recorded: {error_type}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of current metrics.
        
        Returns:
            Dictionary containing current metrics state
        """
        return {
            "uptime": time.time() - self._start_time,
            "total_requests": dict(self._request_count),
            "active_connections": self._active_connections,
            "backend_health": dict(self._backend_health),
            "total_errors": dict(self._error_count)
        }

    async def start(self):
        """Start the metrics exporter HTTP server.
        
        This is an async method that initializes and starts the aiohttp server.
        The server runs in the background and serves metrics on the configured endpoint.
        """
        try:
            # Setup and start the web server
            self.runner = web.AppRunner(self.app)
            await self.runner.setup()
            
            self.site = web.TCPSite(self.runner, self.host, self.port)
            await self.site.start()
            
            logger.info(f"Metrics exporter started at http://{self.host}:{self.port}/metrics")
            
        except Exception as e:
            logger.error(f"Failed to start metrics exporter: {e}")
            raise

    async def stop(self):
        """Stop the metrics exporter HTTP server.
        
        Gracefully shuts down the aiohttp server and cleans up resources.
        """
        try:
            if self.site:
                await self.site.stop()
                logger.info("Metrics site stopped")
            
            if self.runner:
                await self.runner.cleanup()
                logger.info("Metrics runner cleaned up")
            
            logger.info("Metrics exporter stopped successfully")
            
        except Exception as e:
            logger.error(f"Error stopping metrics exporter: {e}")
            raise

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()


# Example usage
if __name__ == "__main__":
    async def main():
        """Example usage of MetricsExporter."""
        # Create and start metrics exporter
        exporter = MetricsExporter(host='0.0.0.0', port=9090)
        
        try:
            await exporter.start()
            
            # Simulate some metrics
            exporter.record_request("/api/users", 0.125)
            exporter.record_request("/api/posts", 0.084)
            exporter.increment_active_connections()
            exporter.update_backend_health("backend-1", True)
            exporter.update_backend_health("backend-2", False)
            exporter.record_error("connection_timeout")
            
            logger.info("Metrics exporter running. Visit http://localhost:9090/metrics")
            logger.info("Press Ctrl+C to stop")
            
            # Keep running
            await asyncio.Event().wait()
            
        except KeyboardInterrupt:
            logger.info("Shutting down...")
        finally:
            await exporter.stop()
    
    # Configure logging for example
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run the example
    asyncio.run(main())
