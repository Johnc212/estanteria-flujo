import os
from flask import Flask, request, redirect, render_template_string
from datetime import date, datetime, timedelta

app = Flask(__name__)
BLOQUES, NIVELES, CALLES = 4, 6, 10

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://","postgresql://",1)

def get_conn():
    if DATABASE_URL:
        try:
            import psycopg2
            return psycopg2.connect(DATABASE_URL, sslmode='require')
        except: pass
    import sqlite3
    c=sqlite3.connect("/tmp/estanteria.db")
    c.row_factory=sqlite3.Row
    return c

def hoy_juliano():
    # Hora Colombia UTC-5 para que cambie a las 00:00 de Cali
    now_col = datetime.utcnow() - timedelta(hours=5)
    return now_col.timetuple().tm_yday # 23 Sep = 266 en 2026

def hoy_fecha_col():
    now_col = datetime.utcnow() - timedelta(hours=5)
    return now_col.date()

def juliano_a_fecha(ddd):
    try:
        ddd=int(str(ddd)[-3:])
        hoy=hoy_fecha_col()
        base=date(hoy.year-1,1,1) if ddd>hoy.timetuple().tm_yday else date(hoy.year,1,1)
        return base+timedelta(days=ddd-1)
    except: return None

def semaforo(ddd):
    f=juliano_a_fecha(ddd)
    if not f: return {"color":"#999","emoji":"⚪","dias":999,"txt":"-"}
    dias=(hoy_fecha_col()-f).days
    if dias<0: dias=0
    if dias<=3: return {"color":"#198754","emoji":"🟢","dias":dias,"txt":f"{dias}d"}
    if dias<=8: return {"color":"#ffc107","emoji":"🟡","dias":dias,"txt":f"{dias}d"}
    return {"color":"#dc3545","emoji":"🔴","dias":dias,"txt":f"{dias}d"}

def init_db():
    conn=get_conn(); cur=conn.cursor()
    try:
        if DATABASE_URL:
            cur.execute("CREATE TABLE IF NOT EXISTS lotes (id SERIAL PRIMARY KEY, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing DATE)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing TEXT)")
        conn.commit()
    except: conn.rollback()
    cur.close(); conn.close()

try: init_db()
except: pass

