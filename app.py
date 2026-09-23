import os
from flask import Flask, request, redirect, render_template_string
from datetime import datetime

app = Flask(__name__)
NIVELES, CALLES, BLOQUES = 6, 10, 4
COLORES = {
 1: {"bg":"#0d6efd", "name":"AZUL"},
 2: {"bg":"#198754", "name":"VERDE"},
 3: {"bg":"#fd7e14", "name":"NARANJA"},
 4: {"bg":"#6f42c1", "name":"MORADO"}
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
        cur.execute("CREATE TABLE IF NOT EXISTS config_calles (bloque INT, calle INT, producto_asignado TEXT, PRIMARY KEY(bloque,calle))")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT INTO posiciones VALUES (%s,%s,%s,%s,'',0) ON CONFLICT DO NOTHING",(f"B{b}-N{n}-C{c}",b,n,c))
                for c in range(1,CALLES+1):
                    cur.execute("INSERT INTO config_calles VALUES (%s,%s,'') ON CONFLICT DO NOTHING",(b,c,'LIBRE' if b!=1 else 'Elite' if c==1 else 'LIBRE'))
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS config_calles (bloque INT, calle INT, producto_asignado TEXT, PRIMARY KEY(bloque,calle))")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT OR IGNORE INTO posiciones VALUES (?,?,?,?, '',0)",(f"B{b}-N{n}-C{c}",b,n,c))
                for c in range(1,CALLES+1):
                    cur.execute("INSERT OR IGNORE INTO config_calles VALUES (?,?,?)",(b,c,'LIBRE'))
    conn.commit(); cur.close(); conn.close()
init_db()

HTML = """
<!doctype html>
<html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#f8f9fa}
.pos{border:2px solid #0d6efd; border-radius:8px; background:white; text-align:center; padding:6px 2px; min-height:62px; font-size:11px; margin:3px; flex:1}
.pos-lleno{background:#dbe8ff; border-color:#0d6efd; font-weight:bold}
.pos-vacio{color:#666}
.header-bloque{background:#0d6efd; color:white; padding:6px 10px; font-size:13px; font-weight:600}
.btn-bloque{border-radius:8px; font-weight:600; padding:8px 16px; border:2px solid}
</style>
</head><body class="p-2">
<div class="container-fluid">

<div class="d-flex align-items-center gap-2 mb-2">
<span style="font-size:28px">📦</span><h4 class="m-0 fw-bold">4 BLOQUES - {{total}} estibas (PERMANENTE)</h4>
<span class="ms-auto small text-muted">Actualizado: {{ahora}}</span>
</div>

<!-- BOTONES DE BLOQUES -->
<div class="d-flex gap-2 mb-3 flex-wrap align-items-center">
{% for b in range(1,BLOQUES+1) %}
<a href="/?bloque={{b}}" class="btn btn-bloque {{'text-white' if bloque==b else ''}}"
   style="{{'background:'+COLORES[b].bg+'; color:white; border-color:'+COLORES[b].bg if bloque==b else 'background:white; color:'+COLORES[b].bg+'; border-color:'+COLORES[b].bg}}">
   <span style="display:inline-block; width:14px; height:14px; background:{{COLORES[b].bg}}; border-radius:3px; vertical-align:middle; margin-right:4px"></span>
   B{{b}} {{COLORES[b].name}} ({{tot[b]}})
</a>
{% endfor %}
<a href="/?bloque=0" class="btn {{'btn-primary' if bloque==0 else 'btn-link'}} ms-2">TODO</a>
<a href="/configuracion" class="btn btn-dark btn-sm ms-auto">⚙️ CONFIGURAR CALLES</a>
</div>

<!-- VISTA POR BLOQUE -->
{% for b in bloques_ver %}
<div class="header-bloque rounded-top">BLOQUE {{b}} - {{COLORES[b].name}} | {% for c in range(1,CALLES+1) %}C{{c}}:{{config[b][c]}} {% if not loop.last %}| {% endif %}{% endfor %} |</div>
<div class="bg-white border p-2 mb-3 rounded-bottom">
{% for n in range(NIVELES,0,-1) %}
<div class="d-flex align-items-stretch mb-1">
<div style="width:35px; font-weight:900; font-size:16px; padding-top:15px">N{{n}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,CALLES+1) %}
{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set p=pos.get(k) %}
<div class="pos {{'pos-lleno' if p and p.estibas>0 else 'pos-vacio'}}">
<div style="font-weight:800">N{{n}}-C{{c}}</div>
<div style="margin-top:2px; font-size:10px; white-space:nowrap; overflow:hidden">{{(p.producto[:8] if p and p.producto else '')}}</div>
<div style="margin-top:4px">{{p.estibas if p else 0}} est.</div>
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="bg-white p-2 rounded border small text-muted mb-3">Mostrando {{mostrando}} ubicaciones • {{total}} estibas ocupadas • Actualizado hace unos segundos</div>

<!-- FORMULARIO TRABAJO -->
<div class="row">
<div class="col-lg-4">
<div class="card shadow-sm">
<div class="card-header fw-bold" style="background:{{COLORES[bloque_actual].bg if bloque_actual!=0 else '#333'}}; color:white">
Trabajando en BLOQUE {{bloque_actual if bloque_actual!=0 else '1'}} - {{COLORES[bloque_actual].name if bloque_actual!=0 else 'SELECCIONA BLOQUE'}}
</div>
<div class="card-body">
<form method="post" action="/movimiento">
<div class="row g-1">
<div class="col-4"><label class="small fw-bold">Bloque</label><select name="bloque" class="form-select form-select-sm">{% for b in range(1,BLOQUES+1) %}<option value="{{b}}" {{'selected' if b==bloque_actual or (bloque_actual==0 and b==1) else ''}}>B{{b}} {{COLORES[b].name}}</option>{% endfor %}</select></div>
<div class="col-4"><label class="small fw-bold">Nivel</label><select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option value="{{n}}">N{{n}}</option>{% endfor %}</select></div>
<div class="col-4"><label class="small fw-bold">Calle</label><select name="calle" class="form-select form-select-sm">{% for c in range(1,CALLES+1) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select></div>
</div>
<input name="producto" class="form-control form-control-sm mt-2" placeholder="Producto Ej: Kimi PH" required>
<div class="row g-1 mt-1">
<div class="col-6"><select name="tipo" class="form-select form-select-sm"><option value="ALIMENTACION">+ ALIMENTACION</option><option value="DESPACHO">- DESPACHO</option></select></div>
<div class="col-6"><input type="number" name="cantidad" class="form-control form-control-sm" value="1" min="1"></div>
</div>
<input name="responsable" class="form-control form-control-sm mt-2" value="John" placeholder="Responsable">
<button class="btn btn-primary w-100 mt-2 fw-bold">Guardar Movimiento</button>
</form>
</div>
</div>
</div>
</div>

</div></body></html>
"""

