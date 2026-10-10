# Project time tracking

Use [`scripts/time_tracking.py`](scripts/time_tracking.py) to keep an append-only JSONL log and produce report-ready totals.

```bash
python scripts/time_tracking.py add --hours 2.5 --note "Gateway work"
python scripts/time_tracking.py start --note "Benchmark preparation"
python scripts/time_tracking.py stop
python scripts/time_tracking.py report --format json
```

The default workday is 8 hours. Reports contain `hours`, exact `days_exact`, and separately rounded `days_rounded` (half-up); use `--hours-per-day` for another workday length. The default log is `time-log.jsonl`, and timer state stays outside the repository.
