import os
from flask import Flask, request, redirect, render_template_string
from datetime import date, timedelta

app = Flask(__name__)
NIVELES, CALLES, BLOQUES = 6, 10, 4
COLORES = {1:{"bg":"#0d6efd","name":"AZUL"},2:{"bg":"#198754","name":"VERDE"},3:{"bg":"#fd7e14","name":"NARANJA"},4:{"bg":"#6f42c1","name":"MORADO"}}
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

def hoy_juliano(): return date.today().timetuple().tm_yday

def parse_juliano(juliano_str):
    try:
        s=str(juliano_str).strip()
        if not s.isdigit(): return None
        ddd=int(s[-3:])
        if ddd<1 or ddd>366: return None
        hoy=date.today(); hoy_ddd=hoy.timetuple().tm_yday; year=hoy.year
        if ddd > hoy_ddd:
            base=date(year-1,1,1)
            return base+timedelta(days=ddd-1)
        else:
            base=date(year,1,1)
            return base+timedelta(days=ddd-1)
    except: return None

def semaforo_ingreso(fecha_ingreso):
    if not fecha_ingreso: return {"color":"#adb5bd","emoji":"⚪","txt":"SIN FECHA","dias":999}
    hoy=date.today(); dias=(hoy-fecha_ingreso).days
    if dias<0: dias=0
    if dias<=1: return {"color":"#198754","emoji":"🟢","txt":f"{dias}d","dias":dias}
    if dias<=10: return {"color":"#ffc107","emoji":"🟡","txt":f"{dias}d","dias":dias}
    return {"color":"#dc3545","emoji":"🔴","txt":f"{dias}d","dias":dias}

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if DATABASE_URL:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0, fecha_juliana TEXT DEFAULT '')")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT INTO posiciones VALUES (%s,%s,%s,%s,'',0,'') ON CONFLICT DO NOTHING",(f"B{b}-N{n}-C{c}",b,n,c))
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0, fecha_juliana TEXT DEFAULT '')")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT OR IGNORE INTO posiciones VALUES (?,?,?,?, '',0,'')",(f"B{b}-N{n}-C{c}",b,n,c))
    conn.commit(); cur.close(); conn.close()
