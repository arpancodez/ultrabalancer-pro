# src/py/main.py
"""
UltraBalancer-Pro: Async Python Entry Point
Runs the main event loop and loads advanced algorithms/plugins.
"""
import asyncio
from core.router import RequestRouter

async def main():
    router = RequestRouter()
    await router.run_event_loop()

if __name__ == "__main__":
    asyncio.run(main())
