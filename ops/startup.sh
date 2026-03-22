#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────
#  NullRecords – Unified Service Manager
#  Usage:  ./ops/startup.sh  start | stop | restart | status
# ──────────────────────────────────────────────────────────
set -euo pipefail

# ── Paths (relative to repo root) ────────────────────────
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PID_DIR="$REPO_ROOT/ops/.pids"
LOG_DIR="$REPO_ROOT/ops/logs"
DASHBOARD_HTML="$REPO_ROOT/ops/dashboard.html"

FORGEWEB_DIR="$REPO_ROOT/forgeweb"
AI_ENGINE_DIR="$REPO_ROOT/ai-engine"
DASHBOARD_DIR="$REPO_ROOT/dashboard"

# ── Default ports (will be bumped if busy) ────────────────
FORGEWEB_PORT=8100
AI_ENGINE_PORT=8200
DASHBOARD_PORT=8300

# ── Colors ────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m' # no color

# ── Helpers ───────────────────────────────────────────────

banner() {
  echo ""
  echo -e "${CYAN}╔══════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║${NC}  ${BOLD}NullRecords Service Manager${NC}                  ${CYAN}║${NC}"
  echo -e "${CYAN}╚══════════════════════════════════════════════╝${NC}"
  echo ""
}

port_is_free() {
  # Returns 0 (true) if port is available
  ! lsof -iTCP:"$1" -sTCP:LISTEN >/dev/null 2>&1
}

find_free_port() {
  local port="$1"
  local max=$(( port + 20 ))
  while [ "$port" -lt "$max" ]; do
    if port_is_free "$port"; then
      echo "$port"
      return 0
    fi
    port=$(( port + 1 ))
  done
  echo ""
  return 1
}

ensure_dirs() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
}

read_pid() {
  local name="$1"
  local pidfile="$PID_DIR/${name}.pid"
  if [ -f "$pidfile" ]; then
    cat "$pidfile"
  fi
}

is_running() {
  local pid
  pid="$(read_pid "$1")"
  [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null
}

read_port() {
  local name="$1"
  local portfile="$PID_DIR/${name}.port"
  if [ -f "$portfile" ]; then
    cat "$portfile"
  fi
}

# ── Start individual services ────────────────────────────

start_forgeweb() {
  if is_running forgeweb; then
    local p; p="$(read_port forgeweb)"
    echo -e "  ${YELLOW}forgeweb${NC} already running on port ${BOLD}$p${NC}"
    return 0
  fi

  local port
  port="$(find_free_port "$FORGEWEB_PORT")"
  if [ -z "$port" ]; then
    echo -e "  ${RED}✗${NC} No free port for forgeweb (tried $FORGEWEB_PORT–$(( FORGEWEB_PORT + 19 )))"
    return 1
  fi

  # Ensure forgeweb venv exists
  if [ ! -d "$FORGEWEB_DIR/.venv" ]; then
    echo -e "  ${YELLOW}⟳${NC} Creating forgeweb virtualenv …"
    python3 -m venv "$FORGEWEB_DIR/.venv"
    "$FORGEWEB_DIR/.venv/bin/pip" install -q -r "$FORGEWEB_DIR/requirements.txt"
  fi

  local fw_py="$FORGEWEB_DIR/.venv/bin/python"

  echo -e "  Starting ${BOLD}forgeweb${NC} on port ${CYAN}$port${NC} …"
  cd "$FORGEWEB_DIR"
  nohup "$fw_py" admin/file-api.py --port "$port" \
    > "$LOG_DIR/forgeweb.log" 2>&1 &
  local pid=$!
  echo "$pid" > "$PID_DIR/forgeweb.pid"
  echo "$port" > "$PID_DIR/forgeweb.port"
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} forgeweb        → ${BOLD}http://localhost:${port}/admin/${NC}"
  else
    echo -e "  ${RED}✗${NC} forgeweb failed to start — see $LOG_DIR/forgeweb.log"
  fi
}

start_ai_engine() {
  if is_running ai-engine; then
    local p; p="$(read_port ai-engine)"
    echo -e "  ${YELLOW}ai-engine${NC} already running on port ${BOLD}$p${NC}"
    return 0
  fi

  local port
  port="$(find_free_port "$AI_ENGINE_PORT")"
  if [ -z "$port" ]; then
    echo -e "  ${RED}✗${NC} No free port for ai-engine (tried $AI_ENGINE_PORT–$(( AI_ENGINE_PORT + 19 )))"
    return 1
  fi

  # Ensure venv exists
  if [ ! -d "$AI_ENGINE_DIR/.venv" ]; then
    echo -e "  ${YELLOW}⟳${NC} Creating ai-engine virtualenv …"
    python3 -m venv "$AI_ENGINE_DIR/.venv"
    "$AI_ENGINE_DIR/.venv/bin/pip" install -q -r "$AI_ENGINE_DIR/requirements.txt"
  fi

  local py="$AI_ENGINE_DIR/.venv/bin/python"

  echo -e "  Starting ${BOLD}ai-engine${NC} on port ${CYAN}$port${NC} …"
  cd "$AI_ENGINE_DIR"
  nohup "$py" -m uvicorn app.main:app --host 127.0.0.1 --port "$port" \
    > "$LOG_DIR/ai-engine.log" 2>&1 &
  local pid=$!
  echo "$pid" > "$PID_DIR/ai-engine.pid"
  echo "$port" > "$PID_DIR/ai-engine.port"
  sleep 2
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} ai-engine       → ${BOLD}http://localhost:${port}/docs${NC}"
    echo -e "                      ${BOLD}http://localhost:${port}/admin${NC}"
  else
    echo -e "  ${RED}✗${NC} ai-engine failed to start — see $LOG_DIR/ai-engine.log"
  fi
}