init_db()

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estantería de Flujo</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#f8f9fa}
.pos{border:2px solid #dee2e6; border-radius:8px; background:white; text-align:center; padding:4px 1px; min-height:72px; font-size:10px; margin:3px; flex:1}
.header-bloque{background:#212529; color:white; padding:8px 12px; font-size:13px; font-weight:700}
.btn-bloque{border-radius:8px; font-weight:700; padding:8px 14px; border:2px solid}
</style>
</head><body class="p-2">
<div class="container-fluid">
<div class="d-flex flex-wrap align-items-center gap-2 mb-2">
<h4 class="m-0 fw-bold">📦 Estantería de Flujo</h4>
<span class="badge bg-dark">{{total}} estibas</span>
<span class="badge" style="background:#198754">🟢 {{tot_verde}}</span>
<span class="badge" style="background:#ffc107; color:black">🟡 {{tot_amarillo}}</span>
<span class="badge" style="background:#dc3545">🔴 {{tot_rojo}}</span>
<span class="ms-auto badge bg-primary fs-6">Hoy = {{hoy_jul}} JULIANO</span>
</div>
<div class="d-flex gap-2 mb-3 flex-wrap">
{% for b in range(1,BLOQUES+1) %}
<a href="/?bloque={{b}}" class="btn btn-bloque {{'text-white' if bloque==b else ''}}" style="{{'background:'+COLORES[b].bg+'; color:white; border-color:'+COLORES[b].bg if bloque==b else 'background:white; color:'+COLORES[b].bg+'; border-color:'+COLORES[b].bg}}">B{{b}} {{COLORES[b].name}} ({{tot[b]}})</a>
{% endfor %}
<a href="/?bloque=0" class="btn {{'btn-primary' if bloque==0 else 'btn-outline-secondary'}}">TODO</a>
<a href="/configuracion" class="btn btn-dark ms-auto fw-bold">⚙️ EDITAR JULIANOS ({{total}} ocupadas)</a>
</div>
{% for b in bloques_ver %}
<div class="header-bloque rounded-top d-flex justify-content-between"><span>BLOQUE {{b}} - {{COLORES[b].name}}</span><span>🟢{{sema_bloque[b].verde}} 🟡{{sema_bloque[b].amarillo}} 🔴{{sema_bloque[b].rojo}}</span></div>
<div class="bg-white border p-2 mb-4 rounded-bottom">
{% for n in range(NIVELES,0,-1) %}
<div class="d-flex align-items-stretch mb-1">
<div style="width:35px; font-weight:900; font-size:15px; padding-top:18px">N{{n}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,CALLES+1) %}
{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set p=pos.get(k) %}{% set s=sema.get(k) %}
<div class="pos" style="border-color:{{s.color if p.estibas>0 else '#dee2e6'}}">
<div style="font-weight:800">N{{n}}-C{{c}}</div>
<div style="font-size:9px">{{p.producto[:7] if p.producto else ''}}</div>
<div>{{p.estibas}} est.</div>
{% if p.estibas>0 %}<div style="font-size:9px; margin-top:2px">{{s.emoji}} J:{{p.fecha_juliana}}<br>{{s.txt}}</div>{% endif %}
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}
<div class="row"><div class="col-lg-5"><div class="card shadow-sm" style="border:2px solid {{COLORES[bloque_actual].bg}}"><div class="card-header fw-bold text-white" style="background:{{COLORES[bloque_actual].bg}}">BLOQUE {{bloque_actual}} - Hoy={{hoy_jul}}</div><div class="card-body"><form method="post" action="/movimiento"><div class="row g-1"><div class="col-3"><select name="bloque" class="form-select form-select-sm">{% for b in range(1,BLOQUES+1) %}<option value="{{b}}" {{'selected' if b==bloque_actual else ''}}>B{{b}}</option>{% endfor %}</select></div><div class="col-3"><select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option value="{{n}}">N{{n}}</option>{% endfor %}</select></div><div class="col-3"><select name="calle" class="form-select form-select-sm">{% for c in range(1,CALLES+1) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select></div><div class="col-3"><input type="number" name="cantidad" class="form-control form-control-sm" value="1" min="1"></div></div><div class="row g-1 mt-2"><div class="col-6"><input name="producto" class="form-control form-control-sm" placeholder="Producto" required></div><div class="col-6"><input name="fecha_juliana" class="form-control form-control-sm" placeholder="Juliano {{hoy_jul}}" value="{{hoy_jul}}" required></div></div><div class="row g-1 mt-2"><div class="col-6"><select name="tipo" class="form-select form-select-sm"><option value="ALIMENTACION">+ ALIMENTAR</option><option value="DESPACHO">- DESPACHAR</option></select></div><div class="col-6"><button class="btn btn-primary btn-sm w-100">Guardar</button></div></div></form></div></div></div><div class="col-lg-7"><div class="card"><div class="card-header fw-bold">🔴 Despachar primero - FIFO</div><div class="card-body p-1" style="max-height:400px; overflow:auto"><table class="table table-sm small mb-0"><tr><th></th><th>Pos</th><th>Prod</th><th>JUL</th><th>Fecha</th><th>Antig</th></tr>{% for item in lista_fefo %}<tr style="background:{{'#ffdddd' if item.sema.color=='#dc3545' else '#fff3cd' if item.sema.color=='#ffc107' else '#d1e7dd'}}"><td>{{item.sema.emoji}}</td><td>{{item.codigo}}</td><td>{{item.producto}}</td><td><b>{{item.fecha_juliana}}</b></td><td>{{item.vence}}</td><td><b>{{item.sema.txt}}</b></td></tr>{% endfor %}</table></div></div></div></div>
</div></body></html>
"""

HTML_EDIT = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Editar Julianos - Estantería de Flujo</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-3">
<div class="container-fluid">
<a href="/" class="btn btn-secondary btn-sm mb-3">← Volver a Estantería de Flujo</a>
<h4 class="fw-bold">⚙️ Configuración - Editar todas las posiciones ocupadas</h4>
<div class="alert alert-info small">Hoy es <b>{{hoy_jul}} juliano</b> (23 Sep = 266). 🟢 0-1 día = verde, 🟡 2-10 días = amarillo, 🔴 +10 días = rojo. Aquí puedes corregir el juliano de todo lo que ya tienes guardado.</div>
<form method="post">
<div class="card"><div class="card-body p-0">
<table class="table table-sm table-bordered small mb-0">
<thead class="table-dark"><tr><th>Bloque</th><th>Posición</th><th>Producto</th><th>Estibas</th><th>Juliano Actual</th><th>Nuevo Juliano</th><th>Semaforo</th></tr></thead>
<tbody>
{% for p in ocupadas %}
{% set s=sema[p.codigo] %}
<tr style="background:{{'#d1e7dd' if s.color=='#198754' else '#fff3cd' if s.color=='#ffc107' else '#f8d7da' if s.color=='#dc3545' else ''}}">
<td>B{{p.bloque}} {{COLORES[p.bloque].name}}</td>
<td><b>{{p.codigo}}</b> (N{{p.nivel}}-C{{p.calle}})</td>
<td><input name="prod_{{p.codigo}}" value="{{p.producto}}" class="form-control form-control-sm"></td>
<td><input name="est_{{p.codigo}}" value="{{p.estibas}}" type="number" min="0" class="form-control form-control-sm" style="width:70px"></td>
<td>{{p.fecha_juliana}} - {{s.emoji}} {{s.txt}}</td>
<td><input name="jul_{{p.codigo}}" value="{{p.fecha_juliana}}" class="form-control form-control-sm" placeholder="{{hoy_jul}}" style="width:90px; font-weight:bold"></td>
<td>{{s.emoji}}</td>
</tr>
{% endfor %}
{% if ocupadas|length==0 %}
<tr><td colspan="7" class="text-center p-4 text-muted">No hay posiciones ocupadas. Ve y alimenta primero.</td></tr>
{% endif %}
</tbody>
</table>
</div></div>
<button class="btn btn-success w-100 mt-3 fw-bold py-2">💾 GUARDAR TODOS LOS JULIANOS</button>
</form>

<hr class="my-4">
<h5>Todas las posiciones (240) - Edición rápida</h5>
<form method="post" action="/configuracion_todo">
<div style="max-height:500px; overflow:auto; border:1px solid #ddd">
<table class="table table-sm small">
<tr><th>Codigo</th><th>Prod</th><th>Est</th><th>Juliano</th></tr>
{% for b in range(1,BLOQUES+1) %}{% for n in range(1,NIVELES+1) %}{% for c in range(1,CALLES+1) %}
{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set p=pos.get(k) %}
<tr><td>{{k}}</td><td><input name="prod_{{k}}" value="{{p.producto}}" class="form-control form-control-sm"></td><td><input name="est_{{k}}" value="{{p.estibas}}" type="number" class="form-control form-control-sm" style="width:60px"></td><td><input name="jul_{{k}}" value="{{p.fecha_juliana}}" class="form-control form-control-sm" style="width:70px"></td></tr>
{% endfor %}{% endfor %}{% endfor %}
</table>
</div>
<button class="btn btn-dark w-100 mt-2">Guardar TODO (240 posiciones)</button>
</form>

</div></body></html>
"""

@app.route("/")
def index():
    b_actual = int(request.args.get('bloque','1'))
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM posiciones"); rows=cur.fetchall()
    pos={}; sema={}; tot={b:0 for b in range(1,BLOQUES+1)}; total=0
    tot_rojo=tot_amarillo=tot_verde=0
    sema_bloque={b:{"rojo":0,"amarillo":0,"verde":0} for b in range(1,BLOQUES+1)}
    lista_fefo=[]
    for r in rows:
        if DATABASE_URL: codigo=r[0]; bloque=r[1]; nivel=r[2]; calle=r[3]; prod=r[4]; est=r[5]; fj=r[6] if len(r)>6 else ''
        else: codigo=r['codigo']; bloque=r['bloque']; nivel=r['nivel']; calle=r['calle']; prod=r['producto']; est=r['estibas']; fj=r['fecha_juliana']
        pos[codigo]={'codigo':codigo,'bloque':bloque,'nivel':nivel,'calle':calle,'producto':prod,'estibas':est,'fecha_juliana':fj}
        s=semaforo_ingreso(parse_juliano(fj) if fj else None); sema[codigo]=s
        if est>0:
            total+=1; tot[bloque]+=1
            if s['color']=='#dc3545': tot_rojo+=1; sema_bloque[bloque]['rojo']+=1
            elif s['color']=='#ffc107': tot_amarillo+=1; sema_bloque[bloque]['amarillo']+=1
            else: tot_verde+=1; sema_bloque[bloque]['verde']+=1
            lista_fefo.append({"codigo":codigo,"producto":prod,"fecha_juliana":fj,"vence":parse_juliano(fj).strftime("%d/%m") if parse_juliano(fj) else "-", "sema":s})
    lista_fefo.sort(key=lambda x: x['sema']['dias'], reverse=True)
    bloques_ver = list(range(1,BLOQUES+1)) if b_actual==0 else [b_actual]
    cur.close(); conn.close()
    return render_template_string(HTML, pos=pos, sema=sema, tot=tot, total=total, bloque=b_actual, bloque_actual=b_actual, bloques_ver=bloques_ver, NIVELES=NIVELES, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES, tot_rojo=tot_rojo, tot_amarillo=tot_amarillo, tot_verde=tot_verde, sema_bloque=sema_bloque, lista_fefo=lista_fefo, hoy_jul=hoy_juliano())

@app.route("/configuracion", methods=["GET","POST"])
def configuracion():
    conn=get_conn(); cur=conn.cursor()
    if request.method=="POST":
        cur.execute("SELECT codigo FROM posiciones")
        for r in cur.fetchall():
            codigo=r[0] if DATABASE_URL else r['codigo']
            fj=request.form.get(f"jul_{codigo}")
            prod=request.form.get(f"prod_{codigo}")
            est=request.form.get(f"est_{codigo}")
            if fj is not None:
                if DATABASE_URL: cur.execute("UPDATE posiciones SET fecha_juliana=%s, producto=%s, estibas=%s WHERE codigo=%s",(fj[-3:] if fj else '', prod, int(est or 0), codigo))
                else: cur.execute("UPDATE posiciones SET fecha_juliana=?, producto=?, estibas=? WHERE codigo=?",(fj[-3:] if fj else '', prod, int(est or 0), codigo))
        conn.commit(); cur.close(); conn.close()
        return redirect("/configuracion")
    cur.execute("SELECT * FROM posiciones WHERE estibas>0 ORDER BY bloque, nivel DESC, calle")
    rows=cur.fetchall()
    ocupadas=[]; pos={}; sema={}
    for r in rows:
        if DATABASE_URL: codigo=r[0]; bloque=r[1]; nivel=r[2]; calle=r[3]; prod=r[4]; est=r[5]; fj=r[6] if len(r)>6 else ''
        else: codigo=r['codigo']; bloque=r['bloque']; nivel=r['nivel']; calle=r['calle']; prod=r['producto']; est=r['estibas']; fj=r['fecha_juliana']
        ocupadas.append({"codigo":codigo,"bloque":bloque,"nivel":nivel,"calle":calle,"producto":prod,"estibas":est,"fecha_juliana":fj})
        pos[codigo]={"producto":prod,"estibas":est,"fecha_juliana":fj}
        sema[codigo]=semaforo_ingreso(parse_juliano(fj) if fj else None)
    # para tabla completa
    cur.execute("SELECT * FROM posiciones")
    for r in cur.fetchall():
        if DATABASE_URL: codigo=r[0]; prod=r[4]; est=r[5]; fj=r[6] if len(r)>6 else ''
        else: codigo=r['codigo']; prod=r['producto']; est=r['estibas']; fj=r['fecha_juliana']
        if codigo not in pos: pos[codigo]={"producto":prod,"estibas":est,"fecha_juliana":fj}
    cur.close(); conn.close()
    return render_template_string(HTML_EDIT, ocupadas=ocupadas, pos=pos, sema=sema, BLOQUES=BLOQUES, NIVELES=NIVELES, CALLES=CALLES, COLORES=COLORES, hoy_jul=hoy_juliano())

@app.route("/configuracion_todo", methods=["POST"])
def configuracion_todo():
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT codigo FROM posiciones")
    for r in cur.fetchall():
        codigo=r[0] if DATABASE_URL else r['codigo']
        fj=request.form.get(f"jul_{codigo}")
        prod=request.form.get(f"prod_{codigo}")
        est=request.form.get(f"est_{codigo}")
        if fj is not None:
            if DATABASE_URL: cur.execute("UPDATE posiciones SET fecha_juliana=%s, producto=%s, estibas=%s WHERE codigo=%s",(fj[-3:] if fj else '', prod, int(est or 0), codigo))
            else: cur.execute("UPDATE posiciones SET fecha_juliana=?, producto=?, estibas=? WHERE codigo=?",(fj[-3:] if fj else '', prod, int(est or 0), codigo))
    conn.commit(); cur.close(); conn.close()
    return redirect("/")

@app.route("/movimiento", methods=["POST"])
def mov():
    conn=get_conn(); cur=conn.cursor()
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; prod=request.form['producto']; tipo=request.form['tipo']; cant=int(request.form['cantidad']); fj=request.form.get('fecha_juliana','').strip()[-3:]
    q="SELECT estibas FROM posiciones WHERE codigo=%s" if DATABASE_URL else "SELECT estibas FROM posiciones WHERE codigo=?"
    cur.execute(q,(codigo,)); row=cur.fetchone(); actual=row[0] if row else 0
    if tipo=="DESPACHO" and cant>actual:
        cur.close(); conn.close(); return f"<h3>Solo hay {actual} en {codigo}</h3><a href='/'>Volver</a>"
    nuevo=actual+cant if tipo=="ALIMENTACION" else actual-cant
    if nuevo==0: fj=""
    if DATABASE_URL: cur.execute("UPDATE posiciones SET estibas=%s, producto=%s, fecha_juliana=%s WHERE codigo=%s",(nuevo,prod if nuevo>0 else '',fj,codigo))
    else: cur.execute("UPDATE posiciones SET estibas=?, producto=?, fecha_juliana=? WHERE codigo=?",(nuevo,prod if nuevo>0 else '',fj,codigo))
    conn.commit(); cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
