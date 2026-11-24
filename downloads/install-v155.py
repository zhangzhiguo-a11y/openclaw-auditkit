#!/usr/bin/env python3
from pathlib import Path
import hashlib, json, os, plistlib, py_compile, re, shutil, sqlite3, subprocess, tempfile, time, urllib.request, zipfile

ROOT=Path.home()/'.lingo-bunny'
APP=ROOT/'app-v1.3.2'
WEB=APP/'web'
DOWNLOAD=WEB/'download'
DB=ROOT/'data'/'lingo_bunny.db'
SERVER=APP/'server.py'
HIST=ROOT/'backups'/'v150-20261122-134657'/'lingo_bunny.db'
HIST2=ROOT/'backups'/'v1511-repair-20261122-140034'/'lingo_bunny.db'
PRESYNC=ROOT/'data'/'backups'/'lingo_bunny-2026-11-23.db'
PREFIX=82927508
PREFIX_SHA='e59b79f79eb2065c5755dd7066bf98e986b7cbedc6c569cba96c4de71e1a04de'
TAIL_SHA='cbaadea25cf55f85626301516ea3228649eabc3e3be2321c3e5a7a885feda19c'
FINAL_SHA='b1589eb1ec5362852872270cee60360ab5536f3c2d1177aab553e8fe9001c41c'
FINAL_BYTES=84074540
EXPECTED_SERVER_SHA='62e1dc9c0dea1130a17f0e2cea36de67f16fe74da118c6f46d01f4bbf94365f2'
TAIL_URLS=[
 'https://raw.githubusercontent.com/zhangzhiguo-a11y/openclaw-auditkit/2627cc07da995b1c9ce0528c7f49a4f3e37c0633/downloads/v155/LingoBunny-V1.5.5-tail-from-common-prefix.bin',
 'https://cdn.jsdelivr.net/gh/zhangzhiguo-a11y/openclaw-auditkit@2627cc07da995b1c9ce0528c7f49a4f3e37c0633/downloads/v155/LingoBunny-V1.5.5-tail-from-common-prefix.bin',
]
TARGET=DOWNLOAD/'LingoBunny-V1.5.5-Android-MultiKid-SafeSync-Review-FINAL.apk'
TAIL=DOWNLOAD/'.LingoBunny-V1.5.5-tail.bin'


