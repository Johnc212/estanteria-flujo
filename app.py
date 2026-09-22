import os, json
from flask import Flask, request, redirect, render_template_string
from datetime import datetime

app = Flask(__name__)
NIVELES, CALLES, BLOQUES = 6, 10, 4
COLORES = {
 1: {"bg":"#0d6efd","light":"#e7f1ff","name":"AZUL","label":"Elite / Kimi"},
 2: {"bg":"#198754","light":"#d1e7dd","name":"VERDE","label":"Familia"},
 3: {"bg":"#fd7e14","light":"#fff3cd","name":"NARANJA","label":"Scott / Kimi PH"},
 4: {"bg":"#6f42c1","light":"#e2d9f3","name":"MORADO","label":"Kleenex / Otros"}
}
DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://","postgresql://",1)

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        import sqlite3
        c=sqlite3.connect("/tmp/estanteria.db")
        c.row_factory=sqlite3.Row
        return c

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if DATABASE_URL:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0)")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT INTO posiciones VALUES (%s,%s,%s,%s,'',0) ON CONFLICT DO NOTHING",(f"B{b}-N{n}-C{c}",b,n,c))
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0)")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT OR IGNORE INTO posiciones VALUES (?,?,?,?, '',0)",(f"B{b}-N{n}-C{c}",b,n,c))
    conn.commit(); cur.close(); conn.close()
