# Performance Tuning Guide

## Overview
This guide provides comprehensive performance tuning recommendations for UltraBalancer Pro to optimize throughput, reduce latency, and improve resource utilization.

## Table of Contents
1. [System Configuration](#system-configuration)
2. [Load Balancer Configuration](#load-balancer-configuration)
3. [Backend Server Optimization](#backend-server-optimization)
4. [Network Tuning](#network-tuning)
5. [Monitoring and Profiling](#monitoring-and-profiling)
6. [Troubleshooting Performance Issues](#troubleshooting-performance-issues)

## System Configuration

### CPU Optimization
- **Worker Processes**: Set worker count to match CPU cores
  ```yaml
  workers: auto  # Auto-detects CPU cores
  # Or explicitly: workers: 8
  ```
- **CPU Affinity**: Pin workers to specific cores to improve cache locality
- **Process Priority**: Consider using `nice` or `renice` for production workloads

### Memory Management
- **Buffer Sizes**: Optimize buffer sizes for your workload
  ```yaml
  buffer_size: 8192  # 8KB default
  max_buffer_size: 65536  # 64KB max
  ```
- **Connection Pool**: Configure connection pooling
  ```yaml
  connection_pool:
    min_size: 10
    max_size: 100
    timeout: 30
  ```

### Event Loop Configuration
- **Use uvloop**: Enable uvloop for faster async operations (Linux/macOS)
  ```python
  import uvloop
  uvloop.install()
  ```
- **Backlog Size**: Increase socket backlog for high-traffic scenarios
  ```yaml
  backlog: 2048
  ```

## Load Balancer Configuration

### Algorithm Selection
Choose the right algorithm for your use case:

| Algorithm | Best For | Pros | Cons |
|-----------|----------|------|------|
| Round Robin | Uniform servers | Simple, fair | Doesn't account for load |
| Least Connections | Variable loads | Adapts to load | Slightly more overhead |
| Weighted Round Robin | Mixed capacity | Handles heterogeneous backends | Requires manual tuning |
| IP Hash | Session persistence | Consistent routing | Uneven distribution |
| Least Response Time | Latency-sensitive | Optimizes latency | Requires health checks |

### Health Check Configuration
```yaml
health_checks:
  enabled: true
  interval: 10  # seconds
  timeout: 5    # seconds
  unhealthy_threshold: 3
  healthy_threshold: 2
  check_type: http  # http, tcp, or custom
  path: /health
```

**Performance Tips:**
- Increase intervals for stable backends to reduce overhead
- Use TCP checks instead of HTTP for performance-critical scenarios
- Implement custom health checks with caching

### Connection Settings
```yaml
connection_settings:
  keep_alive: true
  keep_alive_timeout: 75
  max_requests_per_connection: 1000
  tcp_nodelay: true  # Disable Nagle's algorithm
  tcp_quickack: true  # Linux only
```

## Backend Server Optimization

### Backend Pool Configuration
```yaml
backends:
  - host: backend1.example.com
    port: 8080
    weight: 100
    max_connections: 500
  - host: backend2.example.com
    port: 8080
    weight: 150  # Higher capacity server
    max_connections: 750
```

### Timeouts
Configure appropriate timeouts to prevent resource exhaustion:

```yaml
timeouts:
  connect: 5      # Connection establishment
  read: 30        # Reading response
  write: 30       # Writing request
  keepalive: 75   # Keep-alive connections
```

## Network Tuning

### Linux Kernel Parameters
Add to `/etc/sysctl.conf`:

```bash
# Increase socket buffer sizes
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 67108864
net.ipv4.tcp_wmem = 4096 65536 67108864

# Increase connection backlog
net.core.somaxconn = 4096
net.ipv4.tcp_max_syn_backlog = 8192

# Enable TCP fast open
net.ipv4.tcp_fastopen = 3

# Increase local port range
net.ipv4.ip_local_port_range = 10000 65535

# Enable TCP window scaling
net.ipv4.tcp_window_scaling = 1

# Reduce TIME_WAIT sockets
net.ipv4.tcp_fin_timeout = 15
net.ipv4.tcp_tw_reuse = 1
```

Apply changes:
```bash
sudo sysctl -p
```

### Network Interface Tuning
```bash
# Increase network interface queue length
sudo ifconfig eth0 txqueuelen 5000

# Enable receive packet steering (RPS)
echo f > /sys/class/net/eth0/queues/rx-0/rps_cpus
```

## Monitoring and Profiling

### Prometheus Metrics
Enable Prometheus metrics for monitoring:

```yaml
monitoring:
  prometheus:
    enabled: true
    port: 9090
    path: /metrics
```

**Key Metrics to Monitor:**
- `request_duration_seconds` - Request latency
- `active_connections` - Current connections
- `backend_response_time` - Backend latency
- `error_rate` - Error percentage
- `requests_per_second` - Throughput

### Profiling Tools

**Python Profiling:**
```python
# Use cProfile for CPU profiling
python -m cProfile -o profile.stats ultrabalancer.py

# Use memory_profiler for memory analysis
@profile
def load_balance_request(request):
    # Your code here
    pass
```

**System Profiling:**
```bash
# CPU profiling with perf
sudo perf record -g -p <pid>
sudo perf report

# Network analysis with tcpdump
sudo tcpdump -i eth0 -w capture.pcap
```

## Troubleshooting Performance Issues

### High Latency
**Symptoms:** Slow response times

**Solutions:**
1. Check backend health and response times
2. Review health check intervals (reduce overhead)
3. Analyze network latency with `ping` and `traceroute`
4. Enable connection keep-alive
5. Use connection pooling

### High CPU Usage
**Symptoms:** CPU constantly at 100%

**Solutions:**
1. Increase worker processes
2. Profile code to find hotspots
3. Optimize algorithm selection
4. Reduce health check frequency
5. Enable uvloop for better performance

### Memory Leaks
**Symptoms:** Growing memory usage over time

**Solutions:**
1. Monitor with `memory_profiler`
2. Check for unclosed connections
3. Review session cache size limits
4. Use `objgraph` to find reference cycles
5. Implement connection timeouts

### Connection Exhaustion
**Symptoms:** "Too many open files" errors

**Solutions:**
1. Increase file descriptor limits:
   ```bash
   ulimit -n 65535
   ```
2. Configure max connections per backend
3. Implement connection pooling
4. Reduce keep-alive timeout
5. Review and close idle connections

## Performance Benchmarking

### Load Testing with Locust
```python
from locust import HttpUser, task, between

class LoadBalancerUser(HttpUser):
    wait_time = between(0.5, 2.0)
    
    @task
    def index(self):
        self.client.get("/")
    
    @task(3)
    def api_endpoint(self):
        self.client.get("/api/data")
```

Run benchmark:
```bash
locust -f locustfile.py --host=http://loadbalancer.example.com
```

### Apache Bench (ab)
```bash
ab -n 10000 -c 100 http://loadbalancer.example.com/
```

### wrk
```bash
wrk -t12 -c400 -d30s http://loadbalancer.example.com/
```

## Best Practices Summary

1. ✅ **Match workers to CPU cores** for optimal parallelism
2. ✅ **Enable uvloop** for better async performance on Linux/macOS
3. ✅ **Use connection pooling** to reduce overhead
4. ✅ **Tune kernel parameters** for high-throughput scenarios
5. ✅ **Monitor key metrics** with Prometheus and Grafana
6. ✅ **Choose the right algorithm** for your traffic pattern
7. ✅ **Optimize health checks** to balance reliability and overhead
8. ✅ **Enable keep-alive** for HTTP connections
9. ✅ **Set appropriate timeouts** to prevent resource exhaustion
10. ✅ **Profile regularly** to identify bottlenecks

## Additional Resources

- [Architecture Documentation](architecture.md)
- [Configuration Guide](configuration.md)
- [API Reference](api.md)
- [Deployment Guide](deployment.md)

## Support

For performance-related questions or issues:
- Open an issue on GitHub
- Join our community Slack channel
- Review existing performance discussions
