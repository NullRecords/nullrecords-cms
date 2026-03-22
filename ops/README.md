# NullRecords – ops/

Unified service manager for the NullRecords development stack.

## Quick Start

```bash
bash ops/startup.sh start     # start all services
bash ops/startup.sh stop      # stop all services
bash ops/startup.sh restart   # restart all services
bash ops/startup.sh status    # show running services
```

## Services

| Service      | Default Port | Description                              |
|--------------|-------------|------------------------------------------|
| **forgeweb** | 8100        | Website builder & admin (Python HTTP)    |
| **ai-engine**| 8200        | FastAPI media & outreach platform        |
| **dashboard**| 8300        | Daily reports & analytics (static HTTP)  |

Ports auto-increment if busy (tries up to +20 from default).

## Files

- `startup.sh` — Main service manager script
- `dashboard.html` — Generated dev dashboard with preview links (created on `start`)
- `.pids/` — PID and port files for running services
- `logs/` — stdout/stderr logs for each service

## How It Works

1. **start** finds the first free port starting from each service's default
2. Launches each service as a background process, storing PIDs
3. Generates `dashboard.html` with live links to every running service
4. **stop** reads stored PIDs and sends SIGTERM
5. **status** checks if PIDs are still alive and reports ports
