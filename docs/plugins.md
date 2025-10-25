# Plugin Development Guide

This guide explains how to build plugins for UltraBalancer Pro.

## Plugin Types
- Algorithms: implement routing strategies
- Middleware: request/response hooks

## Directory Structure

```
src/plugins/
  base.py
  loader.py
  algorithms/
    my_algorithm.py
  middleware/
    request_logger.py
```

## Base Interfaces

```python
from typing import List, Optional, Any

class RoutingAlgorithm:
    name: str = "base"

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def select_backend(self, request: Any, backends: List[Any]) -> Optional[Any]:
        raise NotImplementedError

    async def on_request_complete(self, backend: Any, latency: float, success: bool):
        pass
```

## Implement an Algorithm
```python
from src.plugins.base import RoutingAlgorithm
from typing import List, Optional

class MyAlgorithm(RoutingAlgorithm):
    name = "my_algorithm"

    async def select_backend(self, request, backends: List) -> Optional[str]:
        healthy = [b for b in backends if b.healthy]
        if not healthy:
            return None
        # Example: choose least connections
        return min(healthy, key=lambda b: b.active_connections)
```

## Register and Use
```python
from src.plugins.loader import PluginLoader
loader = PluginLoader("./src/plugins")
await loader.load_all()
router.set_algorithm(loader.get_algorithm("my_algorithm"))
```

## Best Practices
- Use async everywhere
- Avoid blocking calls; offload to thread pool if needed
- Emit metrics and logs via provided utilities
- Add tests under tests/plugins
```
