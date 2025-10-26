"""Integration tests for UltraBalancer Pro load balancer.

These tests verify the end-to-end functionality of the load balancer
with real backend servers and network operations.
"""

import asyncio
import pytest
import aiohttp
from typing import List
import time
from unittest.mock import AsyncMock, patch

from ultrabalancer.core.balancer import LoadBalancer
from ultrabalancer.algorithms import RoundRobin, LeastConnections
from ultrabalancer.backends import Backend, BackendPool
from ultrabalancer.health import HealthChecker


@pytest.fixture
async def mock_backend_servers():
    """Create mock backend servers for testing."""
    servers = [
        Backend(host="localhost", port=8081, weight=100),
        Backend(host="localhost", port=8082, weight=100),
        Backend(host="localhost", port=8083, weight=100),
    ]
    yield servers


@pytest.fixture
async def backend_pool(mock_backend_servers):
    """Create a backend pool with mock servers."""
    pool = BackendPool(backends=mock_backend_servers)
    await pool.initialize()
    yield pool
    await pool.cleanup()


@pytest.fixture
async def load_balancer(backend_pool):
    """Create a load balancer instance with round-robin algorithm."""
    lb = LoadBalancer(
        backend_pool=backend_pool,
        algorithm=RoundRobin(),
        health_checker=HealthChecker(interval=5)
    )
    await lb.start()
    yield lb
    await lb.stop()


class TestLoadBalancerIntegration:
    """Integration tests for load balancer functionality."""

    @pytest.mark.asyncio
    async def test_round_robin_distribution(self, load_balancer, backend_pool):
        """Test that round-robin algorithm distributes requests evenly."""
        request_counts = {backend.id: 0 for backend in backend_pool.backends}
        
        # Send 30 requests (10 per backend with 3 backends)
        for _ in range(30):
            backend = await load_balancer.select_backend()
            request_counts[backend.id] += 1
        
        # Verify even distribution
        for count in request_counts.values():
            assert count == 10, "Round-robin should distribute evenly"

    @pytest.mark.asyncio
    async def test_backend_failure_handling(self, load_balancer, backend_pool):
        """Test that failed backends are removed from rotation."""
        # Mark one backend as unhealthy
        failed_backend = backend_pool.backends[0]
        failed_backend.healthy = False
        
        # Send 20 requests
        selected_backends = []
        for _ in range(20):
            backend = await load_balancer.select_backend()
            selected_backends.append(backend.id)
        
        # Verify failed backend was not selected
        assert failed_backend.id not in selected_backends
        assert len(set(selected_backends)) == 2  # Only 2 healthy backends

    @pytest.mark.asyncio
    async def test_least_connections_algorithm(self, backend_pool):
        """Test that least connections algorithm selects backend with fewest connections."""
        lb = LoadBalancer(
            backend_pool=backend_pool,
            algorithm=LeastConnections(),
        )
        await lb.start()
        
        # Simulate active connections
        backend_pool.backends[0].active_connections = 5
        backend_pool.backends[1].active_connections = 2
        backend_pool.backends[2].active_connections = 8
        
        # Should select backend with 2 connections
        selected = await lb.select_backend()
        assert selected.id == backend_pool.backends[1].id
        
        await lb.stop()

    @pytest.mark.asyncio
    async def test_health_check_recovery(self, load_balancer, backend_pool):
        """Test that backends recover after health check passes."""
        # Mark backend as unhealthy
        backend = backend_pool.backends[0]
        backend.healthy = False
        
        # Wait for health check to run and recover
        with patch.object(backend, 'check_health', return_value=True):
            await load_balancer.health_checker.check_all_backends()
        
        assert backend.healthy is True

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, load_balancer):
        """Test load balancer handles concurrent requests correctly."""
        async def make_request():
            backend = await load_balancer.select_backend()
            return backend
        
        # Send 100 concurrent requests
        tasks = [make_request() for _ in range(100)]
        results = await asyncio.gather(*tasks)
        
        # Verify all requests were handled
        assert len(results) == 100
        assert all(backend is not None for backend in results)

    @pytest.mark.asyncio
    async def test_weighted_distribution(self, backend_pool):
        """Test that weighted round-robin respects backend weights."""
        # Set different weights
        backend_pool.backends[0].weight = 50
        backend_pool.backends[1].weight = 100
        backend_pool.backends[2].weight = 150
        
        lb = LoadBalancer(
            backend_pool=backend_pool,
            algorithm=RoundRobin(weighted=True),
        )
        await lb.start()
        
        request_counts = {backend.id: 0 for backend in backend_pool.backends}
        
        # Send 300 requests
        for _ in range(300):
            backend = await lb.select_backend()
            request_counts[backend.id] += 1
        
        # Verify distribution matches weights (50:100:150 = 1:2:3)
        assert request_counts[backend_pool.backends[0].id] == 50
        assert request_counts[backend_pool.backends[1].id] == 100
        assert request_counts[backend_pool.backends[2].id] == 150
        
        await lb.stop()

    @pytest.mark.asyncio
    async def test_connection_limit_enforcement(self, load_balancer, backend_pool):
        """Test that max connections per backend are enforced."""
        # Set max connections
        backend = backend_pool.backends[0]
        backend.max_connections = 5
        backend.active_connections = 5
        
        # Try to select backend (should skip full backend)
        selected = await load_balancer.select_backend()
        assert selected.id != backend.id

    @pytest.mark.asyncio
    async def test_session_persistence(self, load_balancer):
        """Test that session persistence maintains client-backend mapping."""
        load_balancer.enable_session_persistence()
        
        # Simulate client with specific IP
        client_ip = "192.168.1.100"
        
        # First request should create session
        backend1 = await load_balancer.select_backend(client_id=client_ip)
        
        # Subsequent requests should use same backend
        backend2 = await load_balancer.select_backend(client_id=client_ip)
        backend3 = await load_balancer.select_backend(client_id=client_ip)
        
        assert backend1.id == backend2.id == backend3.id

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self, load_balancer):
        """Test that load balancer shuts down gracefully."""
        # Simulate active connections
        for backend in load_balancer.backend_pool.backends:
            backend.active_connections = 3
        
        # Initiate shutdown
        await load_balancer.stop(graceful=True, timeout=10)
        
        # Verify all connections were handled
        for backend in load_balancer.backend_pool.backends:
            assert backend.active_connections == 0

    @pytest.mark.asyncio
    async def test_metrics_collection(self, load_balancer):
        """Test that metrics are collected correctly."""
        # Send some requests
        for _ in range(10):
            await load_balancer.select_backend()
        
        metrics = load_balancer.get_metrics()
        
        assert metrics['total_requests'] >= 10
        assert 'active_connections' in metrics
        assert 'backend_health' in metrics

    @pytest.mark.asyncio
    async def test_backend_timeout_handling(self, load_balancer, backend_pool):
        """Test that backend timeouts are handled properly."""
        backend = backend_pool.backends[0]
        
        # Simulate slow backend
        with patch.object(backend, 'handle_request', side_effect=asyncio.TimeoutError):
            with pytest.raises(asyncio.TimeoutError):
                await load_balancer.forward_request(backend, {"path": "/test"})


