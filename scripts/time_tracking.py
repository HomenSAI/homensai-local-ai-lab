#!/usr/bin/env python3
"""Project time tracking in hours and rounded working days.

  python scripts/time_tracking.py add --hours 2.5 --note "Work"
  python scripts/time_tracking.py start --note "Work"; python scripts/time_tracking.py stop
  python scripts/time_tracking.py report --format json

The JSONL log defaults to reports/time-log.jsonl. The active timer state is
stored outside the repository. A working day is 8 hours by default; use
--hours-per-day to change it. Rounding is half-up to a whole day.
"""

from __future__ import annotations
import argparse, json, math, os, subprocess, sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from typing import Any
SCHEMA_VERSION=1
def root_dir(): return Path(__file__).resolve().parents[1]
def project_name(root):
    try:
        value=subprocess.run(["git","config","--get","remote.origin.url"],cwd=root,capture_output=True,text=True,check=False).stdout.strip().rstrip("/")
        if value: return value.rsplit("/",1)[-1].removesuffix(".git")
    except OSError: pass
    return root.name
def default_log(root):
    configured=os.environ.get("HOMENSAI_TIME_LOG")
    if configured: return Path(configured).expanduser()
    return root/"time-log.jsonl"
def default_state(name):
    configured=os.environ.get("HOMENSAI_TIME_STATE_DIR"); directory=Path(configured).expanduser() if configured else Path.home()/".homenSAI-time-tracking"; return directory/f"{name}.session.json"
def date_value(value):
    try: return datetime.strptime(value,"%Y-%m-%d").date().isoformat()
    except ValueError as exc: raise argparse.ArgumentTypeError("date must be YYYY-MM-DD") from exc
def hours_value(value):
    try: number=float(value)
    except ValueError as exc: raise argparse.ArgumentTypeError("hours must be a number") from exc
    if not math.isfinite(number) or number<0: raise argparse.ArgumentTypeError("hours must be finite and non-negative")
    return number
def now(): return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
def head(root):
    try: return subprocess.run(["git","rev-parse","--short","HEAD"],cwd=root,capture_output=True,text=True,check=False).stdout.strip() or None
    except OSError: return None
def entries(path):
    if not path.exists(): return []
    result=[]
    for number,line in enumerate(path.read_text(encoding="utf-8").splitlines(),1):
        if not line.strip() or line.lstrip().startswith("#"): continue
        try: item=json.loads(line)
        except json.JSONDecodeError as exc: raise ValueError(f"invalid JSON at {path}:{number}: {exc}") from exc
        if item.get("type")=="meta": continue
        if "hours" not in item or "date" not in item: raise ValueError(f"{path}:{number} needs date and hours")
        item["hours"],item["date"]=hours_value(str(item["hours"])),date_value(str(item["date"])); result.append(item)
    return result
def append(path,item):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open("a",encoding="utf-8",newline="\n") as stream: stream.write(json.dumps(item,ensure_ascii=False,sort_keys=True)+"\n")
def summary(rows,per_day,since,until):
    unit=Decimal(str(per_day))
    if unit<=0: raise ValueError("--hours-per-day must be greater than zero")
    rows=[row for row in rows if (since is None or row["date"]>=since) and (until is None or row["date"]<=until)]; total=sum((Decimal(str(row["hours"])) for row in rows),Decimal("0")); dates=[row["date"] for row in rows]
    return {"schema_version":SCHEMA_VERSION,"project":rows[0].get("project") if rows else None,"entries":len(rows),"hours":float(total.quantize(Decimal("0.01"))),"days_exact":float((total/unit).quantize(Decimal("0.01"))),"days_rounded":int((total/unit).quantize(Decimal("1"),rounding=ROUND_HALF_UP)),"hours_per_day":float(unit),"period_start":min(dates) if dates else since,"period_end":max(dates) if dates else until}
