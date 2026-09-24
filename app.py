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

def hoy_juliano():
    return date.today().timetuple().tm_yday

def juliano_a_fecha(ddd):
    try:
        ddd=int(str(ddd)[-3:])
        hoy=date.today()
        hoy_ddd=hoy.timetuple().tm_yday
        if ddd>hoy_ddd:
            base=date(hoy.year-1,1,1)
        else:
            base=date(hoy.year,1,1)
        return base+timedelta(days=ddd-1)
    except: return None

def semaforo(ddd):
    if not ddd: return {"color":"#adb5bd","emoji":"⚪","dias":999,"txt":"-"}
    f=juliano_a_fecha(ddd)
    if not f: return {"color":"#adb5bd","emoji":"⚪","dias":999,"txt":"-"}
    dias=(date.today()-f).days
    if dias<0: dias=0
    if dias<=3: return {"color":"#198754","emoji":"🟢","dias":dias,"txt":f"{dias}d"}
    if dias<=8: return {"color":"#ffc107","emoji":"🟡","dias":dias,"txt":f"{dias}d"}
    return {"color":"#dc3545","emoji":"🔴","dias":dias,"txt":f"{dias}d"}

def init_db():
    conn=get_conn(); cur=conn.cursor()
    if DATABASE_URL:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT)")
        cur.execute("CREATE TABLE IF NOT EXISTS lotes (id SERIAL PRIMARY KEY, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing DATE)")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT INTO posiciones VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",(f"B{b}-N{n}-C{c}",b,n,c))
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT)")
        cur.execute("CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing TEXT)")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0]==0:
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT OR IGNORE INTO posiciones VALUES (?,?,?,?)",(f"B{b}-N{n}-C{c}",b,n,c))
    conn.commit(); cur.close(); conn.close()