@app.route("/reset_db")
def reset_db():
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("DROP TABLE IF EXISTS lotes"); conn.commit()
    except: pass
    cur.close(); conn.close()
    init_db()
    return redirect("/")

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estanteria de Flujo</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>.pos{border:1.5px solid #ccc; border-radius:6px; background:white; padding:4px; min-height:85px; margin:2px; flex:1; font-size:10px; line-height:12px}.lote{font-size:9px; background:#f2f2f2; border-radius:3px; margin:2px 0; padding:1px 3px}</style>
</head><body class="p-2">
<div class="container-fluid">
<div class="d-flex gap-2 mb-2 align-items-center flex-wrap">
<h6 class="fw-bold m-0">📦 Estanteria de Flujo - {{total}} estibas</h6>
<span class="badge bg-primary fs-6">Hoy {{hoy_fecha.strftime('%d %b')}} = {{hoy_jul}} JULIANO</span>
<span class="badge bg-success">🟢 0-3d</span><span class="badge bg-warning text-dark">🟡 4-8d</span><span class="badge bg-danger">🔴 9+d</span>
<span class="small ms-auto text-muted">Cambia auto despues de 00:00 Cali</span>
</div>
<div class="d-flex gap-1 mb-2 flex-wrap">
<a href="/?bloque=1" class="btn btn-sm {{'btn-primary' if bloque==1 else 'btn-outline-primary'}}">B1 ({{tot_bloque[1]}})</a>
<a href="/?bloque=2" class="btn btn-sm {{'btn-success' if bloque==2 else 'btn-outline-success'}}">B2 ({{tot_bloque[2]}})</a>
<a href="/?bloque=3" class="btn btn-sm {{'btn-warning' if bloque==3 else 'btn-outline-warning'}}">B3 ({{tot_bloque[3]}})</a>
<a href="/?bloque=4" class="btn btn-sm {{'btn-secondary' if bloque==4 else 'btn-outline-secondary'}}">B4 ({{tot_bloque[4]}})</a>
<a href="/?bloque=0" class="btn btn-sm {{'btn-dark' if bloque==0 else 'btn-outline-dark'}}">TODO ({{total}})</a>
<a href="/reset_db" class="btn btn-sm btn-danger ms-auto">Reparar</a>
</div>

{% for b in bloques_ver %}
<div class="bg-dark text-white p-1 small fw-bold">BLOQUE {{b}} - {{tot_bloque[b]}} estibas</div>
<div class="bg-white border p-1 mb-3">
{% for n in range(6,0,-1) %}
<div class="d-flex">
<div style="width:30px; font-weight:900">N{{n}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,11) %}
{% set k = 'B' ~ b ~ '-N' ~ n ~ '-C' ~ c %}
<div class="pos">
<div><b>N{{n}}-C{{c}}</b> - {{totales.get(k,0)}} est</div>
{% for lote in grupos.get(k,[]) %}
<div class="lote" style="border-left:3px solid {{lote.sema.color}}"><b>{{lote.producto}}</b> {{lote.estibas}}e J{{lote.juliano}} {{lote.sema.emoji}} {{lote.sema.txt}}</div>
{% endfor %}
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="card">
<div class="card-header py-1 fw-bold">Alimentar - Hoy {{hoy_jul}} = 23 Sep - Cambia a {{hoy_jul+1}} mañana 00:00</div>
<div class="card-body p-2">
<form method="post" action="/movimiento" class="row g-1">
<div class="col-2"><select name="bloque" class="form-select form-select-sm"><option value="1">B1</option><option value="2">B2</option><option value="3">B3</option><option value="4">B4</option></select></div>
<div class="col-2"><select name="nivel" class="form-select form-select-sm"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option></select></div>
<div class="col-2"><select name="calle" class="form-select form-select-sm"><option>1</option><option>2</option><option>3</option><option>4</option><option>5</option><option>6</option><option>7</option><option>8</option><option>9</option><option>10</option></select></div>
<div class="col-3"><input name="producto" class="form-control form-control-sm" value="12005778" placeholder="Material completo" required></div>
<div class="col-2"><input name="juliano" class="form-control form-control-sm" value="{{hoy_jul}}" type="number" min="1" max="366" required></div>
<div class="col-1"><input name="cantidad" class="form-control form-control-sm" value="1" type="number" min="1"></div>
<div class="col-12 mt-2"><button class="btn btn-primary btn-sm w-100 fw-bold">+ ALIMENTAR - Ej: 10 est J255 + 4 est J266 del mismo material</button></div>
</form>
<div class="small text-muted mt-1">Ej hoy 23 Sep=266. Si alimentas 10 estibas de 12005778 J255 y luego 4 estibas J266, en la calle veras: 12005778 10e J255 🔴 + 12005778 4e J266 🟢</div>
</div>
</div>
</div>
</body></html>
"""

@app.route("/")
def index():
    b_actual = int(request.args.get('bloque','1'))
    hoy_jul=hoy_juliano(); hoy_fecha=hoy_fecha_col()
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("SELECT codigo,bloque,producto,juliano,estibas FROM lotes ORDER BY juliano ASC")
        rows=cur.fetchall()
    except: rows=[]
    grupos={}; totales={}; tot_bloque={1:0,2:0,3:0,4:0}; total=0
    for r in rows:
        try:
            codigo=r[0] if DATABASE_URL else r['codigo']; bloque=r[1] if DATABASE_URL else r['bloque']
            producto=r[2] if DATABASE_URL else r['producto']; juliano=r[3] if DATABASE_URL else r['juliano']; estibas=r[4] if DATABASE_URL else r['estibas']
            if estibas<=0: continue
            s=semaforo(juliano)
            obj={"producto":producto,"juliano":juliano,"estibas":estibas,"sema":s}
            if codigo not in grupos: grupos[codigo]=[]
            grupos[codigo].append(obj)
            totales[codigo]=totales.get(codigo,0)+estibas
            tot_bloque[bloque]=tot_bloque.get(bloque,0)+estibas
            total+=estibas
        except: continue
    cur.close(); conn.close()
    bloques_ver=[1,2,3,4] if b_actual==0 else [b_actual]
    return render_template_string(HTML, grupos=grupos, totales=totales, tot_bloque=tot_bloque, total=total, bloque=b_actual, bloques_ver=bloques_ver, hoy_jul=hoy_jul, hoy_fecha=hoy_fecha)

@app.route("/movimiento", methods=["POST"])
def mov():
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; producto=request.form['producto']; cant=int(request.form['cantidad']); jul=int(request.form['juliano'])
    conn=get_conn(); cur=conn.cursor()
    try:
        if DATABASE_URL:
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s AND producto=%s AND juliano=%s",(codigo,producto,jul))
        else:
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=? AND producto=? AND juliano=?",(codigo,producto,jul))
        row=cur.fetchone()
        if row:
            new_est=row[1]+cant
            cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if DATABASE_URL else "UPDATE lotes SET estibas=? WHERE id=?",(new_est,row[0]))
        else:
            f=juliano_a_fecha(jul)
            if DATABASE_URL:
                cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(codigo,b,n,c,producto,jul,cant,f))
            else:
                cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (?,?,?,?,?,?,?,?)",(codigo,b,n,c,producto,jul,cant,f.isoformat() if f else None))
        conn.commit()
    except Exception as e: print(e)
    cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
