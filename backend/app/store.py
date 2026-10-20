import json, sqlite3, threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from .adapters.mock import MockDataAdapter, VEHICLES
from .services.eta import dt, progress

VN=timezone(timedelta(hours=7))
def utcnow(): return datetime.now(timezone.utc)

class Store:
    def __init__(self,path):
        self.path=str(path)
        Path(path).parent.mkdir(parents=True,exist_ok=True)
        self.lock=threading.RLock()
        with self.tx() as db:
            db.executescript("""CREATE TABLE IF NOT EXISTS meta(key TEXT PRIMARY KEY,value TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS trips(id INTEGER PRIMARY KEY AUTOINCREMENT,code TEXT UNIQUE NOT NULL,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS alerts(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS analyses(id TEXT PRIMARY KEY,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS decisions(id INTEGER PRIMARY KEY AUTOINCREMENT,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY AUTOINCREMENT,payload TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS notices(id TEXT PRIMARY KEY,payload TEXT NOT NULL);""")
            if not self.get(db,'clock'): self.seed(db)
    @contextmanager
    def tx(self):
        with self.lock:
            db=sqlite3.connect(self.path,timeout=10)
            db.row_factory=sqlite3.Row
            try:
                db.execute("BEGIN IMMEDIATE")
                yield db
                db.commit()
            except Exception:
                db.rollback();raise
            finally: db.close()
    def get(self,db,key):
        row=db.execute("SELECT value FROM meta WHERE key=?",(key,)).fetchone()
        return json.loads(row['value']) if row else None
    def put(self,db,key,value):
        db.execute("INSERT OR REPLACE INTO meta VALUES(?,?)",(key,json.dumps(value)))
    def rows(self,db):
        return [{**json.loads(row['payload']),"id":row['id']} for row in db.execute('SELECT * FROM trips ORDER BY id')]
    def save_trip(self,db,t,id=None):
        data={k:v for k,v in t.items() if k!='id'}
        if id: db.execute('UPDATE trips SET code=?,payload=? WHERE id=?',(data['code'],json.dumps(data),id));return id
        return db.execute('INSERT INTO trips(code,payload) VALUES(?,?)',(data['code'],json.dumps(data))).lastrowid
    def seed(self,db):
        for table in ['trips','alerts','analyses','decisions','orders','notices']: db.execute(f'DELETE FROM {table}')
        db.execute("DELETE FROM meta WHERE key LIKE 'notice-baseline:%'")
        db.execute("DELETE FROM meta WHERE key='comparison-fleet'")
        db.execute("DELETE FROM meta WHERE key LIKE 'enterprise-%'")
        base=datetime.now(VN).replace(hour=8,minute=0,second=0,microsecond=0)
        clock={"now":base.isoformat(),"base":base.isoformat(),"running":False,"speed":1,"real_anchor":utcnow().isoformat()}
        self.put(db,'clock',clock)
        for i,t in enumerate(MockDataAdapter().fetch_trips(base)):
            t['remaining_minutes']=t['travel_minutes']+t['handling_minutes']+t['delay_minutes']
            t['revision']=1;t['updated_at']=utcnow().isoformat()
            if t['status']=='hoan_thanh':
                t['remaining_minutes']=0;t['completed_at']=(base+timedelta(minutes=80)).isoformat()
                t['start_at']=(base-timedelta(hours=2)).isoformat();t['completed_at']=(base-timedelta(minutes=40)).isoformat()
            self.save_trip(db,t)
    def tick(self,db,advance=0):
        c=self.get(db,'clock'); old=dt(c['now']);real=utcnow()
        delta=max(0,(real-dt(c['real_anchor'])).total_seconds())*c['speed'] if c['running'] else 0
        now=old+timedelta(seconds=delta,minutes=advance)
        for t in self.rows(db):
            progress(t,old,now)
            self.save_trip(db,t,t['id'])
        c['elapsed_minutes']=c.get('elapsed_minutes',0)+delta/60+advance
        c['now']=now.isoformat();c['real_anchor']=real.isoformat()
        self.put(db,'clock',c)
        return c
