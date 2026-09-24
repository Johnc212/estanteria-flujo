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
    now_col = datetime.utcnow() - timedelta(hours=5)
    return now_col.timetuple().tm_yday
def hoy_fecha_col():
    return (datetime.utcnow() - timedelta(hours=5)).date()
def juliano_a_fecha(ddd):
    try:
        ddd=int(str(ddd)[-3:]); hoy=hoy_fecha_col()
        base=date(hoy.year-1,1,1) if ddd>hoy.timetuple().tm_yday else date(hoy.year,1,1)
        return base+timedelta(days=ddd-1)
    except: return None
def semaforo(ddd):
    f=juliano_a_fecha(ddd)
    if not f: return {"color":"#6c757d","emoji":"⚪","dias":999,"txt":"-"}
    dias=(hoy_fecha_col()-f).days
    if dias<=3: return {"color":"#198754","emoji":"🟢","dias":dias,"txt":f"{dias}d"}
    if dias<=8: return {"color":"#ffc107","emoji":"🟡","dias":dias,"txt":f"{dias}d"}
    return {"color":"#dc3545","emoji":"🔴","dias":dias,"txt":f"{dias}d"}
def init_db():
    conn=get_conn(); cur=conn.cursor()
    try:
        cur.execute("CREATE TABLE IF NOT EXISTS lotes (id SERIAL PRIMARY KEY, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing DATE)" if DATABASE_URL else "CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing TEXT)")
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
    cur.close(); conn.close(); init_db()
    return redirect("/")

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estanteria de Flujo</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#eef2f7; font-family: 'Segoe UI', sans-serif}
.topbar{background:#1e4a7a; color:white; padding:12px 18px}
.card-pos{border:1px solid #ccc; border-radius:8px; background:#f8f9fa; min-height:68px; padding:6px; margin:3px; flex:1; font-size:11px}
.card-pos.active{border:2px solid #0d6efd; background:white; box-shadow:0 0 8px #0d6efd40}
.lote{font-size:10px; margin:2px 0; font-weight:600}
.btn-b{border-radius:8px; font-weight:700}
</style>
</head><body>
<div class="topbar d-flex align-items-center gap-3 flex-wrap">
<div class="d-flex align-items-center gap-2"><div style="font-size:32px">🏗️</div><h4 class="m-0 fw-bold" style="line-height:18px">Estanteria de<br>Flujo</h4></div>
<div class="bg-white bg-opacity-25 rounded px-3 py-1 d-flex align-items-center gap-2"><span>📦</span><div><b>{{total}}</b><br><small>estibas</small></div></div>
<div class="bg-white text-dark rounded px-3 py-1 d-flex align-items-center gap-2"><span>📅</span><div><b>Hoy {{hoy_fecha.strftime('%d %b')}} =<br>{{hoy_jul}} JULIANO</b></div></div>
<div class="ms-3 d-flex gap-2">
<span class="badge bg-success fs-6">🟢 0-3d</span>
<span class="badge bg-warning text-dark fs-6">🟡 4-8d</span>
<span class="badge bg-danger fs-6">🔴 9+d</span>
</div>
<div class="ms-auto d-flex gap-2"><button class="btn btn-sm btn-light">🔔</button><button class="btn btn-sm btn-light">⚙️</button><span class="badge bg-primary rounded-pill">AD</span></div>
</div>

<div class="container-fluid p-3">
<div class="bg-white rounded-3 p-3 shadow-sm d-flex gap-2 flex-wrap align-items-center mb-3">
<a href="/?bloque=1" class="btn {{'btn-primary' if bloque==1 else 'btn-outline-secondary'}} btn-b">B1 ({{tot_bloque[1]}})</a>
<a href="/?bloque=2" class="btn {{'btn-success' if bloque==2 else 'btn-outline-secondary'}} btn-b">B2 ({{tot_bloque[2]}})</a>
<a href="/?bloque=3" class="btn {{'btn-warning' if bloque==3 else 'btn-outline-secondary'}} btn-b">B3 ({{tot_bloque[3]}})</a>
<a href="/?bloque=4" class="btn {{'btn-secondary' if bloque==4 else 'btn-outline-secondary'}} btn-b">B4 ({{tot_bloque[4]}})</a>
<a href="/?bloque=0" class="btn {{'btn-dark' if bloque==0 else 'btn-outline-secondary'}} btn-b">☰ TODO ({{total}})</a>
<div class="ms-3 d-flex gap-2 align-items-center">
<label class="small fw-bold">BLOQUE:</label><select name="bloque" form="formMov" class="form-select form-select-sm" style="width:70px"><option>B1</option><option>B2</option><option>B3</option><option>B4</option></select>
<label class="small fw-bold">NIVEL:</label><select name="nivel" form="formMov" class="form-select form-select-sm" style="width:70px"><option>N1</option><option>N2</option><option>N3</option><option>N4</option><option>N5</option><option>N6</option></select>
<label class="small fw-bold">CALLE:</label><select name="calle" form="formMov" class="form-select form-select-sm" style="width:70px"><option>C1</option><option>C2</option><option>C3</option><option>C4</option><option>C5</option><option>C6</option><option>C7</option><option>C8</option><option>C9</option><option>C10</option></select>
</div>
<div class="ms-auto d-flex gap-2">
<input class="form-control form-control-sm" placeholder="🔍 Buscar lote/mate..." style="width:180px">
<button class="btn btn-outline-secondary btn-sm">Exportar CSV</button>
</div>
</div>

{% for b in bloques_ver %}
<div class="bg-white rounded-3 shadow-sm p-3 mb-3">
<div class="d-flex justify-content-between mb-2"><h5 class="fw-bold m-0">BLOQUE {{b}} <small class="badge bg-light text-dark">Nivel: N1 - Calle: C1</small></h5><small>Mostrando 6x10 = 60 ubicaciones</small></div>
{% for n in range(6,0,-1) %}
<div class="d-flex align-items-stretch">
<div style="width:40px; font-weight:800; padding-top:12px">{{'N'+n|string if true else ''}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,11) %}
{% set k = 'B' ~ b ~ '-N' ~ n ~ '-C' ~ c %}
{% set es_activo = (n==1 and c==1 and b==1) %}
<div class="card-pos {{'active' if es_activo else ''}}">
<div class="d-flex justify-content-between"><b>C{{c}}</b>{% if totales.get(k,0)>0 %}<span>{{totales.get(k,0)}} est</span>{% else %}<span class="text-muted">0 est</span>{% endif %}</div>
{% if es_activo and grupos.get(k) %}
<div class="mt-1"><b style="color:#0d6efd">B{{b}}-N{{n}}-C{{c}} - {{totales.get(k,0)}} est</b>
{% for lote in grupos.get(k,[]) %}
<div class="lote"><span style="color:{{lote.sema.color}}">●</span> {{lote.producto}} {{lote.estibas}}e J{{lote.juliano}}</div>
{% endfor %}
</div>
{% endif %}
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="row g-3">
<div class="col-lg-6">
<div class="bg-white rounded-3 shadow-sm p-3">
<div class="d-flex justify-content-between"><h6 class="fw-bold">Alimentar / Despachar</h6><span class="badge bg-light text-dark">Hoy {{hoy_jul}} = {{hoy_fecha.strftime('%d %b')}}</span></div>
<form id="formMov" method="post" action="/movimiento" class="row g-2 mt-2">
<div class="col-4"><label class="small">BLOQUE</label><select name="bloque" class="form-select form-select-sm fw-bold"><option value="1">B1</option><option value="2">B2</option><option value="3">B3</option><option value="4">B4</option></select></div>
<div class="col-4"><label class="small">NIVEL</label><select name="nivel" class="form-select form-select-sm fw-bold"><option value="1">N1</option><option value="2">N2</option><option value="3">N3</option><option value="4">N4</option><option value="5">N5</option><option value="6">N6</option></select></div>
<div class="col-4"><label class="small">CALLE</label><select name="calle" class="form-select form-select-sm fw-bold"><option value="1">C1</option><option value="2">C2</option><option value="3">C3</option><option value="4">C4</option><option value="5">C5</option><option value="6">C6</option><option value="7">C7</option><option value="8">C8</option><option value="9">C9</option><option value="10">C10</option></select></div>
<div class="col-6"><label class="small">MATERIAL COMPLETO</label><input name="producto" class="form-control fw-bold" value="12005778"></div>
<div class="col-3"><label class="small">JULIANO</label><input name="juliano" class="form-control fw-bold" value="{{hoy_jul}}" type="number"></div>
<div class="col-3"><label class="small">ESTIBAS</label><input name="cantidad" class="form-control fw-bold" value="1" type="number"></div>
<div class="col-6"><button name="accion" value="alimentar" class="btn btn-success w-100 fw-bold py-2">⊕ ALIMENTAR</button></div>
<div class="col-6"><button name="accion" value="despachar" class="btn btn-danger w-100 fw-bold py-2">⊖ DESPACHAR</button></div>
</form>
<small class="text-muted d-block mt-2 text-center">Accion se registrara con fecha de hoy {{hoy_fecha.strftime('%d %b')}} - Juliano {{hoy_jul}}</small>
</div>
</div>
<div class="col-lg-6">
<div class="bg-white rounded-3 shadow-sm p-3">
<h6 class="fw-bold">Resumen</h6>
<table class="table table-sm mt-2"><tr><td>Total Estibas:</td><td class="fw-bold">{{total}}</td></tr><tr><td>Lotes activos:</td><td class="fw-bold">{{lotes_count}}</td></tr><tr><td>Ultimo movimiento:</td><td class="fw-bold text-success">J{{hoy_jul}} (Hace 5 min)</td></tr></table>
</div>
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
    try: cur.execute("SELECT codigo,bloque,producto,juliano,estibas FROM lotes ORDER BY juliano ASC"); rows=cur.fetchall()
    except: rows=[]
    grupos={}; totales={}; tot_bloque={1:0,2:0,3:0,4:0}; total=0
    for r in rows:
        try:
            codigo=r[0] if DATABASE_URL else r['codigo']; bloque=r[1] if DATABASE_URL else r['bloque']
            producto=r[2] if DATABASE_URL else r['producto']; juliano=r[3] if DATABASE_URL else r['juliano']; estibas=r[4] if DATABASE_URL else r['estibas']
            if estibas<=0: continue
            s=semaforo(juliano); obj={"producto":producto,"juliano":juliano,"estibas":estibas,"sema":s}
            if codigo not in grupos: grupos[codigo]=[]
            grupos[codigo].append(obj)
            totales[codigo]=totales.get(codigo,0)+estibas
            tot_bloque[bloque]=tot_bloque.get(bloque,0)+estibas
            total+=estibas
        except: continue
    cur.close(); conn.close()
    bloques_ver=[1,2,3,4] if b_actual==0 else [b_actual]
    return render_template_string(HTML, grupos=grupos, totales=totales, tot_bloque=tot_bloque, total=total, bloque=b_actual, bloques_ver=bloques_ver, hoy_jul=hoy_jul, hoy_fecha=hoy_fecha, lotes_count=len(rows))

@app.route("/movimiento", methods=["POST"])
def mov():
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; producto=request.form['producto'].strip(); cant=int(request.form['cantidad']); jul=int(request.form['juliano']); accion=request.form.get('accion','alimentar')
    conn=get_conn(); cur=conn.cursor()
    try:
        if accion=='alimentar':
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s AND producto=%s AND juliano=%s" if DATABASE_URL else "SELECT id, estibas FROM lotes WHERE codigo=? AND producto=? AND juliano=?",(codigo,producto,jul))
            row=cur.fetchone()
            if row:
                cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if DATABASE_URL else "UPDATE lotes SET estibas=? WHERE id=?",(row[1]+cant,row[0]))
            else:
                f=juliano_a_fecha(jul)
                cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)" if DATABASE_URL else "INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (?,?,?,?,?,?,?,?)",(codigo,b,n,c,producto,jul,cant,f))
        else:
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s ORDER BY juliano ASC" if DATABASE_URL else "SELECT id, estibas FROM lotes WHERE codigo=? ORDER BY juliano ASC",(codigo,))
            por=cant
            for r in cur.fetchall():
                if por<=0: break
                id_,est=r[0],r[1]
                if est<=por:
                    por-=est
                    cur.execute("DELETE FROM lotes WHERE id=%s" if DATABASE_URL else "DELETE FROM lotes WHERE id=?",(id_,))
                else:
                    cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if DATABASE_URL else "UPDATE lotes SET estibas=? WHERE id=?",(est-por,id_)); por=0
        conn.commit()
    except Exception as e: print(e)
    cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