start_dashboard() {
  if is_running dashboard; then
    local p; p="$(read_port dashboard)"
    echo -e "  ${YELLOW}dashboard${NC} already running on port ${BOLD}$p${NC}"
    return 0
  fi

  local port
  port="$(find_free_port "$DASHBOARD_PORT")"
  if [ -z "$port" ]; then
    echo -e "  ${RED}✗${NC} No free port for dashboard (tried $DASHBOARD_PORT–$(( DASHBOARD_PORT + 19 )))"
    return 1
  fi

  echo -e "  Starting ${BOLD}dashboard${NC} on port ${CYAN}$port${NC} …"
  cd "$DASHBOARD_DIR"
  nohup python3 -m http.server "$port" --bind 127.0.0.1 \
    > "$LOG_DIR/dashboard.log" 2>&1 &
  local pid=$!
  echo "$pid" > "$PID_DIR/dashboard.pid"
  echo "$port" > "$PID_DIR/dashboard.port"
  sleep 1
  if kill -0 "$pid" 2>/dev/null; then
    echo -e "  ${GREEN}✓${NC} dashboard       → ${BOLD}http://localhost:${port}/daily_report_latest.html${NC}"
  else
    echo -e "  ${RED}✗${NC} dashboard failed to start — see $LOG_DIR/dashboard.log"
  fi
}

# ── Stop ──────────────────────────────────────────────────

stop_service() {
  local name="$1"
  if is_running "$name"; then
    local pid; pid="$(read_pid "$name")"
    kill "$pid" 2>/dev/null && echo -e "  ${GREEN}✓${NC} Stopped ${BOLD}$name${NC} (pid $pid)"
    rm -f "$PID_DIR/${name}.pid" "$PID_DIR/${name}.port"
  else
    echo -e "  ${YELLOW}—${NC} $name is not running"
    rm -f "$PID_DIR/${name}.pid" "$PID_DIR/${name}.port"
  fi
}

stop_all() {
  echo -e "${BOLD}Stopping services …${NC}"
  stop_service forgeweb
  stop_service ai-engine
  stop_service dashboard
  echo ""
}

# ── Status ────────────────────────────────────────────────

status_all() {
  echo -e "${BOLD}Service Status${NC}"
  echo -e "─────────────────────────────────────────────"
  for svc in forgeweb ai-engine dashboard; do
    if is_running "$svc"; then
      local p; p="$(read_port "$svc")"
      local pid; pid="$(read_pid "$svc")"
      echo -e "  ${GREEN}●${NC}  ${BOLD}$svc${NC}  pid=$pid  port=$p"
    else
      echo -e "  ${RED}●${NC}  ${BOLD}$svc${NC}  stopped"
    fi
  done
  echo ""
}

# ── Dashboard HTML with preview links ────────────────────

