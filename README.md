# UltraBalancer Pro

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg)](https://github.com/arpancodez/ultrabalancer-pro)

Ultra-advanced load balancer with Python+C++ hybrid architecture. Features ML-powered routing algorithms, flexible plugin system, comprehensive metrics export, and high-performance async design for enterprise-grade traffic management.

## 🚀 Features

### Core Capabilities
- **High-Performance Architecture**: Python+C++ hybrid design for optimal performance
- **Async I/O**: Non-blocking async operations for handling thousands of concurrent connections
- **ML-Powered Routing**: Machine learning algorithms for intelligent traffic distribution
- **Flexible Plugin System**: Easily extend functionality with custom plugins
- **Real-time Health Monitoring**: Automatic backend health checks with smart retry logic
- **Comprehensive Metrics**: Detailed performance metrics and monitoring

### Load Balancing Algorithms
- Round Robin
- Weighted Round Robin
- Least Connections
- IP Hash
- Random
- ML-Powered Adaptive Routing

### Advanced Features
- Circuit breaker pattern for fault tolerance
- Connection pooling and keep-alive support
- SSL/TLS termination
- WebSocket support
- Request/response transformation
- Rate limiting and throttling
- Session persistence (sticky sessions)
- Health check customization
- Graceful shutdown and reload

## 📦 Installation

### Prerequisites
- Python 3.9 or higher
- C++ compiler (gcc 7+ or clang 8+)
- pip or poetry package manager

### From Source

```bash
# Clone the repository
git clone https://github.com/arpancodez/ultrabalancer-pro.git
cd ultrabalancer-pro

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Using pip (when published)

```bash
pip install ultrabalancer-pro
```

### Using Docker

```bash
# Build image
docker build -t ultrabalancer-pro .

# Run container
docker run -d -p 8080:8080 -v ./config:/app/config ultrabalancer-pro
```

## ⚙️ Configuration

Create a configuration file `config/balancer.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8080
  workers: 4

backends:
  - url: http://backend1.example.com:8001
    weight: 1
    max_connections: 100
  - url: http://backend2.example.com:8002
    weight: 2
    max_connections: 100
  - url: http://backend3.example.com:8003
    weight: 1
    max_connections: 50

routing:
  algorithm: weighted_round_robin
  # Options: round_robin, weighted_round_robin, least_connections, 
  #          ip_hash, random, ml_adaptive

health_check:
  enabled: true
  interval: 10  # seconds
  timeout: 5    # seconds
  path: /health
  healthy_threshold: 2
  unhealthy_threshold: 3
  retry_backoff:
    initial: 1
    max: 60
    multiplier: 2

metrics:
  enabled: true
  port: 9090
  path: /metrics
  exporters:
    - prometheus
    - statsd

plugins:
  directory: ./src/plugins
  enabled:
    - request_logger
    - rate_limiter
    - circuit_breaker

logging:
  level: INFO
  format: json
  output: stdout
```

## 📈 Usage

### Basic Usage

```python
from ultrabalancer.core import Router
from ultrabalancer.config import load_config

# Load configuration
config = load_config('config/balancer.yaml')

# Initialize router
router = Router(config)

# Start the load balancer
await router.start()
```

### Command Line Interface

```bash
# Start with default config
ultrabalancer start

# Start with custom config
ultrabalancer start --config /path/to/config.yaml

# Check configuration
ultrabalancer validate --config config.yaml

# Show statistics
ultrabalancer stats

# Reload configuration without downtime
ultrabalancer reload
```

### Advanced Usage

```python
import asyncio
from ultrabalancer.core import Router
from ultrabalancer.health import HealthChecker
from ultrabalancer.metrics import MetricsExporter
from ultrabalancer.plugins import PluginLoader

async def main():
    # Initialize components
    router = Router(
        algorithm='ml_adaptive',
        backends=[
            {'url': 'http://backend1:8001', 'weight': 1},
            {'url': 'http://backend2:8002', 'weight': 2},
        ]
    )
    
    # Configure health checking
    health_checker = HealthChecker(
        interval=10,
        timeout=5,
        retry_strategy='exponential_backoff'
    )
    router.set_health_checker(health_checker)
    
    # Enable metrics
    metrics = MetricsExporter(port=9090)
    router.set_metrics_exporter(metrics)
    
    # Load plugins
    plugin_loader = PluginLoader('./src/plugins')
    await plugin_loader.load_all()
    router.register_plugins(plugin_loader.plugins)
    
    # Start router
    await router.start()
    
    try:
        await asyncio.Event().wait()  # Keep running
    except KeyboardInterrupt:
        await router.shutdown(graceful=True)

if __name__ == '__main__':
    asyncio.run(main())
```

## 📊 Monitoring & Metrics

### Prometheus Metrics

Access Prometheus metrics at `http://localhost:9090/metrics`:

```
# Request metrics
ultrabalancer_requests_total
ultrabalancer_requests_duration_seconds
ultrabalancer_requests_in_flight

# Backend metrics
ultrabalancer_backend_connections
ultrabalancer_backend_requests_total
ultrabalancer_backend_failures_total
ultrabalancer_backend_health_status

# System metrics
ultrabalancer_cpu_usage
ultrabalancer_memory_usage
ultrabalancer_goroutines
```

### Health Check Endpoint

```bash
curl http://localhost:8080/health
```

Response:
```json
{
  "status": "healthy",
  "backends": [
    {"url": "http://backend1:8001", "status": "healthy", "latency_ms": 12},
    {"url": "http://backend2:8002", "status": "healthy", "latency_ms": 8},
    {"url": "http://backend3:8003", "status": "unhealthy", "error": "timeout"}
  ],
  "uptime_seconds": 3600,
  "requests_total": 150000
}
```

## 🔌 Plugins

### Creating Custom Plugins

Create a plugin in `src/plugins/algorithms/my_algorithm.py`:

```python
from ultrabalancer.plugins.base import RoutingAlgorithm
from typing import List, Optional

class MyCustomAlgorithm(RoutingAlgorithm):
    """Custom routing algorithm."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.name = "my_custom_algorithm"
    
    async def select_backend(self, request, backends: List) -> Optional[str]:
        """Select backend based on custom logic."""
        # Your custom selection logic here
        available = [b for b in backends if b.healthy]
        if not available:
            return None
        
        # Example: Select based on custom header
        priority = request.headers.get('X-Priority', 'normal')
        if priority == 'high':
            return available[0]  # First available backend
        return available[-1]  # Last available backend
    
    async def on_request_complete(self, backend: str, 
                                 latency: float, success: bool):
        """Update algorithm state after request."""
        # Track performance metrics
        self.update_metrics(backend, latency, success)
```

Register the plugin:

```python
from ultrabalancer.plugins import PluginLoader

loader = PluginLoader('./src/plugins')
await loader.load_plugin('my_algorithm')
router.set_algorithm(loader.get_plugin('my_algorithm'))
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_router.py

# Run integration tests
pytest tests/integration/
```

### Load Testing

```bash
# Using Apache Bench
ab -n 10000 -c 100 http://localhost:8080/

# Using wrk
wrk -t12 -c400 -d30s http://localhost:8080/
```

## 📝 Documentation

- [Architecture Overview](docs/architecture.md)
- [Plugin Development Guide](docs/plugins.md)
- [Configuration Reference](docs/configuration.md)
- [API Documentation](docs/api.md)
- [Performance Tuning](docs/performance.md)

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Quick Start for Contributors

```bash
# Fork and clone the repository
git clone https://github.com/YOUR_USERNAME/ultrabalancer-pro.git
cd ultrabalancer-pro

# Create a feature branch
git checkout -b feature/my-feature

# Install development dependencies
pip install -r requirements-dev.txt

# Make your changes and add tests
# ...

# Run tests and linters
pytest
flake8 src/
black src/

# Commit and push
git commit -m "feat: add my feature"
git push origin feature/my-feature

# Open a pull request
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Arpan** - [@arpancodez](https://github.com/arpancodez)

## 🚀 Roadmap

- [ ] gRPC support
- [ ] HTTP/3 (QUIC) support
- [ ] Advanced caching layer
- [ ] Request/response transformation plugins
- [ ] GraphQL load balancing
- [ ] Cloud-native integrations (K8s, AWS ELB)
- [ ] Web UI dashboard
- [ ] Advanced ML models for traffic prediction

## ⭐ Star History

If you find this project useful, please consider giving it a star!

## 💬 Support

- Open an [issue](https://github.com/arpancodez/ultrabalancer-pro/issues)
- Check [discussions](https://github.com/arpancodez/ultrabalancer-pro/discussions)
- Read the [documentation](docs/)

## 🙏 Acknowledgments

- Inspired by industry-standard load balancers (HAProxy, NGINX, Envoy)
- Built with modern Python async capabilities
- Community feedback and contributions

---

Made with ❤️ by the UltraBalancer Pro team