def render(data,fmt):
    if fmt=="json": return json.dumps(data,ensure_ascii=False,indent=2)
    if fmt=="text": return f"Project: {data.get('project') or 'project'}\nHours: {data['hours']:.2f}\nDays at {data['hours_per_day']:g} h: {data['days_exact']:.2f}\nRounded days: {data['days_rounded']}\nEntries: {data['entries']}"
    return f"# Time report: {data.get('project') or 'project'}\n\n| Metric | Value |\n|---|---:|\n| Hours | {data['hours']:.2f} |\n| Days at {data['hours_per_day']:g} h | {data['days_exact']:.2f} |\n| Rounded days | {data['days_rounded']} |\n| Entries | {data['entries']} |\n| Period | {data.get('period_start') or '—'} — {data.get('period_end') or '—'} |"
def make_parser():
    p=argparse.ArgumentParser(description="Project time tracking in hours and working days."); p.add_argument("--log",type=Path); p.add_argument("--state",type=Path); p.add_argument("--hours-per-day",type=hours_value,default=8.0); p.add_argument("--since",type=date_value); p.add_argument("--until",type=date_value)
    s=p.add_subparsers(dest="action",required=True); a=s.add_parser("add"); a.add_argument("--hours",required=True,type=hours_value); a.add_argument("--date",type=date_value,default=datetime.now().date().isoformat()); a.add_argument("--note",default=""); b=s.add_parser("start"); b.add_argument("--note",default=""); s.add_parser("stop"); s.add_parser("status"); t=s.add_parser("total"); t.add_argument("--format",choices=("text","json"),default="text"); r=s.add_parser("report"); r.add_argument("--format",choices=("text","json","markdown"),default="markdown"); r.add_argument("--output",type=Path); return p
def main(argv=None):
    args=make_parser().parse_args(argv); root=root_dir(); name=project_name(root); log=args.log.expanduser() if args.log else default_log(root); state=args.state.expanduser() if args.state else default_state(name)
    try:
        if args.action=="add": append(log,{"schema_version":SCHEMA_VERSION,"project":name,"date":args.date,"hours":args.hours,"note":args.note,"source":"manual","recorded_at":now(),"commit":head(root)}); print(f"Added {args.hours:.2f} h to {log}"); return 0
        if args.action=="start":
            if state.exists(): raise ValueError(f"active session exists: {state}")
            state.parent.mkdir(parents=True,exist_ok=True); state.write_text(json.dumps({"project":name,"started_at":now(),"note":args.note},ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); print(f"Session started: {state}"); return 0
        if args.action=="status": print(state.read_text(encoding="utf-8").strip() if state.exists() else "No active session."); return 0
        if args.action=="stop":
            if not state.exists(): raise ValueError("no active session")
            saved=json.loads(state.read_text(encoding="utf-8")); started=datetime.fromisoformat(saved["started_at"].replace("Z","+00:00")); ended_at=now(); ended=datetime.fromisoformat(ended_at.replace("Z","+00:00")); worked=max(0.0,(ended-started).total_seconds()/3600)
            append(log,{"schema_version":SCHEMA_VERSION,"project":name,"date":started.date().isoformat(),"hours":round(worked,4),"note":saved.get("note",""),"source":"timer","started_at":saved["started_at"],"ended_at":ended_at,"commit":head(root)}); state.unlink(); print(f"Recorded {worked:.2f} h in {log}"); return 0
        data=summary(entries(log),args.hours_per_day,args.since,args.until); text=render(data,args.format)
        if args.action=="total": print(text); return 0
        if args.output:
            target=args.output.expanduser(); target=target if target.is_absolute() else root/target; target.parent.mkdir(parents=True,exist_ok=True); target.write_text(text+"\n",encoding="utf-8"); print(f"Report written: {target}")
        else: print(text)
        return 0
    except (OSError,ValueError,json.JSONDecodeError) as exc: print(f"Error: {exc}",file=sys.stderr); return 2
if __name__=="__main__": raise SystemExit(main())
