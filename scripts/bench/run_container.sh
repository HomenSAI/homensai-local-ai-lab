#!/bin/sh
# Container entrypoint (restart: unless-stopped). Every phase skips finished work -> after a crash/reboot it continues from the last step.
cd /ai-server/bench_results
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
if grep -q ALL-PHASES-FINISHED run_all.log 2>/dev/null; then echo "all phases finished"; exec sleep infinity; fi
docker rm -f bench-srv >/dev/null 2>&1
docker start cache-dropper >/dev/null 2>&1
docker stop ai-llama-swap-gateway >/dev/null 2>&1
echo "$(date) start" >> run_all.log
python -u bench_ctx.py --skip-done >> bench_ctx.log 2>&1
python -u german_fix.py >> german_fix.log 2>&1
python -u bench_accel.py all >> bench_accel.log 2>&1
python -u bench_stem.py >> bench_stem.log 2>&1
echo "$(date) ALL-PHASES-FINISHED" >> run_all.log
exec sleep infinity
