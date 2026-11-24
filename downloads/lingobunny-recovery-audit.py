#!/usr/bin/env python3
from pathlib import Path
import sqlite3, json, re, hashlib, time, shutil

HOME = Path.home()
ROOT = HOME / ".lingo-bunny"
DATA = ROOT / "data"
BACKUPS = ROOT / "backups"
STAMP = time.strftime("%Y%m%d-%H%M%S")
REPORT = ROOT / f"recovery-audit-{STAMP}.txt"
SNAPDIR = BACKUPS / f"recovery-snapshot-{STAMP}"

KEYS = {
    "courseDay","lastCompletedCourseDay","coursePosition","lessonDay","currentLesson",
    "dailyRecords","studyDays","completedDates","reviewBank","wishRequests","rewardHistory",
    "diaryEntries","coins","stars","streak","updatedAt","learnerName","name","profileId"
}

def sha256(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1024*1024), b""):
            h.update(b)
    return h.hexdigest()

def summarize_state(obj):
    if not isinstance(obj, dict):
        return None
    candidates=[obj]
    for k in ("state","data","profile","payload","progress"):
        v=obj.get(k)
        if isinstance(v,dict): candidates.append(v)
    best=max(candidates, key=lambda d: sum(1 for k in KEYS if k in d))
    if not any(k in best for k in KEYS):
        return None
    def n(x):
        return len(x) if isinstance(x,(list,dict,set,tuple)) else x
    out={}
    for k in ("learnerName","name","profileId","courseDay","lastCompletedCourseDay","currentLesson",
              "coins","stars","streak","updatedAt"):
        if k in best: out[k]=best.get(k)
    for k in ("dailyRecords","studyDays","completedDates","reviewBank","wishRequests","rewardHistory","diaryEntries"):
        if k in best: out[k+"_count"]=n(best.get(k))
    dr=best.get("dailyRecords")
    if isinstance(dr,dict):
        completed=[]
        for day, rec in dr.items():
            if isinstance(rec,dict) and (rec.get("completed") or rec.get("isComplete") or rec.get("done") or rec.get("claimed")):
                try:
                    completed.append(int(re.sub(r"\D","",str(day)) or 0))
                except Exception:
                    pass
        if completed:
            out["dailyRecords_max_completed_key"]=max(completed)
    return out

def walk_json_candidates(obj, path="$", depth=0):
    if depth>5:
        return
    if isinstance(obj,dict):
        s=summarize_state(obj)
        if s:
            yield path,s
        for k,v in obj.items():
            if isinstance(v,(dict,list)):
                yield from walk_json_candidates(v, path+"."+str(k), depth+1)
    elif isinstance(obj,list):
        for i,v in enumerate(obj[:100]):
            if isinstance(v,(dict,list)):
                yield from walk_json_candidates(v, f"{path}[{i}]", depth+1)

lines=[]
def log(x=""):
    lines.append(str(x))
    print(x)

log("=== Lingo Bunny recovery audit (READ-ONLY except new backup copies/report) ===")
log("ROOT="+str(ROOT))

SNAPDIR.mkdir(parents=True, exist_ok=False)
current_files=[]
for p in [DATA/"lingo_bunny.db", DATA/"lingo_bunny.db-wal", DATA/"lingo_bunny.db-shm"]:
    if p.exists() and p.is_file():
        dst=SNAPDIR/p.name
        shutil.copy2(p,dst)
        current_files.append(p)
        log(f"SNAPSHOT {p} -> {dst} bytes={p.stat().st_size} sha256={sha256(p)}")
if not current_files:
    log("WARNING: current lingo_bunny.db not found")

cands=[]
for base in (DATA,BACKUPS):
    if base.exists():
        for p in base.rglob("*"):
            if not p.is_file():
                continue
            low=p.name.lower()
            if low.endswith((".db",".sqlite",".sqlite3",".json",".bak",".backup")) or "lingo" in low or "profile" in low or "state" in low:
                try:
                    cands.append((p.stat().st_mtime,p))
                except Exception:
                    pass
cands=sorted(cands, reverse=True)[:250]
log(f"CANDIDATE_FILES={len(cands)}")

def audit_sqlite(p):
    uri="file:"+str(p)+"?mode=ro"
    con=sqlite3.connect(uri, uri=True)
    con.row_factory=sqlite3.Row
    tables=[r[0] for r in con.execute("select name from sqlite_master where type='table' order by name")]
    log(f"\n[SQLITE] {p} bytes={p.stat().st_size} sha256={sha256(p)}")
    log("tables="+",".join(tables))
    for t in tables:
        try:
            cols=[r[1] for r in con.execute(f'pragma table_info("{t}")')]
            count=con.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]
            log(f" table={t} rows={count} cols={','.join(cols)}")
            order=""
            for oc in ("updated_at","updatedAt","id","created_at","createdAt"):
                if oc in cols:
                    order=f' ORDER BY "{oc}" DESC'
                    break
            rows=con.execute(f'SELECT * FROM "{t}"{order} LIMIT 100').fetchall()
            for idx,row in enumerate(rows):
                rd=dict(row)
                for col,val in rd.items():
                    if not isinstance(val,str) or len(val)<2:
                        continue
                    if any(s in col.lower() for s in ("pin","password","secret","token","hash")):
                        continue
                    txt=val.strip()
                    if not (txt.startswith("{") or txt.startswith("[")):
                        continue
                    try:
                        obj=json.loads(txt)
                    except Exception:
                        continue
                    found=list(walk_json_candidates(obj, f"{t}[{idx}].{col}"))
                    for jpath,s in found[:20]:
                        log("  STATE "+jpath+" "+json.dumps(s,ensure_ascii=False,sort_keys=True))
        except Exception as e:
            log(f"  ERROR table={t}: {type(e).__name__}: {e}")
    con.close()

def audit_json(p):
    try:
        if p.stat().st_size>20*1024*1024:
            return
        raw=p.read_text("utf-8",errors="replace")
        obj=json.loads(raw)
    except Exception:
        return
    found=list(walk_json_candidates(obj))
    if found:
        log(f"\n[JSON] {p} bytes={p.stat().st_size} sha256={sha256(p)}")
        for jpath,s in found[:50]:
            log(" STATE "+jpath+" "+json.dumps(s,ensure_ascii=False,sort_keys=True))

for _,p in cands:
    try:
        head=p.read_bytes()[:16]
        if head.startswith(b"SQLite format 3"):
            audit_sqlite(p)
        elif p.suffix.lower()==".json":
            audit_json(p)
    except Exception as e:
        log(f"\n[FILE_ERROR] {p}: {type(e).__name__}: {e}")

log("\n=== IMPORTANT ===")
log("No course progress, wish, review, or profile data was modified.")
log("Do NOT run the previous V1.5.4 updater with forced lesson recovery.")
log("REPORT="+str(REPORT))
REPORT.write_text("\n".join(lines)+"\n",encoding="utf-8")
print("RESULT=RECOVERY_AUDIT_READY")
