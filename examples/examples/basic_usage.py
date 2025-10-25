import asyncio
from typing import List

try:
    from src.core.router import Router
    from src.health.health_checker import HealthChecker
    from src.metrics.metrics_exporter import MetricsExporter
    from src.plugins.loader import PluginLoader
except Exception:
    from ultrabalancer.core.router import Router
    from ultrabalancer.health.health_checker import HealthChecker
    from ultrabalancer.metrics.metrics_exporter import MetricsExporter
    from ultrabalancer.plugins.loader import PluginLoader


async def main():
    backends: List[dict] = [
        {"url": "http://localhost:8001", "weight": 1},
        {"url": "http://localhost:8002", "weight": 2},
    ]

    router = Router(algorithm="weighted_round_robin", backends=backends)

    # Health checking
    health_checker = HealthChecker(interval=5, timeout=2)
    router.set_health_checker(health_checker)

    # Metrics exporter
    metrics = MetricsExporter(port=9090)
    router.set_metrics_exporter(metrics)

    # Plugins
    plugin_loader = PluginLoader("./src/plugins")
    await plugin_loader.load_all()

    await router.start()
    print("Router started on :8080. Press Ctrl+C to stop.")

    try:
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        await router.shutdown(graceful=True)


if __name__ == "__main__":
    asyncio.run(main())