def sha256(p):
    h=hashlib.sha256()
    with open(p,'rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

def download(urls,dst):
    last=None
    for url in urls:
        for attempt in range(1,5):
            try:
                req=urllib.request.Request(url,headers={'User-Agent':'LingoBunny-V155-Updater/1.0'})
                with urllib.request.urlopen(req,timeout=45) as r,open(dst,'wb') as out:shutil.copyfileobj(r,out,1024*1024)
                return url
            except Exception as e:
                last=e
                try:dst.unlink()
                except FileNotFoundError:pass
                print(f'download retry {attempt}/4: {type(e).__name__}: {e}')
                time.sleep(min(2*attempt,6))
    raise RuntimeError('download failed: '+str(last))

def obj(v):return v if isinstance(v,dict) else {}
def seq(v):return v if isinstance(v,list) else []
def num(v,d=0):
    try:return float(v) if isinstance(v,float) else int(v)
    except Exception:return d

def deep(v):return json.loads(json.dumps(v,ensure_ascii=False))
def dmax(a,b):
    a=str(a or '');b=str(b or '');return a if a>=b else b

def merge_num_map(a,b):
    out={}
    for k in set(obj(a))|set(obj(b)):out[k]=max(num(obj(a).get(k)),num(obj(b).get(k)))
    return out

def merge_stats(a,b):
    out=deep(obj(a))
    for k,v in obj(b).items():
        if isinstance(v,(int,float)) or isinstance(out.get(k),(int,float)):out[k]=max(num(out.get(k)),num(v))
        elif k not in out:out[k]=deep(v)
    return out

def merge_daily(a,b):
    out={}
    for k in set(obj(a))|set(obj(b)):
        x=deep(obj(obj(a).get(k)));y=deep(obj(obj(b).get(k)))
        z={**x,**y}
        ids=[]
        for v in seq(x.get('lessonIds'))+seq(y.get('lessonIds')):
            try:v=int(v)
            except Exception:continue
            if v>0 and v not in ids:ids.append(v)
        ids.sort()
        z['lessonIds']=ids
        z['count']=max(len(ids),num(x.get('count')),num(y.get('count')))
        z['courseDay']=max(num(x.get('courseDay')),num(y.get('courseDay')))
        z['completedAt']=max(num(x.get('completedAt')),num(y.get('completedAt')))
        z['updatedAt']=max(num(x.get('updatedAt')),num(y.get('updatedAt')))
        z['claimed']=bool(x.get('claimed') or y.get('claimed') or ids)
        dx=obj(x.get('done'));dy=obj(y.get('done'))
        if dx or dy:z['done']={m:bool(dx.get(m) or dy.get(m)) for m in set(dx)|set(dy)}
        out[k]=z
    return out

def merge_diary(a,b):
    out=deep(obj(a))
    for k,y in obj(b).items():
        if k not in out:out[k]=deep(y);continue
        x=out[k]
        if not isinstance(x,dict) or not isinstance(y,dict):
            if len(json.dumps(y,ensure_ascii=False))>len(json.dumps(x,ensure_ascii=False)):out[k]=deep(y)
            continue
        xt=num(x.get('updatedAt'));yt=num(y.get('updatedAt'))
        if yt>xt or (yt==xt and len(json.dumps(y,ensure_ascii=False))>len(json.dumps(x,ensure_ascii=False))):out[k]=deep(y)
    return out

def merge_review_item(a,b):
    if not a:return deep(b)
    if not b:return deep(a)
    al=str(a.get('lastReviewed') or '');bl=str(b.get('lastReviewed') or '')
    if bl>al:newer,older=b,a
    elif al>bl:newer,older=a,b
    elif num(b.get('updatedAt'))>num(a.get('updatedAt')):newer,older=b,a
    else:newer,older=a,b
    out={**deep(older),**deep(newer)}
    la=str(a.get('learnedAt') or '');lb=str(b.get('learnedAt') or '')
    if la and lb:out['learnedAt']=min(la,lb)
    elif la or lb:out['learnedAt']=la or lb
    vals=[v for v in [num(a.get('courseDayLearned'),999999),num(b.get('courseDayLearned'),999999)] if v>0]
    if vals:out['courseDayLearned']=min(vals)
    out['wrongCount']=max(num(a.get('wrongCount')),num(b.get('wrongCount')))
    out['reviews']=max(num(a.get('reviews')),num(b.get('reviews')))
    return out

def merge_review(a,b):
    out=deep(obj(a))
    for k,v in obj(b).items():out[k]=merge_review_item(out.get(k),v)
    return out

def reward_key(x):
    if not isinstance(x,dict):return ''
    return str(x.get('id') or x.get('fingerprint') or '|'.join(str(x.get(k) or '') for k in ('type','studyDay','date','at','name','title')))
def merge_rewards(a,b):
    m={}
    for x in seq(a)+seq(b):
        if not isinstance(x,dict):continue
        k=reward_key(x)
        if not k:continue
        m[k]={**m.get(k,{}),**deep(x)}
    return sorted(m.values(),key=lambda x:max(num(x.get('at')),num(x.get('updatedAt')),num(x.get('studyDay'))),reverse=True)[:200]

def wish_key(w):
    if not isinstance(w,dict):return ''
    return str(w.get('id') or w.get('fingerprint') or '|'.join(str(w.get(k) or '') for k in ('createdAt','text','title','name')))
def wish_rank(s):return {'deleted':4,'fulfilled':3,'pending':2,'saved':1}.get(str(s),0)
def merge_wishes(a,b):
    m={}
    for w in seq(a)+seq(b):
        if not isinstance(w,dict):continue
        k=wish_key(w)
        if not k:continue
        old=m.get(k)
        if not old:m[k]=deep(w);continue
        newer=w if num(w.get('updatedAt'))>num(old.get('updatedAt')) else old
        older=old if newer is w else w
        z={**deep(older),**deep(newer)}
        z['status']=w.get('status') if wish_rank(w.get('status'))>wish_rank(old.get('status')) else old.get('status')
        for f in ('updatedAt','redeemedAt','fulfilledAt','deletedAt'):z[f]=max(num(old.get(f)),num(w.get(f)))
        vals=[v for v in (num(old.get('createdAt'),0),num(w.get('createdAt'),0)) if v>0]
        if vals:z['createdAt']=min(vals)
        m[k]=z
    return sorted(m.values(),key=lambda x:num(x.get('updatedAt')),reverse=True)

def merge_core(current,incoming,trust_spendable=False):
    a=deep(obj(current));b=deep(obj(incoming))
    ac=num(a.get('lastCompletedCourseDay'));bc=num(b.get('lastCompletedCourseDay'))
    ad=max(1,num(a.get('courseDay'),1));bd=max(1,num(b.get('courseDay'),1))
    winner=b if (bc,bd,num(b.get('updatedAt')))>(ac,ad,num(a.get('updatedAt'))) else a
    out=deep(winner)
    out['lastCompletedCourseDay']=max(ac,bc);out['courseDay']=max(ad,bd,out['lastCompletedCourseDay']+1)
    out['dailyRecords']=merge_daily(a.get('dailyRecords'),b.get('dailyRecords'))
    out['diaryEntries']=merge_diary(a.get('diaryEntries'),b.get('diaryEntries'))
    out['reviewBank']=merge_review(a.get('reviewBank'),b.get('reviewBank'))
    out['weakWords']=merge_num_map(a.get('weakWords'),b.get('weakWords'))
    out['stats']=merge_stats(a.get('stats'),b.get('stats'))
    out['rewardHistory']=merge_rewards(a.get('rewardHistory'),b.get('rewardHistory'))
    out['wishRequests']=merge_wishes(a.get('wishRequests'),b.get('wishRequests'))
    for f in ('studyDays','stars','xp','islandLevel','level','lastRareRewardStudyDay','lastCourseWeekReview','lastCourseMonthReview','streak'):
        out[f]=max(num(a.get(f)),num(b.get(f)))
    for f in ('lastClaimDate','lastChestDate','lastRareRewardDate','lastStudy','lastWeeklyReview','lastMonthlyReview','lastCourseAdvanceDate'):
        out[f]=dmax(a.get(f),b.get(f))
    if trust_spendable:
        out['coins']=num(b.get('coins'));out['wishTickets']=num(b.get('wishTickets'))
    else:
        out['coins']=num(a.get('coins'));out['wishTickets']=num(a.get('wishTickets'))
    if ad==bd and ac==bc:
        da=obj(a.get('done'));db=obj(b.get('done'));out['done']={k:bool(da.get(k) or db.get(k)) for k in set(da)|set(db)}
    else:out['done']=deep(obj((b if (bc,bd)>(ac,ad) else a).get('done')))
    out['lessonModeV2']=True
    return out

def db_snapshot(path,live=False):
    td=tempfile.TemporaryDirectory();dst=Path(td.name)/'x.db'
    if live:
        with sqlite3.connect(path) as src,sqlite3.connect(dst) as out:src.backup(out)
    else:
        shutil.copyfile(path,dst)
        wal=Path(str(path)+'-wal')
        if wal.exists():shutil.copyfile(wal,str(dst)+'-wal')
    con=sqlite3.connect(dst);con.row_factory=sqlite3.Row
    if con.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise RuntimeError('database integrity failed: '+str(path))
    rows=[dict(r) for r in con.execute('SELECT * FROM profiles')];con.close();td.cleanup();return rows

def identity(r):return (r.get('code'),r.get('pin_salt'),r.get('pin_hash'))
def load_state(r):return json.loads(r.get('state_json') or '{}')

def evidence_recovery_preview():
    cur=db_snapshot(DB,True);h1=db_snapshot(HIST);h2=db_snapshot(HIST2);pre=db_snapshot(PRESYNC)
    if len(cur)!=1 or len(h1)!=1 or len(h2)!=1 or len(pre)!=1:raise RuntimeError('expected exactly one profile in recovery sources')
    cr,hr,h2r,pr=cur[0],h1[0],h2[0],pre[0]
    if not (identity(cr)==identity(hr)==identity(h2r)==identity(pr)):raise RuntimeError('profile identity mismatch; recovery aborted')
    cs,hs,h2s,ps=map(load_state,(cr,hr,h2r,pr))
    # Two independent Nov-22 copies must corroborate the historical learning state.
    sig=lambda s:(num(s.get('courseDay')),num(s.get('lastCompletedCourseDay')),len(obj(s.get('diaryEntries'))),len(obj(s.get('reviewBank'))))
    if sig(hs)!=sig(h2s):raise RuntimeError('historical copies do not corroborate; recovery aborted')
    if sig(hs)[0]<=sig(cs)[0] or sig(hs)[1]<=sig(cs)[1] or sig(hs)[2]<10 or sig(hs)[3]<100:raise RuntimeError('no evidence-backed higher historical progress found')
    merged=merge_core(hs,cs,True)  # current spendable balances, union learning facts
    # Keep only the genuinely fulfilled historical wish from pre-sync; ignore stale saved wish.
    fulfilled=[w for w in seq(ps.get('wishRequests')) if isinstance(w,dict) and w.get('status')=='fulfilled']
    merged['wishRequests']=merge_wishes(cs.get('wishRequests'),fulfilled)
    merged['coins']=num(cs.get('coins'));merged['wishTickets']=num(cs.get('wishTickets'))
    merged['stars']=max(num(cs.get('stars')),num(hs.get('stars')))
    merged['xp']=max(num(cs.get('xp')),num(hs.get('xp')))
    merged['studyDays']=max(num(cs.get('studyDays')),num(hs.get('studyDays')))
    merged['streak']=max(num(cs.get('streak')),num(hs.get('streak')))
    merged['name']=cs.get('name',hs.get('name'))
    merged['syncMergeVersion']='1.5.5-server-recovered'
    merged['recoveryV155']={
      'at':int(time.time()*1000),'method':'evidence-union','historicalCourseDay':num(hs.get('courseDay')),
      'historicalLastCompleted':num(hs.get('lastCompletedCourseDay')),'currentBeforeCourseDay':num(cs.get('courseDay')),
      'dailyRecords':len(obj(merged.get('dailyRecords'))),'diaryEntries':len(obj(merged.get('diaryEntries'))),
      'reviewBank':len(obj(merged.get('reviewBank'))),'source':'two-corroborating-2026-11-22-snapshots'
    }
    merged['updatedAt']=int(time.time()*1000)
    return cr,cs,merged

SERVER_SAVE_V155=r'''    def save_profile(self, code, pin, state):
        code = self._clean_code(code)
        pin = self._validate_pin(pin)
        if len(code) != 8 or not pin:
            return None
        incoming, _ = self._normalize_state(state)
        now_ms = int(time.time() * 1000)

        def n(v, d=0):
            try:
                return int(v)
            except Exception:
                return d
        def cp(v):
            return json.loads(json.dumps(v, ensure_ascii=False))
        def od(v):
            return v if isinstance(v, dict) else {}
        def ls(v):
            return v if isinstance(v, list) else []
        def dmax(a, b):
            a, b = str(a or ""), str(b or "")
            return a if a >= b else b
        def merge_num_map(a, b):
            a, b = od(a), od(b)
            return {k: max(n(a.get(k)), n(b.get(k))) for k in set(a) | set(b)}
        def merge_stats(a, b):
            a, b = od(a), od(b); out = cp(a)
            for k, v in b.items():
                if isinstance(v, (int, float)) or isinstance(out.get(k), (int, float)):
                    out[k] = max(n(out.get(k)), n(v))
                elif k not in out:
                    out[k] = cp(v)
            return out
        def merge_daily(a, b):
            a, b = od(a), od(b); out = {}
            for k in set(a) | set(b):
                x, y = cp(od(a.get(k))), cp(od(b.get(k))); z = {**x, **y}
                ids = []
                for v in ls(x.get("lessonIds")) + ls(y.get("lessonIds")):
                    try: v = int(v)
                    except Exception: continue
                    if v > 0 and v not in ids: ids.append(v)
                ids.sort(); z["lessonIds"] = ids
                z["count"] = max(len(ids), n(x.get("count")), n(y.get("count")))
                z["courseDay"] = max(n(x.get("courseDay")), n(y.get("courseDay")))
                z["completedAt"] = max(n(x.get("completedAt")), n(y.get("completedAt")))
                z["updatedAt"] = max(n(x.get("updatedAt")), n(y.get("updatedAt")))
                z["claimed"] = bool(x.get("claimed") or y.get("claimed") or ids)
                dx, dy = od(x.get("done")), od(y.get("done"))
                if dx or dy: z["done"] = {m: bool(dx.get(m) or dy.get(m)) for m in set(dx) | set(dy)}
                out[k] = z
            return out
        def merge_diary(a, b):
            a, b = od(a), od(b); out = cp(a)
            for k, y in b.items():
                if k not in out: out[k] = cp(y); continue
                x = out[k]
                if not isinstance(x, dict) or not isinstance(y, dict):
                    if len(json.dumps(y, ensure_ascii=False)) > len(json.dumps(x, ensure_ascii=False)): out[k] = cp(y)
                    continue
                xt, yt = n(x.get("updatedAt")), n(y.get("updatedAt"))
                if yt > xt or (yt == xt and len(json.dumps(y, ensure_ascii=False)) > len(json.dumps(x, ensure_ascii=False))): out[k] = cp(y)
            return out
        def review_item(a, b):
            if not a: return cp(b)
            if not b: return cp(a)
            al, bl = str(a.get("lastReviewed") or ""), str(b.get("lastReviewed") or "")
            if bl > al: newer, older = b, a
            elif al > bl: newer, older = a, b
            elif n(b.get("updatedAt")) > n(a.get("updatedAt")): newer, older = b, a
            else: newer, older = a, b
            out = {**cp(older), **cp(newer)}
            la, lb = str(a.get("learnedAt") or ""), str(b.get("learnedAt") or "")
            if la and lb: out["learnedAt"] = min(la, lb)
            elif la or lb: out["learnedAt"] = la or lb
            vals = [x for x in (n(a.get("courseDayLearned"), 999999), n(b.get("courseDayLearned"), 999999)) if x > 0]
            if vals: out["courseDayLearned"] = min(vals)
            out["wrongCount"] = max(n(a.get("wrongCount")), n(b.get("wrongCount")))
            out["reviews"] = max(n(a.get("reviews")), n(b.get("reviews")))
            return out
        def merge_review(a, b):
            out = cp(od(a))
            for k, v in od(b).items(): out[k] = review_item(out.get(k), v)
            return out
        def reward_key(x):
            return str(x.get("id") or x.get("fingerprint") or "|".join(str(x.get(k) or "") for k in ("type","studyDay","date","at","name","title")))
        def merge_rewards(a, b):
            m = {}
            for x in ls(a) + ls(b):
                if not isinstance(x, dict): continue
                k = reward_key(x)
                if k: m[k] = {**m.get(k, {}), **cp(x)}
            return sorted(m.values(), key=lambda x: max(n(x.get("at")), n(x.get("updatedAt")), n(x.get("studyDay"))), reverse=True)[:200]
        def wish_key(w):
            return str(w.get("id") or w.get("fingerprint") or "|".join(str(w.get(k) or "") for k in ("createdAt","text","title","name")))
        def wrank(s):
            return {"deleted":4,"fulfilled":3,"pending":2,"saved":1}.get(str(s), 0)
        def merge_wishes(a, b):
            m = {}
            for w in ls(a) + ls(b):
                if not isinstance(w, dict): continue
                k = wish_key(w)
                if not k: continue
                old = m.get(k)
                if not old: m[k] = cp(w); continue
                newer = w if n(w.get("updatedAt")) > n(old.get("updatedAt")) else old
                older = old if newer is w else w
                z = {**cp(older), **cp(newer)}
                z["status"] = w.get("status") if wrank(w.get("status")) > wrank(old.get("status")) else old.get("status")
                for f in ("updatedAt","redeemedAt","fulfilledAt","deletedAt"): z[f] = max(n(old.get(f)), n(w.get(f)))
                vals = [v for v in (n(old.get("createdAt")), n(w.get("createdAt"))) if v > 0]
                if vals: z["createdAt"] = min(vals)
                m[k] = z
            return sorted(m.values(), key=lambda x: n(x.get("updatedAt")), reverse=True)
        def merge(current, inc):
            a, b = cp(od(current)), cp(od(inc))
            ac, bc = n(a.get("lastCompletedCourseDay")), n(b.get("lastCompletedCourseDay"))
            ad, bd = max(1, n(a.get("courseDay"),1)), max(1, n(b.get("courseDay"),1))
            winner = b if (bc, bd, n(b.get("updatedAt"))) > (ac, ad, n(a.get("updatedAt"))) else a
            out = cp(winner); out["lastCompletedCourseDay"] = max(ac, bc); out["courseDay"] = max(ad, bd, out["lastCompletedCourseDay"] + 1)
            out["dailyRecords"] = merge_daily(a.get("dailyRecords"), b.get("dailyRecords"))
            out["diaryEntries"] = merge_diary(a.get("diaryEntries"), b.get("diaryEntries"))
            out["reviewBank"] = merge_review(a.get("reviewBank"), b.get("reviewBank"))
            out["weakWords"] = merge_num_map(a.get("weakWords"), b.get("weakWords"))
            out["stats"] = merge_stats(a.get("stats"), b.get("stats"))
            out["rewardHistory"] = merge_rewards(a.get("rewardHistory"), b.get("rewardHistory"))
            out["wishRequests"] = merge_wishes(a.get("wishRequests"), b.get("wishRequests"))
            for f in ("studyDays","stars","xp","islandLevel","level","lastRareRewardStudyDay","lastCourseWeekReview","lastCourseMonthReview","streak"):
                out[f] = max(n(a.get(f)), n(b.get(f)))
            for f in ("lastClaimDate","lastChestDate","lastRareRewardDate","lastStudy","lastWeeklyReview","lastMonthlyReview","lastCourseAdvanceDate"):
                out[f] = dmax(a.get(f), b.get(f))
            trusted = str(b.get("syncMergeVersion") or "").startswith("1.5.5")
            out["coins"] = n(b.get("coins")) if trusted else n(a.get("coins"))
            out["wishTickets"] = n(b.get("wishTickets")) if trusted else n(a.get("wishTickets"))
            if ad == bd and ac == bc:
                da, db = od(a.get("done")), od(b.get("done")); out["done"] = {k: bool(da.get(k) or db.get(k)) for k in set(da) | set(db)}
            else:
                out["done"] = cp(od((b if (bc,bd) > (ac,ad) else a).get("done")))
            out["lessonModeV2"] = True; out["syncMergeVersion"] = "1.5.5-server"; out["updatedAt"] = now_ms
            return out

        with self.db() as con:
            row = con.execute("SELECT * FROM profiles WHERE code=?", (code,)).fetchone()
            if not row or not self._verify_pin(row, pin):
                return None
            current = json.loads(row["state_json"] or "{}")
            merged = merge(current, incoming)
            merged, encoded = self._normalize_state(merged)
            merged["updatedAt"] = now_ms
            merged, encoded = self._normalize_state(merged)
            current_revision = int(row["revision"]); next_revision = current_revision + 1
            con.execute("""CREATE TABLE IF NOT EXISTS profile_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, revision INTEGER NOT NULL,
                state_json TEXT NOT NULL, updated_at INTEGER NOT NULL, saved_at TEXT NOT NULL)""")
            con.execute("INSERT INTO profile_history(code,revision,state_json,updated_at,saved_at) VALUES(?,?,?,?,?)",
                        (code, current_revision, row["state_json"] or "{}", int(row["updated_at"]), self._utcnow()))
            con.execute("UPDATE profiles SET state_json=?, updated_at=?, revision=?, last_seen_at=? WHERE code=?",
                        (encoded, now_ms, next_revision, self._utcnow(), code))
            con.execute("DELETE FROM profile_history WHERE code=? AND id NOT IN (SELECT id FROM profile_history WHERE code=? ORDER BY id DESC LIMIT 200)", (code, code))
        self._daily_backup()
        return {"ok": True, "accepted": True, "state": merged, "revision": next_revision, "updatedAt": now_ms, "merge": "v1.5.5-server"}
'''

def patch_server_text(text):
    if 'merge": "v1.5.5-server"' in text:return text,False
    pat=re.compile(r'(?ms)^    def save_profile\(self, code, pin, state\):\n.*?(?=^    def |\Z)')
    matches=list(pat.finditer(text))
    if len(matches)!=1:raise RuntimeError(f'cannot uniquely locate save_profile: {len(matches)} matches')
    return text[:matches[0].start()]+SERVER_SAVE_V155+'\n'+text[matches[0].end():],True

def find_launch_label():
    for p in sorted((Path.home()/'Library/LaunchAgents').glob('*.plist')):
        try:
            with open(p,'rb') as f:d=plistlib.load(f)
            args=' '.join(str(x) for x in d.get('ProgramArguments',[]))
            if 'lingo-bunny' in args and ('server.py' in args or '8792' in args):return d.get('Label'),p
        except Exception:pass
    return 'com.bestresources.lingobunny',None

print('=== Lingo Bunny V1.5.5 evidence-safe updater ===')
for p in (WEB,DB,SERVER,HIST,HIST2,PRESYNC):
    if not p.exists():raise SystemExit('ERROR: required path missing: '+str(p))
DOWNLOAD.mkdir(parents=True,exist_ok=True)

# PRE-FLIGHT: evidence and server must match before any modification.
row,before,recovered=evidence_recovery_preview()
print('RECOVERY_EVIDENCE=OK')
print('BEFORE courseDay=%s lastCompleted=%s diary=%s review=%s coins=%s wishes=%s' % (before.get('courseDay'),before.get('lastCompletedCourseDay'),len(obj(before.get('diaryEntries'))),len(obj(before.get('reviewBank'))),before.get('coins'),len(seq(before.get('wishRequests')))))
print('PREVIEW courseDay=%s lastCompleted=%s diary=%s review=%s coins=%s wishes=%s' % (recovered.get('courseDay'),recovered.get('lastCompletedCourseDay'),len(obj(recovered.get('diaryEntries'))),len(obj(recovered.get('reviewBank'))),recovered.get('coins'),len(seq(recovered.get('wishRequests')))))
server_sha=sha256(SERVER);print('SERVER_SHA_BEFORE='+server_sha)
server_text=SERVER.read_text()
if server_sha!=EXPECTED_SERVER_SHA and 'merge": "v1.5.5-server"' not in server_text:raise SystemExit('ERROR: server.py changed since preflight; no files changed')
patched_server,server_changed=patch_server_text(server_text)
with tempfile.NamedTemporaryFile('w',suffix='.py',delete=False) as tf:tf.write(patched_server);tmp_py=tf.name
try:py_compile.compile(tmp_py,doraise=True)
finally:Path(tmp_py).unlink(missing_ok=True)
print('SERVER_PATCH_PREFLIGHT=OK changed='+str(server_changed))

# Rebuild signed APK from unchanged common prefix + signed V155 tail.
candidates=sorted(DOWNLOAD.glob('LingoBunny-V1.5.[234]*.apk'))
base=None
for p in candidates:
    if p.stat().st_size>=PREFIX:
        h=hashlib.sha256()
        with open(p,'rb') as f:
            remaining=PREFIX
            while remaining:
                b=f.read(min(1024*1024,remaining));
                if not b:break
                h.update(b);remaining-=len(b)
        if remaining==0 and h.hexdigest()==PREFIX_SHA:base=p;break
if base is None:raise SystemExit('ERROR: no trusted V1.5.2/1.5.3/1.5.4 base APK with exact common prefix; no files changed')
print('BASE='+base.name)
used=download(TAIL_URLS,TAIL);print('TAIL_SOURCE='+used)
if sha256(TAIL)!=TAIL_SHA:TAIL.unlink(missing_ok=True);raise SystemExit('ERROR: tail SHA mismatch; no files changed')
tmp_apk=DOWNLOAD/'.LingoBunny-V1.5.5-building.apk'
with open(base,'rb') as src,open(tmp_apk,'wb') as out:
    remaining=PREFIX
    while remaining:
        b=src.read(min(1024*1024,remaining))
        if not b:raise SystemExit('ERROR: base truncated')
        out.write(b);remaining-=len(b)
    with open(TAIL,'rb') as f:shutil.copyfileobj(f,out,1024*1024)
if tmp_apk.stat().st_size!=FINAL_BYTES or sha256(tmp_apk)!=FINAL_SHA:
    tmp_apk.unlink(missing_ok=True);TAIL.unlink(missing_ok=True);raise SystemExit('ERROR: final V1.5.5 APK verification failed; no files changed')
with zipfile.ZipFile(tmp_apk) as z:
    if z.testzip():raise SystemExit('ERROR: APK zip validation failed')
    req={'AndroidManifest.xml','assets/www/index.html','assets/www/v155-data-review.js','assets/www/android-release-v152.js','assets/www/wish-v152.js','assets/www/sw.js','assets/www/manifest.json','assets/www/sync-config.js'}
    if not req.issubset(set(z.namelist())):raise SystemExit('ERROR: V1.5.5 required files missing')
    idx=z.read('assets/www/index.html').decode('utf-8','replace');fix=z.read('assets/www/v155-data-review.js').decode('utf-8','replace')
    if 'V1.5.5' not in idx or 'evidenceOnlyRecovery:true' not in fix or 'RECOVERY_TARGET' in fix:raise SystemExit('ERROR: V1.5.5 markers invalid')
print('APK_PREFLIGHT=OK SHA256='+FINAL_SHA)

# BACKUP before any write.
stamp=time.strftime('%Y%m%d-%H%M%S')
backup=ROOT/'backups'/('v155-before-install-'+stamp);backup.mkdir(parents=True,exist_ok=False)
with sqlite3.connect(DB) as src,sqlite3.connect(backup/'lingo_bunny.db') as dst:src.backup(dst)
shutil.copy2(SERVER,backup/'server.py')
for name in ('index.html','android-release-v152.js','sw.js','wish-v152.js','manifest.json','sync-config.js'):
    p=WEB/name
    if p.exists():shutil.copy2(p,backup/name)
print('BACKUP='+str(backup))

# 1) Recover only evidence-backed learning facts, retaining current spendable balances.
now=int(time.time()*1000);recovered['updatedAt']=now
with sqlite3.connect(DB,timeout=30) as con:
    con.row_factory=sqlite3.Row
    cur=con.execute('SELECT * FROM profiles WHERE code=?',(row['code'],)).fetchone()
    if not cur:raise SystemExit('ERROR: active profile disappeared')
    if (cur['code'],cur['pin_salt'],cur['pin_hash'])!=identity(row):raise SystemExit('ERROR: active profile identity changed during install')
    con.execute('''CREATE TABLE IF NOT EXISTS profile_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT, code TEXT NOT NULL, revision INTEGER NOT NULL,
        state_json TEXT NOT NULL, updated_at INTEGER NOT NULL, saved_at TEXT NOT NULL)''')
    con.execute('INSERT INTO profile_history(code,revision,state_json,updated_at,saved_at) VALUES(?,?,?,?,?)',(cur['code'],int(cur['revision']),cur['state_json'] or '{}',int(cur['updated_at']),time.strftime('%Y-%m-%dT%H:%M:%S')))
    encoded=json.dumps(recovered,ensure_ascii=False,separators=(',',':'))
    con.execute('UPDATE profiles SET state_json=?,updated_at=?,revision=? WHERE code=?',(encoded,now,int(cur['revision'])+1,cur['code']))
    con.commit()
    if con.execute('PRAGMA quick_check').fetchone()[0]!='ok':raise SystemExit('ERROR: DB integrity failed after recovery')
print('RECOVERY_APPLIED courseDay=%s lastCompleted=%s daily=%s diary=%s review=%s coins=%s stars=%s wishes=%s' % (recovered.get('courseDay'),recovered.get('lastCompletedCourseDay'),len(obj(recovered.get('dailyRecords'))),len(obj(recovered.get('diaryEntries'))),len(obj(recovered.get('reviewBank'))),recovered.get('coins'),recovered.get('stars'),len(seq(recovered.get('wishRequests')))))

# 2) Patch server-side merge protection atomically.
if server_changed:
    t=SERVER.with_name('.server.py.v155.tmp');t.write_text(patched_server);os.chmod(t,SERVER.stat().st_mode & 0o777);os.replace(t,SERVER)
py_compile.compile(str(SERVER),doraise=True)
print('SERVER_PATCHED=OK SHA256='+sha256(SERVER))

# 3) Publish signed APK + only changed web shell files. Curriculum/content files are untouched.
os.chmod(tmp_apk,0o644);os.replace(tmp_apk,TARGET)
web_files=[
 ('assets/www/index.html','index.html'),('assets/www/android-release-v152.js','android-release-v152.js'),
 ('assets/www/v155-data-review.js','v155-data-review.js'),('assets/www/sw.js','sw.js'),
 ('assets/www/wish-v152.js','wish-v152.js'),('assets/www/manifest.json','manifest.json'),('assets/www/sync-config.js','sync-config.js')]
with zipfile.ZipFile(TARGET) as z:
    for src_name,dst_name in web_files:
        dst=WEB/dst_name;t=WEB/('.'+dst_name+'.v155.tmp');t.write_bytes(z.read(src_name));os.chmod(t,0o644);os.replace(t,dst)
TAIL.unlink(missing_ok=True)
print('APK_PATH='+str(TARGET));print('APK_BYTES='+str(TARGET.stat().st_size));print('APK_SHA256='+sha256(TARGET))

# 4) Restart launchd service so server-side protection is active.
label,plist=find_launch_label();print('LAUNCH_LABEL='+str(label))
uid=os.getuid();r=subprocess.run(['launchctl','kickstart','-k',f'gui/{uid}/{label}'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
if r.returncode!=0:
    print('LAUNCH_KICKSTART_WARNING='+r.stdout.strip())
    if plist:
        subprocess.run(['launchctl','bootout',f'gui/{uid}',str(plist)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        r2=subprocess.run(['launchctl','bootstrap',f'gui/{uid}',str(plist)],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True)
        if r2.returncode!=0:raise SystemExit('ERROR: server restart failed: '+r2.stdout.strip())
# health
ok=False
for _ in range(20):
    try:
        with urllib.request.urlopen('http://127.0.0.1:8792/',timeout=3) as resp:
            if resp.status==200:ok=True;break
    except Exception:time.sleep(.5)
if not ok:raise SystemExit('ERROR: server did not become healthy on 8792')
print('LOCAL_SERVER_HTTP=200')

# 5) Public checks.
url='https://lingo.bestresources.cn/download/'+TARGET.name;print('APK_URL='+url)
try:
    req=urllib.request.Request(url,method='HEAD',headers={'User-Agent':'LingoBunny-V155-Updater/1.0'})
    with urllib.request.urlopen(req,timeout=20) as r:print('PUBLIC_HEAD_HTTP='+str(r.status));print('PUBLIC_CONTENT_LENGTH='+str(r.headers.get('Content-Length') or ''))
except Exception as e:print('PUBLIC_HEAD_HTTP=ERROR '+type(e).__name__+': '+str(e))
try:
    req=urllib.request.Request('https://lingo.bestresources.cn/api/profile/load',method='OPTIONS',headers={'Origin':'https://appassets.androidplatform.net','Access-Control-Request-Method':'POST','Access-Control-Request-Headers':'content-type'})
    with urllib.request.urlopen(req,timeout=20) as r:print('CORS_PREFLIGHT=OK' if 'POST' in (r.headers.get('Access-Control-Allow-Methods') or '').upper() else 'CORS_PREFLIGHT=BAD')
except Exception as e:print('CORS_PREFLIGHT=ERROR '+str(e))
print('RESULT=V155_READY')
