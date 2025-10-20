"""
HealthChecker for UltraBalancer-Pro
Efficiently monitors backend servers with async HTTP/TCP checks.
"""
import asyncio
import aiohttp

class HealthChecker:
    def __init__(self, backends, interval=5, retries=2, timeout=2):
        """
        backends: List of backend server URLs/IPs.
        interval: Seconds between health checks.
        retries: How many times to retry on failure.
        timeout: Seconds per health check attempt.
        """
        self.backends = backends
        self.interval = interval
        self.retries = retries
        self.timeout = timeout
        self.status = {b: False for b in backends}

    async def _check_backend(self, backend):
        """Checks health of a single backend (HTTP GET), with retries."""
        for _ in range(self.retries):
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(backend, timeout=self.timeout) as resp:
                        if resp.status == 200:
                            return True
            except Exception:
                await asyncio.sleep(0.1)
        return False

    async def check_all(self):
        """Check all backends in parallel and update status dict."""
        results = await asyncio.gather(
            *(self._check_backend(b) for b in self.backends)
        )
        for b, ok in zip(self.backends, results):
            self.status[b] = ok

    async def loop(self):
        """Continuous health monitoring loop."""
        while True:
            await self.check_all()
            await asyncio.sleep(self.interval)
