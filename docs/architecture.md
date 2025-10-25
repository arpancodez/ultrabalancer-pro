# UltraBalancer Pro Architecture

## Overview
UltraBalancer Pro is a high-performance, async-first load balancer with a modular architecture:
- Core Router: request routing, algorithm selection, backends state
- Health Checker: active/passive checks with retries/backoff
- Metrics Exporter: unified metrics layer, pluggable exporters (Prometheus, StatsD)
- Plugins: algorithms, middleware, and hooks system
- Config: YAML-based runtime configuration

## High-level Diagram

```
           ┌────────────────────────────┐
           │        Entrypoint          │
           │   (HTTP/TCP/WebSocket)     │
           └─────────────┬──────────────┘
                         │
                  ┌──────▼───────┐
                  │   Router     │  Async event loop
                  │ (core)       │─────────────────────┐
                  └───┬─────┬────┘                     │
                      │     │                          │
              ┌───────▼──┐  │                   ┌──────▼─────────┐
              │Algorithms│  │                   │ Metrics        │
              │(plugins) │  │                   │ Exporter       │
              └───────┬──┘  │                   └──────┬─────────┘
                      │     │                          │
                      │     │                          │
                ┌─────▼─────▼───┐                ┌─────▼────────────┐
                │ Health Checker │<──────────────▶ Observability     │
                │ (active/passive)               │ (Prometheus etc.) │
                └─────┬──────────┘                └──────────────────┘
                      │
         ┌────────────▼────────────┐
         │     Backend Pool        │
         │  (instances/services)   │
         └─────────────────────────┘
```

## Core Router
- Selects backend via configured algorithm
- Maintains in-flight counters, per-backend stats
- Integrates with health checker and metrics exporter
- Graceful shutdown and draining

## Health Checker
- Async probes (HTTP/TCP) with timeouts
- Smarter retry strategy with exponential backoff and jitter
- Healthy/Unhealthy thresholds
- Emits events for state changes, updates router/metrics

## Metrics Exporter
- Counters: requests, errors, retries, circuit opens
- Histograms: request latency, backend RTT
- Gauges: in-flight requests, healthy backends, CPU/memory

## Plugins System
- Algorithms: drop-in routing strategies (e.g., ML adaptive)
- Middleware: request/response hooks
- Loader: dynamic discovery and hot-reload ready

## Data Flow
1. Request arrives at Router
2. Router filters healthy backends
3. Algorithm selects target backend
4. Request proxied to backend
5. Metrics logged; plugin hooks invoked
6. Health checker updates state asynchronously

## Error Handling
- Centralized async error logging with context
- Circuit breaker to prevent cascading failures
- Retries with capped backoff and jitter

## Future Enhancements
- gRPC/HTTP3 support
- Advanced ML models and feature store
- Control plane for distributed coordination