init_db()

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estantería de Flujo</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#f5f5f5; font-size:13px}
.pos{border:1.5px solid #ccc; border-radius:6px; background:white; padding:3px 2px; min-height:78px; margin:2px; flex:1; font-size:10px; line-height:11px}
.pos-ocupado{border-width:2.5px}
.lote{font-size:9px; background:#f8f9fa; border-radius:3px; margin:1px 0; padding:1px 2px; white-space:nowrap; overflow:hidden}
.header-bloque{background:#212529; color:white; padding:6px 10px; font-weight:700; font-size:12px; display:flex; justify-content:space-between}
.btn-bloque{border-radius:6px; font-weight:700; padding:6px 12px; border:2px solid; font-size:12px}
</style>
</head><body class="p-2">
<div class="container-fluid">
<div class="d-flex flex-wrap align-items-center gap-2 mb-2">
<h6 class="m-0 fw-bold">📦 Estantería de Flujo <span class="badge bg-dark">{{total_estibas}} estibas</span></h6>
<span class="badge" style="background:#198754">🟢 {{tot_verde}} 0-3d</span>
<span class="badge" style="background:#ffc107; color:black">🟡 {{tot_amarillo}} 4-8d</span>
<span class="badge" style="background:#dc3545">🔴 {{tot_rojo}} 9+d</span>
<span class="ms-auto badge bg-primary fs-6">Hoy = {{hoy_jul}} JULIANO</span>
</div>

<div class="d-flex gap-1 mb-2 flex-wrap">
{% for b in range(1,BLOQUES+1) %}
<a href="/?bloque={{b}}" class="btn btn-bloque {{'text-white' if bloque==b else ''}}" style="{{'background:'+COLORES[b].bg+'; color:white; border-color:'+COLORES[b].bg if bloque==b else 'background:white; color:'+COLORES[b].bg+'; border-color:'+COLORES[b].bg}}">B{{b}} {{COLORES[b].name}} ({{tot_bloque[b]}})</a>
{% endfor %}
<a href="/?bloque=0" class="btn btn-bloque {{'btn-dark text-white' if bloque==0 else 'btn-outline-secondary'}}">TODO ({{total_estibas}})</a>
<a href="/configuracion" class="btn btn-dark btn-sm ms-auto">⚙️ EDITAR JULIANOS ({{total_lotes}} lotes)</a>
</div>

{% for b in bloques_ver %}
<div class="header-bloque rounded-top"><span>BLOQUE {{b}} - {{COLORES[b].name}}</span><span>🟢{{sema_bloque[b].verde}} 🟡{{sema_bloque[b].amarillo}} 🔴{{sema_bloque[b].rojo}}</span></div>
<div class="bg-white border p-1 mb-3 rounded-bottom">
{% for n in range(NIVELES,0,-1) %}
<div class="d-flex align-items-stretch mb-1">
<div style="width:28px; font-weight:900; font-size:12px; padding-top:10px">N{{n}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,CALLES+1) %}
{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set lotes=grupos.get(k,[]) %}{% set total=sum(l.estibas for l in lotes) %}
{% set s=sema_pos.get(k) %}
<div class="pos {{'pos-ocupado' if total>0 else ''}}" style="border-color:{{s.color if total>0 else '#ccc'}}; {{'background:#fff5f5' if s.color=='#dc3545' and total>0 else ''}}">
<div style="font-weight:800; font-size:10px">N{{n}}-C{{c}}</div>
<div style="font-weight:700">{{total}} est.</div>
{% for lote in lotes[:3] %}
<div class="lote" style="border-left:3px solid {{lote.sema.color}}">{{lote.producto}} {{lote.estibas}}e J{{lote.juliano}} {{lote.sema.emoji}}</div>
{% endfor %}
{% if lotes|length>3 %}<div class="lote">+{{lotes|length-3}} lotes más</div>{% endif %}
{% if total==0 %}<div class="text-muted">0 est.</div>{% endif %}
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="row">
<div class="col-lg-4">
<div class="card shadow-sm" style="border:2px solid {{COLORES[bloque].bg if bloque!=0 else '#000'}}">
<div class="card-header fw-bold text-white py-1" style="background:{{COLORES[bloque].bg if bloque!=0 else '#000'}}">BLOQUE {{bloque if bloque!=0 else '1'}} - Hoy={{hoy_jul}} - Material completo</div>
<div class="card-body p-2">
<form method="post" action="/movimiento">
<div class="row g-1">
<div class="col-3"><select name="bloque" class="form-select form-select-sm">{% for b in range(1,BLOQUES+1) %}<option value="{{b}}" {{'selected' if b==bloque_actual else ''}}>B{{b}}</option>{% endfor %}</select></div>
<div class="col-3"><select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option value="{{n}}">N{{n}}</option>{% endfor %}</select></div>
<div class="col-3"><select name="calle" class="form-select form-select-sm">{% for c in range(1,CALLES+1) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select></div>
<div class="col-3"><input type="number" name="cantidad" class="form-control form-control-sm" value="1" min="1"></div>
</div>
<input name="producto" class="form-control form-control-sm mt-2" placeholder="Material completo ej: 12005778" required value="12005778">
<div class="row g-1 mt-1">
<div class="col-6"><input name="juliano" class="form-control form-control-sm" placeholder="Juliano {{hoy_jul}}" value="{{hoy_jul}}" required type="number" min="1" max="366"></div>
<div class="col-6"><select name="tipo" class="form-select form-select-sm"><option value="ALIMENTACION">+ ALIMENTAR</option><option value="DESPACHO">- DESPACHAR</option></select></div>
</div>
<div class="small text-muted mt-1">Ej: 10 estibas J255 + 4 estibas J266 del mismo 12005778 se suman y se ven separadas. FIFO descuenta el más viejo primero.</div>
<button class="btn btn-primary w-100 mt-2 btn-sm fw-bold">Guardar</button>
</form>
</div>
</div>
</div>
<div class="col-lg-8">
<div class="card"><div class="card-header fw-bold py-1">🔴 Despacho FIFO - Mas antiguo primero (Juliano menor)</div>
<div class="card-body p-1" style="max-height:420px; overflow:auto">
<table class="table table-sm small mb-0"><tr><th></th><th>Pos</th><th>Material completo</th><th>Est</th><th>JUL</th><th>Fecha</th><th>Antig</th></tr>
{% for l in lista_fifo %}<tr style="background:{{'#ffdddd' if l.sema.color=='#dc3545' else '#fff3cd' if l.sema.color=='#ffc107' else '#d1e7dd'}}"><td>{{l.sema.emoji}}</td><td>{{l.codigo}}</td><td><b>{{l.producto}}</b></td><td>{{l.estibas}}</td><td><b>{{l.juliano}}</b></td><td>{{l.fecha_str}}</td><td><b>{{l.sema.txt}}</b></td></tr>{% endfor %}
</table>
</div></div>
</div>
</div>

</div></body></html>
"""

HTML_EDIT = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Editar Julianos</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
</head><body class="p-3">
<div class="container-fluid">
<a href="/" class="btn btn-secondary btn-sm mb-2">← Volver</a>
<h5 class="fw-bold">⚙️ Editar Julianos - Hoy={{hoy_jul}} (23 Sep=266) - Semaforo: 🟢0-3d 🟡4-8d 🔴9+d</h5>
<form method="post">
<table class="table table-sm table-bordered small">
<tr class="table-dark"><th>ID</th><th>Codigo</th><th>Material completo</th><th>Estibas</th><th>Juliano</th><th>Fecha</th><th>Semaforo</th><th>Borrar</th></tr>
{% for l in lotes %}
<tr style="background:{{'#d1e7dd' if l.sema.color=='#198754' else '#fff3cd' if l.sema.color=='#ffc107' else '#f8d7da'}}">
<td>{{l.id}}</td><td>{{l.codigo}}</td>
<td><input name="prod_{{l.id}}" value="{{l.producto}}" class="form-control form-control-sm" style="width:110px"></td>
<td><input name="est_{{l.id}}" value="{{l.estibas}}" type="number" class="form-control form-control-sm" style="width:60px"></td>
<td><input name="jul_{{l.id}}" value="{{l.juliano}}" type="number" min="1" max="366" class="form-control form-control-sm" style="width:70px"></td>
<td>{{l.fecha_str}}</td><td>{{l.sema.emoji}} {{l.sema.txt}}</td>
<td><input type="checkbox" name="del_{{l.id}}"></td>
</tr>
{% endfor %}
</table>
<button class="btn btn-success w-100 fw-bold">💾 GUARDAR CAMBIOS</button>
</form>
</div></body></html>
"""

@app.route("/")
def index():
    b_actual = int(request.args.get('bloque','1'))
    hoy_jul=hoy_juliano()
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT id,codigo,bloque,nivel,calle,producto,juliano,estibas FROM lotes ORDER BY juliano ASC")
    rows=cur.fetchall()
    lotes=[]
    grupos={} # codigo -> lista
    tot_bloque={b:0 for b in range(1,BLOQUES+1)}
    total_estibas=0
    tot_verde=tot_amarillo=tot_rojo=0
    sema_bloque={b:{"verde":0,"amarillo":0,"rojo":0} for b in range(1,BLOQUES+1)}
    sema_pos={}
    lista_fifo=[]
    for r in rows:
        if DATABASE_URL: id_,codigo,bloque,nivel,calle,producto,juliano,estibas=r
        else: id_=r['id']; codigo=r['codigo']; bloque=r['bloque']; nivel=r['nivel']; calle=r['calle']; producto=r['producto']; juliano=r['juliano']; estibas=r['estibas']
        if estibas<=0: continue
        s=semaforo(juliano)
        f=juliano_a_fecha(juliano)
        fecha_str=f.strftime("%d/%m/%Y") if f else "-"
        obj={"id":id_,"codigo":codigo,"bloque":bloque,"nivel":nivel,"calle":calle,"producto":producto,"juliano":juliano,"estibas":estibas,"sema":s,"fecha_str":fecha_str,"fecha":f}
        lotes.append(obj)
        grupos.setdefault(codigo, []).append(obj)
        tot_bloque[bloque]+=estibas
        total_estibas+=estibas
        if s['color']=='#dc3545': tot_rojo+=1; sema_bloque[bloque]['rojo']+=1
        elif s['color']=='#ffc107': tot_amarillo+=1; sema_bloque[bloque]['amarillo']+=1
        else: tot_verde+=1; sema_bloque[bloque]['verde']+=1
        lista_fifo.append(obj)
    # semaforo por posicion = el mas viejo (rojo manda)
    for codigo, lst in grupos.items():
        lst_sorted=sorted(lst, key=lambda x: x['sema']['dias'], reverse=True)
        sema_pos[codigo]=lst_sorted[0]['sema']
        grupos[codigo]=sorted(lst, key=lambda x: x['juliano'])
    lista_fifo=sorted(lista_fifo, key=lambda x: x['juliano'])
    bloques_ver = list(range(1,BLOQUES+1)) if b_actual==0 else [b_actual]
    cur.close(); conn.close()
    return render_template_string(HTML, grupos=grupos, sema_pos=sema_pos, tot_bloque=tot_bloque, total_estibas=total_estibas, total_lotes=len(lotes), bloque=b_actual, bloque_actual=b_actual if b_actual!=0 else 1, bloques_ver=bloques_ver, NIVELES=NIVELES, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES, tot_verde=tot_verde, tot_amarillo=tot_amarillo, tot_rojo=tot_rojo, sema_bloque=sema_bloque, lista_fifo=lista_fifo, hoy_jul=hoy_jul)

@app.route("/configuracion", methods=["GET","POST"])
def configuracion():
    conn=get_conn(); cur=conn.cursor()
    if request.method=="POST":
        cur.execute("SELECT id FROM lotes")
        for r in cur.fetchall():
            id_=r[0] if DATABASE_URL else r['id']
            if request.form.get(f"del_{id_}")=="on":
                cur.execute("DELETE FROM lotes WHERE id=%s" if DATABASE_URL else "DELETE FROM lotes WHERE id=?",(id_,))
            else:
                prod=request.form.get(f"prod_{id_}")
                est=request.form.get(f"est_{id_}")
                jul=request.form.get(f"jul_{id_}")
                try:
                    jul=int(jul); est=int(est)
                    f=juliano_a_fecha(jul)
                    if DATABASE_URL: cur.execute("UPDATE lotes SET producto=%s, estibas=%s, juliano=%s, fecha_ing=%s WHERE id=%s",(prod,est,jul,f,id_))
                    else: cur.execute("UPDATE lotes SET producto=?, estibas=?, juliano=?, fecha_ing=? WHERE id=?",(prod,est,jul,f.isoformat() if f else None,id_))
                except: pass
        conn.commit()
    cur.execute("SELECT id,codigo,bloque,producto,juliano,estibas FROM lotes ORDER BY bloque, codigo, juliano")
    rows=cur.fetchall()
    lotes=[]
    for r in rows:
        if DATABASE_URL: id_,codigo,bloque,producto,juliano,estibas=r
        else: id_=r['id']; codigo=r['codigo']; bloque=r['bloque']; producto=r['producto']; juliano=r['juliano']; estibas=r['estibas']
        f=juliano_a_fecha(juliano)
        lotes.append({"id":id_,"codigo":codigo,"bloque":bloque,"producto":producto,"juliano":juliano,"estibas":estibas,"sema":semaforo(juliano),"fecha_str":f.strftime("%d/%m/%Y") if f else "-"})
    cur.close(); conn.close()
    return render_template_string(HTML_EDIT, lotes=lotes, hoy_jul=hoy_juliano())

@app.route("/movimiento", methods=["POST"])
def mov():
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; producto=request.form['producto'].strip(); tipo=request.form['tipo']; cant=int(request.form['cantidad']); jul=int(request.form['juliano'])
    conn=get_conn(); cur=conn.cursor()
    if tipo=="ALIMENTACION":
        f=juliano_a_fecha(jul)
        # si ya existe mismo producto y mismo juliano en esa calle, suma
        if DATABASE_URL:
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s AND producto=%s AND juliano=%s",(codigo,producto,jul))
        else:
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=? AND producto=? AND juliano=?",(codigo,producto,jul))
        row=cur.fetchone()
        if row:
            id_=row[0]; est=row[1]
            new_est=est+cant
            if DATABASE_URL: cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s",(new_est,id_))
            else: cur.execute("UPDATE lotes SET estibas=? WHERE id=?",(new_est,id_))
        else:
            if DATABASE_URL: cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",(codigo,b,n,c,producto,jul,cant,f))
            else: cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (?,?,?,?,?,?,?,?)",(codigo,b,n,c,producto,jul,cant,f.isoformat() if f else None))
    else: # DESPACHO FIFO por ese codigo
        if DATABASE_URL:
            cur.execute("SELECT id, estibas, juliano FROM lotes WHERE codigo=%s ORDER BY juliano ASC",(codigo,))
        else:
            cur.execute("SELECT id, estibas, juliano FROM lotes WHERE codigo=? ORDER BY juliano ASC",(codigo,))
        por_despachar=cant
        for r in cur.fetchall():
            if por_despachar<=0: break
            id_=r[0]; est=r[1]
            if est<=por_despachar:
                por_despachar-=est
                cur.execute("DELETE FROM lotes WHERE id=%s" if DATABASE_URL else "DELETE FROM lotes WHERE id=?",(id_,))
            else:
                new_est=est-por_despachar
                por_despachar=0
                cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if DATABASE_URL else "UPDATE lotes SET estibas=? WHERE id=?",(new_est,id_))
    conn.commit(); cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