generate_dashboard_html() {
  local fw_port; fw_port="$(read_port forgeweb)"
  local ai_port; ai_port="$(read_port ai-engine)"
  local db_port; db_port="$(read_port dashboard)"

  # Pre-compute status strings
  local fw_badge="stopped" fw_label="STOPPED"
  local ai_badge="stopped" ai_label="STOPPED"
  local db_badge="stopped" db_label="STOPPED"
  local fw_links="" ai_links="" db_links=""

  if [ -n "$fw_port" ]; then
    fw_badge="running"; fw_label="RUNNING"
    fw_links="<a class=\"link\" href=\"http://localhost:${fw_port}/admin/\" target=\"_blank\">ADMIN</a>
    <a class=\"link\" href=\"http://localhost:${fw_port}/\" target=\"_blank\">SITE PREVIEW</a>
    <p style=\"color:#555;font-size:0.65rem;margin-top:0.5rem;\">http://localhost:${fw_port}</p>"
  fi
  if [ -n "$ai_port" ]; then
    ai_badge="running"; ai_label="RUNNING"
    ai_links="<a class=\"link\" href=\"http://localhost:${ai_port}/admin\" target=\"_blank\">ADMIN</a>
    <a class=\"link\" href=\"http://localhost:${ai_port}/docs\" target=\"_blank\">API DOCS</a>
    <a class=\"link\" href=\"http://localhost:${ai_port}/system/health\" target=\"_blank\">HEALTH</a>
    <p style=\"color:#555;font-size:0.65rem;margin-top:0.5rem;\">http://localhost:${ai_port}</p>"
  fi
  if [ -n "$db_port" ]; then
    db_badge="running"; db_label="RUNNING"
    db_links="<a class=\"link\" href=\"http://localhost:${db_port}/daily_report_latest.html\" target=\"_blank\">LATEST REPORT</a>
    <a class=\"link\" href=\"http://localhost:${db_port}/daily_reports/\" target=\"_blank\">ALL REPORTS</a>
    <p style=\"color:#555;font-size:0.65rem;margin-top:0.5rem;\">http://localhost:${db_port}</p>"
  fi

  local gen_date; gen_date="$(date '+%Y-%m-%d %H:%M:%S')"

  cat > "$DASHBOARD_HTML" <<HTMLEOF
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NullRecords – Dev Dashboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'JetBrains Mono', 'Fira Code', monospace;
      background: #0a0a0a; color: #e0e0e0;
      display: flex; align-items: center; justify-content: center;
      min-height: 100vh;
    }
    .container { max-width: 640px; width: 100%; padding: 2rem; }
    h1 {
      font-family: 'Press Start 2P', monospace;
      color: #00ffff; font-size: 1rem; text-align: center;
      margin-bottom: 0.5rem; letter-spacing: 2px;
    }
    .subtitle {
      text-align: center; color: #666; font-size: 0.75rem;
      margin-bottom: 2rem;
    }
    .card {
      background: #1a1a1a; border: 1px solid #333;
      border-radius: 8px; padding: 1.25rem 1.5rem;
      margin-bottom: 1rem; transition: border-color 0.2s;
    }
    .card:hover { border-color: #00ffff; }
    .card h2 {
      font-size: 0.85rem; margin-bottom: 0.5rem;
      display: flex; align-items: center; gap: 0.5rem;
    }
    .card p { color: #888; font-size: 0.75rem; margin-bottom: 0.75rem; }
    .badge {
      display: inline-block; font-size: 0.6rem; padding: 2px 8px;
      border-radius: 4px; font-weight: bold; text-transform: uppercase;
    }
    .badge.running { background: #00ff4133; color: #00ff41; }
    .badge.stopped { background: #ff575833; color: #ff5758; }
    a.link {
      display: inline-block; color: #00ffff; font-size: 0.75rem;
      text-decoration: none; border: 1px solid #00ffff44;
      padding: 4px 12px; border-radius: 4px; margin-right: 0.5rem;
      transition: background 0.2s;
    }
    a.link:hover { background: #00ffff22; }
    .footer {
      text-align: center; color: #444; font-size: 0.65rem;
      margin-top: 2rem;
    }
  </style>
</head>
<body>
<div class="container">
  <h1>NULLRECORDS_DEV</h1>
  <p class="subtitle">local service dashboard</p>

  <div class="card">
    <h2>ForgeWeb <span class="badge ${fw_badge}">${fw_label}</span></h2>
    <p>Website builder &amp; admin &bull; Python HTTP Server</p>
    ${fw_links}
  </div>

  <div class="card">
    <h2>AI Engine <span class="badge ${ai_badge}">${ai_label}</span></h2>
    <p>FastAPI media &amp; outreach platform</p>
    ${ai_links}
  </div>

  <div class="card">
    <h2>Dashboard <span class="badge ${db_badge}">${db_label}</span></h2>
    <p>Daily reports, analytics &amp; monitoring</p>
    ${db_links}
  </div>

  <div class="footer">NullRecords Dev Dashboard &bull; Generated ${gen_date}</div>
</div>
</body>
</html>
HTMLEOF

  echo -e "  ${GREEN}✓${NC} Dashboard HTML → ${BOLD}$DASHBOARD_HTML${NC}"
}

# ── Main ──────────────────────────────────────────────────

main() {
  ensure_dirs
  banner

  case "${1:-}" in

    start)
      echo -e "${BOLD}Starting services …${NC}"
      echo ""
      start_forgeweb
      start_ai_engine
      start_dashboard
      echo ""
      generate_dashboard_html
      echo ""
      echo -e "${BOLD}All services started.${NC}  Open the dev dashboard:"
      echo -e "  ${CYAN}open $DASHBOARD_HTML${NC}"
      echo ""
      status_all
      ;;

    stop)
      stop_all
      ;;

    restart)
      stop_all
      sleep 1
      echo -e "${BOLD}Starting services …${NC}"
      echo ""
      start_forgeweb
      start_ai_engine
      start_dashboard
      echo ""
      generate_dashboard_html
      echo ""
      echo -e "${BOLD}All services restarted.${NC}"
      echo ""
      status_all
      ;;

    status)
      status_all
      ;;

    *)
      echo "Usage: $0 {start|stop|restart|status}"
      exit 1
      ;;
  esac
}

main "$@"
