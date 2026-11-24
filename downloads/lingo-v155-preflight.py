#!/usr/bin/env python3
"""Lingo Bunny V1.5.5 preflight: read-only evidence, no application or DB changes."""
import ast, hashlib, json, sqlite3, tempfile, shutil, re
from pathlib import Path
ROOT=Path.home()/'.lingo-bunny'
DB=ROOT/'data/lingo_bunny.db'
SERVER=ROOT/'app-v1.3.2/server.py'
SOURCES=[('CURRENT',DB),('HISTORICAL',ROOT/'backups/v150-20261122-134657/lingo_bunny.db'),('HISTORICAL_CHECK',ROOT/'backups/v1511-repair-20261122-140034/lingo_bunny.db'),('PRE_SYNC',ROOT/'data/backups/lingo_bunny-2026-11-23.db')]
def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,ensure_ascii=False,default=str).encode()).hexdigest()[:16]
def obj(v):return v if isinstance(v,dict) else {}
def seq(v):return v if isinstance(v,list) else []
def read(p,live=False):
    if not p.is_file():raise RuntimeError('missing '+str(p))
    # SQLite online backup is a consistent snapshot of the live database, including WAL.
    with tempfile.TemporaryDirectory() as td:
        target=Path(td)/'copy.db'
        if live:
            with sqlite3.connect(p.as_uri()+'?mode=ro',uri=True,timeout=10) as c,sqlite3.connect(target) as out:c.backup(out)
        else:
            shutil.copyfile(p,target)
            wal=Path(str(p)+'-wal')
            if wal.exists():shutil.copyfile(wal,str(target)+'-wal')
        with sqlite3.connect(target) as c:
            c.row_factory=sqlite3.Row
            if c.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('integrity check failed')
            return [dict(r) for r in c.execute('SELECT code,pin_salt,pin_hash,state_json,revision,updated_at FROM profiles')]
def identity(r):return digest([r['code'],r['pin_salt'],r['pin_hash']])
def state(r):return json.loads(r['state_json'])
def public(s):
    keys=['courseDay','lastCompletedCourseDay','coins','stars','xp','studyDays','streak','wishTickets','lastClaimDate','lastChestDate','lastStudy','lastRareRewardDate','lastRareRewardStudyDay','lastWeeklyReview','lastMonthlyReview','lastCourseWeekReview','lastCourseMonthReview','lessonModeV2','claimed','updatedAt','done']
    return {k:s.get(k) for k in keys if k in s}
def daily(s):
    return {d:{k:v[k] for k in ['courseDay','lessonIds','claimed','count','completedAt','updatedAt','done'] if k in v} for d,v in sorted(obj(s.get('dailyRecords')).items()) if isinstance(v,dict)}
def rewards(s):
    allowed={'type','kind','id','date','at','studyDay','coins','amount','cost','value','stars','xp','status','createdAt','updatedAt','redeemedAt','fulfilledAt','deletedAt'}
    def clean(v):return {k:x for k,x in v.items() if k in allowed and (isinstance(x,(int,float,bool)) or k in {'type','kind','status','date'} and isinstance(x,str))}|{'fingerprint':digest(v)}
    return [clean(v) for v in seq(s.get('rewardHistory')) if isinstance(v,dict)]
def wishes(s):
    return [{k:v[k] for k in ['status','createdAt','updatedAt','redeemedAt','fulfilledAt','deletedAt'] if k in v}|{'fingerprint':digest(v)} for v in seq(s.get('wishRequests')) if isinstance(v,dict)]
def review_meta(s):
    b=obj(s.get('reviewBank')); types={}; fields=set()
    for v in b.values():
        if not isinstance(v,dict):continue
        t=str(v.get('type','unknown'));types[t]=types.get(t,0)+1;fields.update(v.keys())
    return {'count':len(b),'types':types,'fields':sorted(fields),'wrongToday':sum(bool(obj(v).get('wrongToday')) for v in b.values())}
def report():
    sources={}
    for tag,p in SOURCES:
        try:
            rows=read(p,tag=='CURRENT'); sources[tag]={identity(r):(r,state(r)) for r in rows}
            print(tag,'rows=',len(rows),'file=',p.relative_to(ROOT))
            for ident,(r,s) in sources[tag].items():
                print('identity',ident,'revision',r['revision'],'state',json.dumps(public(s),ensure_ascii=False,sort_keys=True))
                print('daily',json.dumps(daily(s),ensure_ascii=False,sort_keys=True))
                print('diary dates/course',json.dumps({d:obj(v).get('courseDay') for d,v in sorted(obj(s.get('diaryEntries')).items())},ensure_ascii=False))
                print('review',json.dumps(review_meta(s),ensure_ascii=False));print('rewards',json.dumps(rewards(s),ensure_ascii=False));print('wishes',json.dumps(wishes(s),ensure_ascii=False));print('state fields',','.join(sorted(s)))
        except Exception as e:print(tag,'ERROR',type(e).__name__,str(e))
    cur=sources.get('CURRENT',{});hist=sources.get('HISTORICAL',{});check=sources.get('HISTORICAL_CHECK',{});pre=sources.get('PRE_SYNC',{})
    print('\n=== MATCHED PROFILE RECOVERY PREVIEW ===')
    for ident,(_,a) in cur.items():
        if ident not in hist:print('NO_EXACT_IDENTITY_MATCH',ident);continue
        _,b=hist[ident];print('MATCH',ident,'historical corroboration',ident in check and digest(b)==digest(check[ident][1]))
        print('course evidence',a.get('courseDay'),b.get('courseDay'),'last completed',a.get('lastCompletedCourseDay'),b.get('lastCompletedCourseDay'))
        for field in ('dailyRecords','diaryEntries','reviewBank','weakWords','stats'):
            x,y=obj(a.get(field)),obj(b.get(field)); common=set(x)&set(y)
            print(field,'current',len(x),'historical',len(y),'union',len(set(x)|set(y)),'different_shared',sum(x[k]!=y[k] for k in common),'current_only',len(set(x)-set(y)),'historical_only',len(set(y)-set(x)))
        print('balance conflict', {k:[a.get(k),b.get(k),pre.get(ident,({},{}))[1].get(k)] for k in ['coins','stars','xp','wishTickets','studyDays']})
    print('\n=== SERVER ROUTE INSPECTION ===')
    try:
        src=SERVER.read_text(encoding='utf-8'); tree=ast.parse(src); lines=src.splitlines();print('server_sha256',hashlib.sha256(src.encode()).hexdigest())
        for n in ast.walk(tree):
            if not isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef)):continue
            seg='\n'.join(lines[n.lineno-1:n.end_lineno]); relevant=n.name=='do_POST' or ('profile' in n.name.lower() and any(x in n.name.lower() for x in ['save','load','auth','update','get'])) or ('UPDATE profiles' in seg and len(seg)<12000)
            if not relevant:continue
            print('FUNCTION',n.name,'lines',n.lineno,n.end_lineno)
            for line in lines[n.lineno-1:n.end_lineno]:
                # Never report literal credential assignments or PIN/salt/hash values.
                if re.search(r'''(?i)(password|secret|token|api_key|pin|salt)\s*=\s*["']''',line):print('    # literal credential assignment omitted');continue
                print(line)
    except Exception as e:print('SERVER_INSPECT_ERROR',type(e).__name__,str(e))
    print('RESULT=V155_PREFLIGHT_READ_ONLY_DONE')
if __name__=='__main__':report()