class TestHealthCheckIntegration:
    """Integration tests for health check functionality."""

    @pytest.mark.asyncio
    async def test_http_health_check(self, backend_pool):
        """Test HTTP-based health checks."""
        health_checker = HealthChecker(
            check_type="http",
            path="/health",
            interval=5,
            timeout=3
        )
        
        # Mock HTTP response
        with patch('aiohttp.ClientSession.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_get.return_value.__aenter__.return_value = mock_response
            
            result = await health_checker.check_backend(backend_pool.backends[0])
            assert result is True

    @pytest.mark.asyncio
    async def test_tcp_health_check(self, backend_pool):
        """Test TCP-based health checks."""
        health_checker = HealthChecker(
            check_type="tcp",
            interval=5,
            timeout=3
        )
        
        # Mock TCP connection
        with patch('asyncio.open_connection', return_value=(None, None)):
            result = await health_checker.check_backend(backend_pool.backends[0])
            assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure_threshold(self, backend_pool):
        """Test that backends are marked unhealthy after threshold."""
        health_checker = HealthChecker(
            unhealthy_threshold=3,
            interval=1
        )
        
        backend = backend_pool.backends[0]
        
        # Simulate 3 consecutive failures
        for _ in range(3):
            with patch.object(health_checker, 'check_backend', return_value=False):
                await health_checker.run_health_check(backend)
        
        assert backend.healthy is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
