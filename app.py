import os
from flask import Flask, request, redirect, render_template_string
from datetime import datetime, date, timedelta

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

def hoy_juliano():
    return date.today().timetuple().tm_yday # hoy 23 sep = 266

def parse_juliano(juliano_str):
    try:
        s=str(juliano_str).strip()
        if not s.isdigit(): return None
        ddd=int(s[-3:]) # tomamos ultimos 3 digitos, si ponen 25266 agarra 266
        if ddd<1 or ddd>366: return None
        hoy=date.today()
        hoy_ddd=hoy.timetuple().tm_yday
        year=hoy.year
        # si el juliano es mayor que hoy, es del año pasado (ej hoy 266 y ponen 360 = diciembre pasado)
        if ddd > hoy_ddd:
            # asumimos año pasado para no dar fecha futura
            try:
                base=date(year-1,1,1)
                return base+timedelta(days=ddd-1)
            except:
                base=date(year,1,1)
                return base+timedelta(days=ddd-1)
        else:
            base=date(year,1,1)
            return base+timedelta(days=ddd-1)
    except: return None

def semaforo_ingreso(fecha_ingreso):
    if not fecha_ingreso: return {"color":"#adb5bd","emoji":"⚪","txt":"SIN FECHA","dias":999}
    hoy=date.today()
    dias=(hoy-fecha_ingreso).days
    if dias<0: dias=0
    if dias<=1: return {"color":"#198754","emoji":"🟢","txt":f"{dias}d","dias":dias}
    if dias<=10: return {"color":"#ffc107","emoji":"🟡","txt":f"{dias}d","dias":dias}
    return {"color":"#dc3545","emoji":"🔴","txt":f"{dias}d","dias":dias}

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if DATABASE_URL:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0, fecha_juliana TEXT DEFAULT '')")
        try: cur.execute("ALTER TABLE posiciones ADD COLUMN IF NOT EXISTS fecha_juliana TEXT DEFAULT ''")
        except: pass
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
.pos-lleno{border-width:3px}
.header-bloque{background:#212529; color:white; padding:8px 12px; font-size:13px; font-weight:700}
.btn-bloque{border-radius:8px; font-weight:700; padding:8px 14px; border:2px solid}
</style>
</head><body class="p-2">
<div class="container-fluid">
<div class="d-flex flex-wrap align-items-center gap-2 mb-2">
<h4 class="m-0 fw-bold">📦 Estantería de Flujo</h4>
<span class="badge bg-dark">{{total}} estibas</span>
<span class="badge" style="background:#198754">🟢 {{tot_verde}} hoy/ayer</span>
<span class="badge" style="background:#ffc107; color:black">🟡 {{tot_amarillo}} 2-10d</span>
<span class="badge" style="background:#dc3545">🔴 {{tot_rojo}} +10d</span>
<span class="ms-auto badge bg-primary fs-6">Hoy 23 Sep = {{hoy_jul}} JULIANO</span>
</div>

<div class="d-flex gap-2 mb-3 flex-wrap">
{% for b in range(1,BLOQUES+1) %}
<a href="/?bloque={{b}}" class="btn btn-bloque {{'text-white' if bloque==b else ''}}" style="{{'background:'+COLORES[b].bg+'; color:white; border-color:'+COLORES[b].bg if bloque==b else 'background:white; color:'+COLORES[b].bg+'; border-color:'+COLORES[b].bg}}">B{{b}} {{COLORES[b].name}} ({{tot[b]}})</a>
{% endfor %}
<a href="/?bloque=0" class="btn {{'btn-primary' if bloque==0 else 'btn-outline-secondary'}}">TODO</a>
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

<div class="row">
<div class="col-lg-5">
<div class="card shadow-sm" style="border:2px solid {{COLORES[bloque_actual].bg if bloque_actual!=0 else '#333'}}">
<div class="card-header fw-bold text-white" style="background:{{COLORES[bloque_actual].bg if bloque_actual!=0 else '#212529'}}">BLOQUE {{bloque_actual}} - Ingreso Juliano (Hoy={{hoy_jul}})</div>
<div class="card-body">
<form method="post" action="/movimiento">
<div class="row g-1">
<div class="col-3"><label class="small fw-bold">Bloque</label><select name="bloque" class="form-select form-select-sm">{% for b in range(1,BLOQUES+1) %}<option value="{{b}}" {{'selected' if b==bloque_actual else ''}}>B{{b}}</option>{% endfor %}</select></div>
<div class="col-3"><label class="small fw-bold">Nivel</label><select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option value="{{n}}">N{{n}}</option>{% endfor %}</select></div>
<div class="col-3"><label class="small fw-bold">Calle</label><select name="calle" class="form-select form-select-sm">{% for c in range(1,CALLES+1) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select></div>
<div class="col-3"><label class="small fw-bold">Cant</label><input type="number" name="cantidad" class="form-control form-control-sm" value="1" min="1"></div>
</div>
<div class="row g-1 mt-2">
<div class="col-6"><label class="small fw-bold">Producto</label><input name="producto" class="form-control form-control-sm" placeholder="Kimi PH" required></div>
<div class="col-6"><label class="small fw-bold">Juliano (Hoy={{hoy_jul}})</label><input name="fecha_juliana" class="form-control form-control-sm" placeholder="Ej: {{hoy_jul}}" value="{{hoy_jul}}" required></div>
</div>
<div class="small text-muted mt-2">Ejemplo: Hoy 23 Sep = 266. Si pones 256 = hace 10 dias (🟡), si pones 200 = 🔴 +10 dias</div>
<div class="row g-1 mt-2">
<div class="col-6"><select name="tipo" class="form-select form-select-sm"><option value="ALIMENTACION">+ ALIMENTAR</option><option value="DESPACHO">- DESPACHAR</option></select></div>
<div class="col-6"><input name="responsable" class="form-control form-control-sm" value="John"></div>
</div>
<button class="btn btn-primary w-100 mt-3 fw-bold">Guardar con Juliano {{hoy_jul}}</button>
</form>
</div>
</div>
</div>
<div class="col-lg-7">
<div class="card"><div class="card-header fw-bold">🔴 Despachar primero - Mas antiguo (FIFO) por Juliano</div>
<div class="card-body p-1" style="max-height:400px; overflow:auto">
<table class="table table-sm small mb-0"><tr><th></th><th>Pos</th><th>Prod</th><th>JUL</th><th>Fecha</th><th>Antig.</th></tr>
{% for item in lista_fefo %}<tr style="background:{{'#ffdddd' if item.sema.color=='#dc3545' else '#fff3cd' if item.sema.color=='#ffc107' else '#d1e7dd'}}"><td>{{item.sema.emoji}}</td><td>{{item.codigo}}</td><td>{{item.producto}}</td><td><b>{{item.fecha_juliana}}</b></td><td>{{item.vence}}</td><td><b>{{item.sema.txt}}</b></td></tr>{% endfor %}
</table>
</div></div>
</div>
</div>
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
        if DATABASE_URL:
            codigo=r[0]; bloque=r[1]; prod=r[4]; est=r[5]; fj=r[6] if len(r)>6 else ''
        else:
            codigo=r['codigo']; bloque=r['bloque']; prod=r['producto']; est=r['estibas']; fj=r['fecha_juliana'] if 'fecha_juliana' in r.keys() else ''
        pos[codigo]={'codigo':codigo,'bloque':bloque,'producto':prod,'estibas':est,'fecha_juliana':fj}
        fecha_obj=parse_juliano(fj) if fj else None
        s=semaforo_ingreso(fecha_obj)
        sema[codigo]=s
        if est>0:
            total+=1; tot[bloque]+=1
            if s['color']=='#dc3545': tot_rojo+=1; sema_bloque[bloque]['rojo']+=1
            elif s['color']=='#ffc107': tot_amarillo+=1; sema_bloque[bloque]['amarillo']+=1
            else: tot_verde+=1; sema_bloque[bloque]['verde']+=1
            lista_fefo.append({"codigo":codigo,"producto":prod,"fecha_juliana":fj,"vence":fecha_obj.strftime("%d/%m/%Y") if fecha_obj else "-", "sema":s})
    lista_fefo.sort(key=lambda x: x['sema']['dias'], reverse=True)
    bloques_ver = list(range(1,BLOQUES+1)) if b_actual==0 else [b_actual]
    cur.close(); conn.close()
    return render_template_string(HTML, pos=pos, sema=sema, tot=tot, total=total, bloque=b_actual, bloque_actual=b_actual, bloques_ver=bloques_ver, NIVELES=NIVELES, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES, tot_rojo=tot_rojo, tot_amarillo=tot_amarillo, tot_verde=tot_verde, sema_bloque=sema_bloque, lista_fefo=lista_fefo, hoy_jul=hoy_juliano())

@app.route("/movimiento", methods=["POST"])
def mov():
    conn=get_conn(); cur=conn.cursor()
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; prod=request.form['producto']; tipo=request.form['tipo']; cant=int(request.form['cantidad']); fj=request.form.get('fecha_juliana','').strip()[-3:]
    q="SELECT estibas FROM posiciones WHERE codigo=%s" if DATABASE_URL else "SELECT estibas FROM posiciones WHERE codigo=?"
    cur.execute(q,(codigo,)); row=cur.fetchone()
    actual=row[0] if row else 0
    if tipo=="DESPACHO" and cant>actual:
        cur.close(); conn.close(); return f"<h3>Solo hay {actual} en {codigo}</h3><a href='/'>Volver</a>"
    nuevo=actual+cant if tipo=="ALIMENTACION" else actual-cant
    if nuevo==0: fj=""
    if DATABASE_URL:
        cur.execute("UPDATE posiciones SET estibas=%s, producto=%s, fecha_juliana=%s WHERE codigo=%s",(nuevo,prod if nuevo>0 else '',fj,codigo))
    else:
        cur.execute("UPDATE posiciones SET estibas=?, producto=?, fecha_juliana=? WHERE codigo=?",(nuevo,prod if nuevo>0 else '',fj,codigo))
    conn.commit(); cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

@app.route("/configuracion")
def configuracion(): return redirect("/")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