HTML_CONFIG = """
<!doctype html><html><head><meta charset="utf-8"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="p-3"><div class="container"><a href="/" class="btn btn-secondary btn-sm mb-3">← Volver</a><h4>CONFIGURAR CALLES - Que producto va en cada calle</h4><form method="post">
{% for b in range(1,BLOQUES+1) %}<div class="card mb-3" style="border-left:5px solid {{COLORES[b].bg}}"><div class="card-header text-white" style="background:{{COLORES[b].bg}}">BLOQUE {{b}} - {{COLORES[b].name}}</div><div class="card-body"><div class="row">{% for c in range(1,CALLES+1) %}<div class="col-md-2 col-6 mb-2"><label class="small fw-bold">Calle {{c}}</label><input name="prod_B{{b}}_C{{c}}" value="{{config[b][c]}}" class="form-control form-control-sm" list="prods"></div>{% endfor %}</div></div></div>{% endfor %}
<datalist id="prods"><option value="Elite"><option value="LIBRE"><option value="Kimi PH"><option value="Familia"><option value="Scott"></datalist>
<button class="btn btn-success w-100 fw-bold">GUARDAR CONFIGURACION</button></form></div></body></html>
"""

@app.route("/")
def index():
    b_actual = int(request.args.get('bloque','1'))
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM posiciones"); rows=cur.fetchall()
    pos={}
    for r in rows:
        if DATABASE_URL: pos[r[0]]={'codigo':r[0],'bloque':r[1],'nivel':r[2],'calle':r[3],'producto':r[4],'estibas':r[5]}
        else: pos[r['codigo']]={'codigo':r['codigo'],'bloque':r['bloque'],'nivel':r['nivel'],'calle':r['calle'],'producto':r['producto'],'estibas':r['estibas']}
    cur.execute("SELECT * FROM config_calles"); rows=cur.fetchall()
    config={b:{c:'LIBRE' for c in range(1,CALLES+1)} for b in range(1,BLOQUES+1)}
    for r in rows:
        if DATABASE_URL: config[r[0]][r[1]]=r[2]
        else: config[r['bloque']][r['calle']]=r['producto_asignado']
    tot={b:0 for b in range(1,BLOQUES+1)}; total=0
    for p in pos.values(): tot[p['bloque']]+=p['estibas']; total+=p['estibas']
    bloques_ver = list(range(1,BLOQUES+1)) if b_actual==0 else [b_actual]
    mostrando = len(bloques_ver)*NIVELES*CALLES
    cur.close(); conn.close()
    ahora=datetime.now().strftime("%H:%M:%S")
    return render_template_string(HTML, pos=pos, config=config, tot=tot, total=total, bloque=b_actual, bloque_actual=b_actual, bloques_ver=bloques_ver, mostrando=mostrando, NIVELES=NIVELES, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES, ahora=ahora)

@app.route("/configuracion", methods=["GET","POST"])
def configuracion():
    conn=get_conn(); cur=conn.cursor()
    if request.method=="POST":
        for b in range(1,BLOQUES+1):
            for c in range(1,CALLES+1):
                prod=request.form.get(f"prod_B{b}_C{c}","").strip()
                if DATABASE_URL: cur.execute("INSERT INTO config_calles VALUES (%s,%s,%s) ON CONFLICT (bloque,calle) DO UPDATE SET producto_asignado=%s",(b,c,prod,prod))
                else: cur.execute("UPDATE config_calles SET producto_asignado=? WHERE bloque=? AND calle=?",(prod,b,c))
        conn.commit(); cur.close(); conn.close()
        return redirect("/")
    cur.execute("SELECT * FROM config_calles"); rows=cur.fetchall()
    config={b:{c:'' for c in range(1,CALLES+1)} for b in range(1,BLOQUES+1)}
    for r in rows:
        if DATABASE_URL: config[r[0]][r[1]]=r[2]
        else: config[r['bloque']][r['calle']]=r['producto_asignado']
    cur.close(); conn.close()
    return render_template_string(HTML_CONFIG, config=config, BLOQUES=BLOQUES, CALLES=CALLES, COLORES=COLORES)

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
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