init_db()

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#f5f5f7; font-family: -apple-system, BlinkMacSystemFont, sans-serif}
.card-stat{border-radius:12px; border:1px solid #e5e7eb; background:white; box-shadow: 0 1px 2px rgba(0,0,0,0.05)}
.shelf-card{background:white; border-radius:12px; border:1px solid #e5e7eb; margin-bottom:20px; overflow:hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.05)}
.tag{border-radius:6px; padding:4px 10px; font-size:12px; font-weight:700; color:white; display:inline-block}
.level-row{border-bottom:1px solid #f0f0f0; padding:12px 16px; display:flex; align-items:center; gap:12px}
.level-row:last-child{border:0}
</style></head><body class="p-3">
<div class="container-fluid" style="max-width:1300px">
<h1 style="font-family: Georgia, serif; font-weight:900; font-size:42px">Sistema de Estanterias</h1>
<p class="text-muted">Monitorea y gestiona el inventario por bloques y niveles. Controla capacidad, stock y ocupacion en tiempo real.</p>

<div class="row g-3 mb-4">
<div class="col-md-3"><div class="card-stat p-3"><div class="d-flex align-items-start gap-3"><div style="font-size:32px">🏠</div><div><div class="small text-muted fw-bold">Total Estantes</div><div style="font-size:36px; font-weight:900; line-height:1">{{BLOQUES}}</div><div class="small mt-1">• {{NIVELES*CALLES*BLOQUES}} posiciones • {{BLOQUES}} activos</div></div></div></div></div>
<div class="col-md-3"><div class="card-stat p-3"><div class="d-flex align-items-start gap-3"><div style="font-size:32px">📦</div><div><div class="small text-muted fw-bold">Total Estibas</div><div style="font-size:36px; font-weight:900; line-height:1">{{total}}</div><div class="small mt-1">• +{{total}} almacenadas</div></div></div></div></div>
<div class="col-md-3"><div class="card-stat p-3"><div class="d-flex align-items-start gap-3"><div style="font-size:32px">📊</div><div><div class="small text-muted fw-bold">Capacidad Ocupada</div><div style="font-size:36px; font-weight:900; line-height:1">{{pct}}%</div><div class="small mt-1">• {{total}} de {{cap}} slots • {{'Saludable' if pct<80 else 'Lleno'}}</div></div></div></div></div>
<div class="col-md-3"><div class="card-stat p-3"><div class="d-flex align-items-start gap-3"><div style="font-size:32px">✅</div><div><div class="small text-muted fw-bold">Estado del Sistema</div><div style="font-size:36px; font-weight:900; line-height:1; color:#198754">En Linea</div><div class="small mt-1">• Todos los bloques conectados • Activo</div></div></div></div></div>
</div>

<div class="d-flex justify-content-between align-items-center mb-3 flex-wrap">
<h2 style="font-weight:900; font-size:28px">Vista General de Estantes y Niveles</h2>
<div><span class="badge rounded-pill border border-success text-success bg-white p-2 px-3">● Todos los estantes • En Linea</span> <a href="#agregar" class="btn btn-primary btn-sm ms-2" style="border-radius:8px">+ Agregar Estiba</a></div>
</div>

{% for b in range(1,BLOQUES+1) %}
<div class="shelf-card">
<div class="p-3 d-flex justify-content-between align-items-center" style="border-left:6px solid {{COLORES[b].bg}}; background:{{COLORES[b].light}}22">
<div><b style="font-size:18px">Estante {{'ABCD'[b-1]}} — {{COLORES[b].label}} — BLOQUE {{b}} {{COLORES[b].name}}</b></div>
<div><span class="badge rounded-pill px-3 py-2" style="background:{{COLORES[b].light}}; color:{{COLORES[b].bg}}; border:1px solid {{COLORES[b].bg}}">Ocupado {{ocup[b]}}/{{NIVELES}} niveles • {{pct_b[b]}}% • {{'Saludable' if pct_b[b]<80 else 'Lleno'}}</span></div>
</div>
{% for n in range(NIVELES,0,-1) %}
<div class="level-row">
<div style="width:110px; font-weight:800">N{{n}} — {{'Superior' if n==NIVELES else 'Base' if n==1 else 'Medio'}}</div>
<div style="width:70px" class="text-muted small fw-bold">{{count_n[b][n]}}/{{CALLES}}</div>
<div class="d-flex flex-wrap gap-2 flex-grow-1">
{% set hay = false %}
{% for c in range(1,CALLES+1) %}
{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set p=pos.get(k) %}
{% if p and p.estibas>0 %}
{% set hay = true %}
<span class="tag" style="background:{{COLORES[b].bg}}">{{p.producto[:12]}} x{{p.estibas}}</span>
{% endif %}
{% endfor %}
{% if not hay %}
<span style="border:1px dashed #aaa; border-radius:6px; padding:4px 16px; font-size:12px; color:#888; background:#fafafa">1 espacio disponible — Listo para almacenar</span>
{% endif %}
</div>
<div style="width:70px; text-align:right"><span class="badge" style="background:{{COLORES[b].bg}}">{{'Lleno' if count_n[b][n]==CALLES else ''}}</span></div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="shelf-card p-3 mt-4" id="agregar">
<h5 class="fw-bold">Agregar / Despachar Estiba</h5>
<form method="post" action="/movimiento" class="row g-2 align-items-end">
<div class="col-md-2"><label class="small fw-bold">Bloque</label><select name="bloque" class="form-select form-select-sm">{% for b in range(1,BLOQUES+1) %}<option value="{{b}}">B{{b}} {{COLORES[b].name}}</option>{% endfor %}</select></div>
<div class="col-md-1"><label class="small fw-bold">Nivel</label><select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option value="{{n}}">N{{n}}</option>{% endfor %}</select></div>
<div class="col-md-1"><label class="small fw-bold">Calle</label><select name="calle" class="form-select form-select-sm">{% for c in range(1,CALLES+1) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select></div>
<div class="col-md-3"><label class="small fw-bold">Producto</label><input name="producto" class="form-control form-control-sm" placeholder="Ej: Kimi PH, Familia, Scott" required></div>
<div class="col-md-1"><label class="small fw-bold">Cant.</label><input type="number" name="cantidad" class="form-control form-control-sm" value="1" min="1"></div>
<div class="col-md-2"><label class="small fw-bold">Tipo</label><select name="tipo" class="form-select form-select-sm"><option value="ALIMENTACION">+ ALIMENTACION</option><option value="DESPACHO">- DESPACHO</option></select></div>
<div class="col-md-2"><button class="btn btn-primary btn-sm w-100 fw-bold" style="height:31px">Guardar</button></div>
</form>
<p class="small text-muted mt-2 mb-0">Leyenda: <span style="color:#0d6efd">● Azul = Bloque 1</span> <span style="color:#198754">● Verde = Bloque 2</span> <span style="color:#fd7e14">● Naranja = Bloque 3</span> <span style="color:#6f42c1">● Morado = Bloque 4</span> | Ultima actualizacion: {{ahora}} • Auto-refresh activo</p>
</div>

</div></body></html>
"""

@app.route("/")
def index():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM posiciones"); rows=cur.fetchall()
    pos={}
    for r in rows:
        if DATABASE_URL: pos[r[0]]={'codigo':r[0],'bloque':r[1],'nivel':r[2],'calle':r[3],'producto':r[4],'estibas':r[5]}
        else: pos[r['codigo']]={'codigo':r['codigo'],'bloque':r['bloque'],'nivel':r['nivel'],'calle':r['calle'],'producto':r['producto'],'estibas':r['estibas']}
    total=sum(p['estibas'] for p in pos.values())
    cap=NIVELES*CALLES*BLOQUES
    pct=int(total/cap*100) if cap else 0
    ocup={}; pct_b={}; count_n={b:{n:0 for n in range(1,NIVELES+1)} for b in range(1,BLOQUES+1)}
    for b in range(1,BLOQUES+1):
        niveles_con=set()
        for p in pos.values():
            if p['bloque']==b and p['estibas']>0:
                niveles_con.add(p['nivel'])
                count_n[b][p['nivel']]+=1
        ocup[b]=len(niveles_con)
        pct_b[b]=int(len(niveles_con)/NIVELES*100) if NIVELES else 0
    cur.close(); conn.close()
    ahora=datetime.now().strftime("%Y-%m-%d %H:%M")
    return render_template_string(HTML, pos=pos, total=total, cap=cap, pct=pct, ocup=ocup, pct_b=pct_b, count_n=count_n, BLOQUES=BLOQUES, NIVELES=NIVELES, CALLES=CALLES, COLORES=COLORES, ahora=ahora)

@app.route("/movimiento", methods=["POST"])
def mov():
    conn=get_conn(); cur=conn.cursor()
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; prod=request.form['producto']; tipo=request.form['tipo']; cant=int(request.form['cantidad'])
    q="SELECT estibas FROM posiciones WHERE codigo=%s" if DATABASE_URL else "SELECT estibas FROM posiciones WHERE codigo=?"
    cur.execute(q,(codigo,)); actual=cur.fetchone()[0]
    if tipo=="DESPACHO" and cant>actual:
        cur.close(); conn.close(); return f"<h3>Solo hay {actual} en {codigo}</h3><a href='/'>Volver</a>"
    nuevo=actual+cant if tipo=="ALIMENTACION" else actual-cant
    if DATABASE_URL: cur.execute("UPDATE posiciones SET estibas=%s, producto=%s WHERE codigo=%s",(nuevo,prod,codigo))
    else: cur.execute("UPDATE posiciones SET estibas=?, producto=? WHERE codigo=?",(nuevo,prod,codigo))
    conn.commit(); cur.close(); conn.close()
    return redirect("/")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
