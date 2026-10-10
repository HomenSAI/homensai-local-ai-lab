#!/bin/sh
# Entrypoint of the bench-runner container (docker compose --profile bench up -d bench-runner; restart: unless-stopped).
# The runners are copied next to the results in bench_results/ (the layout the report builder expects: it reads the
# model list from bench_results/bench_top.py). Every phase skips finished work, so after a crash or reboot the run
# continues from the last step. Each phase writes the log and the finish marker of its stage in DEFAULT_PLAN
# (scripts/build_live_report.py), so the console shows progress.
# Phases: BENCH_PHASES="general german context german_fix accel stem chem code20" (default); soak needs the gateway
# and runs only when listed.
cd /ai-server/bench_results || exit 1
export PYTHONIOENCODING=utf-8 PYTHONUTF8=1
cp /ai-server/benchmarks/*.py .
python make_images.py
PHASES=${BENCH_PHASES:-general german context german_fix accel stem chem code20}
STAMP=$(echo "$PHASES" | tr ' ' '-')
if grep -q "ALL-PHASES-FINISHED $STAMP" run_all.log 2>/dev/null; then echo "all phases finished: $PHASES"; exec sleep infinity; fi
docker rm -f bench-srv >/dev/null 2>&1
echo "$(date) start: $PHASES" >> run_all.log
for phase in $PHASES; do
  case $phase in
    general)    docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u bench_top.py --skip-done >> bench_full.log 2>&1 ;;
    german)     docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u german_all.py --skip-done >> german_all.log 2>&1 ;;
    context)    docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u bench_ctx.py --skip-done >> bench_ctx.log 2>&1 ;;
    german_fix) docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u german_fix.py >> german_fix.log 2>&1 ;;
    accel)      docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u bench_accel.py all >> bench_accel.log 2>&1 ;;
    stem)       docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u bench_stem.py >> bench_stem.log 2>&1 ;;
    chem)       docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u bench_chem.py >> bench_chem.log 2>&1 ;;
    code20)     docker stop ai-llama-swap-gateway >/dev/null 2>&1; python -u bench_code20.py >> bench_code20.log 2>&1 ;;
    soak)       docker rm -f bench-srv >/dev/null 2>&1; docker start ai-llama-swap-gateway >/dev/null 2>&1; python -u soak.py >> soak.log 2>&1 ;;
    *)          echo "$(date) unknown phase: $phase" >> run_all.log ;;
  esac
  echo "$(date) phase $phase ended (exit $?)" >> run_all.log
done
echo "$(date) ALL-PHASES-FINISHED $STAMP" >> run_all.log
exec sleep infinity
