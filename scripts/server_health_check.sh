#!/usr/bin/env bash
# Pre-rush server health check - read-only, safe to run anytime.
# Paste directly into an SSH session on the production box, or run it there:
#   bash scripts/server_health_check.sh
#
# Sections that print nothing/errors need the right binary or connection args
# for that specific box (e.g. psql -U/-h/-d) - fill in and rerun that section.
#
# One thing this script does NOT check but is worth checking separately before
# a rush: the Celery queue backlog. The worker runs at concurrency=1 on this
# same box (see registrations/tasks.py) - a backlog that's already growing
# before the rush even starts won't resolve itself once it does:
#   celery -A sportfac inspect active
#   celery -A sportfac inspect reserved
#   celery -A sportfac inspect stats

echo "===== CPU ====="
echo "Cores: $(nproc 2>/dev/null || sysctl -n hw.ncpu)"
echo "Load average (1m 5m 15m):"
uptime
echo
echo "Top CPU consumers:"
ps -eo pid,pcpu,pmem,etime,cmd --sort=-pcpu 2>/dev/null | head -11 || ps aux | sort -rk3 | head -11

echo
echo "===== RAM ====="
free -h 2>/dev/null || vm_stat
echo
echo "Swap:"
swapon --show 2>/dev/null || sysctl vm.swapusage 2>/dev/null

echo
echo "===== DISK ====="
df -h

echo
echo "===== PROCESSES / LIMITS ====="
echo "Current process count: $(ps -e | wc -l)"
echo "Process limit (ulimit -u): $(ulimit -u)"
echo "Open file descriptors in use: $(lsof 2>/dev/null | wc -l)"
echo "File descriptor limit (ulimit -n): $(ulimit -n)"
echo "System-wide file-max:"
cat /proc/sys/fs/file-max 2>/dev/null

echo
echo "===== SUPERVISOR (app + celery workers) ====="
supervisorctl status 2>/dev/null || echo "supervisorctl not found / not on PATH - check manually"

echo
echo "===== POSTGRESQL ====="
echo "Active connections vs max (needs DB access - adjust connection args as needed):"
psql -U postgres -c "SELECT count(*) AS active_connections FROM pg_stat_activity;" 2>/dev/null
psql -U postgres -c "SHOW max_connections;" 2>/dev/null
echo "(run manually with the right -U/-h/-d if the above didn't connect)"

echo
echo "===== REDIS ====="
redis-cli INFO memory 2>/dev/null | grep -E "used_memory_human|maxmemory_human|maxmemory_policy"
redis-cli INFO clients 2>/dev/null | grep -E "connected_clients|blocked_clients"

echo
echo "===== NETWORK ====="
echo "Established connections by port (top 15):"
ss -tn 2>/dev/null | awk 'NR>1 {print $4}' | sed -E 's/.*:([0-9]+)$/\1/' | sort | uniq -c | sort -rn | head -15 \
  || netstat -an | grep ESTABLISHED | awk '{print $4}' | sed -E 's/.*\.([0-9]+)$/\1/' | sort | uniq -c | sort -rn | head -15

echo
echo "===== DONE ====="
