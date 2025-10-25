import asyncio
import pytest
from typing import List

# Assuming these modules exist in the project
# If paths differ, adjust imports accordingly
try:
    from src.core.router import Router
    from src.health.health_checker import HealthChecker
    from src.metrics.metrics_exporter import MetricsExporter
    from src.plugins.loader import PluginLoader
except Exception:  # pragma: no cover - fallback for alt package layouts
    from ultrabalancer.core.router import Router
    from ultrabalancer.health.health_checker import HealthChecker
    from ultrabalancer.metrics.metrics_exporter import MetricsExporter
    from ultrabalancer.plugins.loader import PluginLoader


class DummyBackend:
    def __init__(self, url: str, healthy: bool = True, weight: int = 1):
        self.url = url
        self.healthy = healthy
        self.weight = weight
        self.active_connections = 0


@pytest.mark.asyncio
async def test_router_basic_round_robin():
    backends: List[DummyBackend] = [
        DummyBackend("http://b1"),
        DummyBackend("http://b2"),
        DummyBackend("http://b3"),
    ]
    router = Router(algorithm="round_robin", backends=backends)

    selected = [await router.select_backend({}) for _ in range(6)]
    urls = [b.url if hasattr(b, "url") else b for b in selected]

    # Expect strict rotation
    assert urls == ["http://b1", "http://b2", "http://b3", "http://b1", "http://b2", "http://b3"]


@pytest.mark.asyncio
async def test_router_skips_unhealthy():
    backends = [
        DummyBackend("http://b1", healthy=False),
        DummyBackend("http://b2", healthy=True),
    ]
    router = Router(algorithm="round_robin", backends=backends)

    selected = [await router.select_backend({}) for _ in range(3)]
    urls = [b.url if hasattr(b, "url") else b for b in selected]

    assert urls == ["http://b2", "http://b2", "http://b2"]


@pytest.mark.asyncio
async def test_metrics_exporter_counters_increment(monkeypatch):
    metrics = MetricsExporter(port=0)
    metrics.reset()

    metrics.inc("requests_total")
    metrics.inc("requests_total", 2)
    metrics.observe("requests_latency_ms", 12.5)

    data = metrics.snapshot()
    assert data["requests_total"] == 3
    assert any(b for b in data.get("requests_latency_ms_bucket", []))


@pytest.mark.asyncio
async def test_health_checker_backoff_and_retry(monkeypatch):
    attempts = []

    async def fake_probe(url, timeout):
        attempts.append(asyncio.get_event_loop().time())
        # First 2 attempts fail, then succeed
        if len(attempts) < 3:
            return False, "timeout"
        return True, None

    hc = HealthChecker(
        interval=0.01,
        timeout=0.005,
        backoff_initial=0.01,
        backoff_multiplier=2.0,
        backoff_max=0.05,
        unhealthy_threshold=1,
        healthy_threshold=1,
    )
    hc._probe = fake_probe  # monkeypatch

    status, err = await hc.check("http://b1/health")
    assert status is True
    assert err is None
    assert len(attempts) >= 3  # retried with backoff


@pytest.mark.asyncio
async def test_plugin_loader_loads_algorithm(tmp_path):
    plugin_dir = tmp_path / "plugins" / "algorithms"
    plugin_dir.mkdir(parents=True)
    (plugin_dir / "sample_algo.py").write_text(
        """
from typing import List, Optional

class Algorithm:
    name = "sample_algo"
    async def select_backend(self, request, backends: List) -> Optional[str]:
        return backends[0]
"""
    )

    loader = PluginLoader(str(tmp_path / "plugins"))
    await loader.load_all()

    algo = loader.get_algorithm("sample_algo")
    assert algo is not None
