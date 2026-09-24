import os, json, sqlite3
from flask import Flask, request, redirect, render_template_string
from datetime import date, datetime, timedelta

app = Flask(__name__)

# CONFIG persistente
CONFIG_FILE = "/tmp/config_est.json"
DEFAULT_CONFIG = {"bloques":4, "niveles":6, "calles":10, "verde_max":3, "amarillo_max":8}
def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE,'r') as f: return {**DEFAULT_CONFIG, **json.load(f)}
    except: pass
    return DEFAULT_CONFIG.copy()
def save_config(cfg):
    try:
        with open(CONFIG_FILE,'w') as f: json.dump(cfg,f)
    except: pass
CONFIG = load_config()

def get_conn():
    db_url=os.environ.get("DATABASE_URL","")
    if db_url:
        try:
            if db_url.startswith("postgres://"): db_url=db_url.replace("postgres://","postgresql://",1)
            import psycopg2; return psycopg2.connect(db_url, sslmode='require')
        except Exception as e: print(e)
    conn=sqlite3.connect("/tmp/estanteria.db", check_same_thread=False)
    conn.row_factory=sqlite3.Row; return conn

def init_db():
    try:
        conn=get_conn(); cur=conn.cursor()
        if os.environ.get("DATABASE_URL"):
            cur.execute("CREATE TABLE IF NOT EXISTS lotes (id SERIAL PRIMARY KEY, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing DATE)")
        else:
            cur.execute("CREATE TABLE IF NOT EXISTS lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing TEXT)")
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(e)
init_db()

def hoy_juliano(): return (datetime.utcnow()-timedelta(hours=5)).timetuple().tm_yday
def hoy_fecha_col(): return (datetime.utcnow()-timedelta(hours=5)).date()
def juliano_a_fecha(ddd):
    try:
        ddd=int(str(ddd)[-3:]); hoy=hoy_fecha_col()
        base=date(hoy.year-1,1,1) if ddd>hoy.timetuple().tm_yday else date(hoy.year,1,1)
        return base+timedelta(days=ddd-1)
    except: return None
def semaforo(ddd):
    f=juliano_a_fecha(ddd)
    if not f: return {"color":"#6c757d","emoji":"⚪","dias":999,"txt":"-"}
    dias=(hoy_fecha_col()-f).days; dias=max(dias,0)
    if dias<=CONFIG["verde_max"]: return {"color":"#198754","emoji":"🟢","dias":dias,"txt":f"{dias}d"}
    if dias<=CONFIG["amarillo_max"]: return {"color":"#ffc107","emoji":"🟡","dias":dias,"txt":f"{dias}d"}
    return {"color":"#dc3545","emoji":"🔴","dias":dias,"txt":f"{dias}d"}

@app.route("/reset_db")
def reset_db():
    try: conn=get_conn(); cur=conn.cursor(); cur.execute("DROP TABLE IF EXISTS lotes"); conn.commit(); cur.close(); conn.close()
    except: pass
    init_db(); return redirect("/")

@app.route("/config", methods=["GET","POST"])
def config():
    global CONFIG
    if request.method=="POST":
        CONFIG["bloques"]=int(request.form.get("bloques",4))
        CONFIG["niveles"]=int(request.form.get("niveles",6))
        CONFIG["calles"]=int(request.form.get("calles",10))
        CONFIG["verde_max"]=int(request.form.get("verde",3))
        CONFIG["amarillo_max"]=int(request.form.get("amarillo",8))
        save_config(CONFIG); return redirect("/")
    return f"""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div style="max-width:500px;margin:30px auto;" class="bg-white p-4 rounded shadow">
    <h4>⚙️ Configuración Estantería</h4>
    <form method="post">
    <div class="row g-2">
    <div class="col-4"><label class="small fw-bold">Nº Bloques</label><input name="bloques" type="number" min="1" max="20" value="{CONFIG['bloques']}" class="form-control"></div>
    <div class="col-4"><label class="small fw-bold">Nº Niveles (N)</label><input name="niveles" type="number" min="1" max="10" value="{CONFIG['niveles']}" class="form-control"></div>
    <div class="col-4"><label class="small fw-bold">Nº Calles (C)</label><input name="calles" type="number" min="1" max="20" value="{CONFIG['calles']}" class="form-control"></div>
    <div class="col-6"><label class="small fw-bold">Verde hasta día</label><input name="verde" type="number" value="{CONFIG['verde_max']}" class="form-control"></div>
    <div class="col-6"><label class="small fw-bold">Amarillo hasta día</label><input name="amarillo" type="number" value="{CONFIG['amarillo_max']}" class="form-control"></div>
    </div>
    <div class="alert alert-info small mt-3">
    <b>¿Mal alimentada?</b> Si metiste en B1-N1-C1 y era C2, usa el botón <b>↻ Mover</b> que aparece en cada lote.<br>
    <b>¿Ocupada?</b> Puedes alimentar otra referencia en la misma B1-N1-C1, se guardan juntas: ej 2e J259 + 10e J260.
    </div>
    <button class="btn btn-primary w-100 mt-2">Guardar y Actualizar Vista</button>
    <a href="/" class="btn btn-secondary w-100 mt-2">Volver sin guardar</a>
    </form>
    </div>
    """

@app.route("/mover/<int:lote_id>", methods=["GET","POST"])
def mover(lote_id):
    conn=get_conn(); cur=conn.cursor(); is_pg=os.environ.get("DATABASE_URL") is not None
    if request.method=="POST":
        b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
        codigo=f"B{b}-N{n}-C{c}"
        cur.execute("UPDATE lotes SET codigo=%s, bloque=%s, nivel=%s, calle=%s WHERE id=%s" if is_pg else "UPDATE lotes SET codigo=?, bloque=?, nivel=?, calle=? WHERE id=?",(codigo,b,n,c,lote_id))
        conn.commit(); cur.close(); conn.close(); return redirect(f"/?bloque={b}")
    q="SELECT codigo,producto,juliano,estibas FROM lotes WHERE id=%s" if is_pg else "SELECT codigo,producto,juliano,estibas FROM lotes WHERE id=?"
    cur.execute(q,(lote_id,)); r=cur.fetchone(); cur.close(); conn.close()
    if not r: return redirect("/")
    return f"""
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <div style="max-width:400px;margin:30px auto;" class="bg-white p-4 rounded shadow">
    <h5>↻ Mover / Corregir</h5>
    <p class="small">Lote: <b>{r[1]} {r[3]}e J{r[2]}</b> en {r[0]}<br>Selecciona la posición correcta:</p>
    <form method="post">
    <div class="row g-2">
    <div class="col-4"><label>Bloque</label><select name="bloque" class="form-select">{"".join([f'<option value={i}>B{i}</option>' for i in range(1,CONFIG['bloques']+1)])}</select></div>
    <div class="col-4"><label>Nivel</label><select name="nivel" class="form-select">{"".join([f'<option value={i}>N{i}</option>' for i in range(1,CONFIG['niveles']+1)])}</select></div>
    <div class="col-4"><label>Calle</label><select name="calle" class="form-select">{"".join([f'<option value={i}>C{i}</option>' for i in range(1,CONFIG['calles']+1)])}</select></div>
    </div>
    <button class="btn btn-warning w-100 mt-3 fw-bold">Corregir Posición</button>
    <a href="/" class="btn btn-secondary w-100 mt-2">Cancelar</a>
    </form>
    </div>
    """

HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estanteria</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>
body{background:#eef2f7;font-family:'Segoe UI',sans-serif}
.topbar{background:#1e4a7a;color:white;padding:12px 18px}
.card-pos{border:1px solid #ccc;border-radius:8px;background:#f8f9fa;min-height:90px;padding:6px;margin:3px;flex:1;font-size:11px;position:relative}
.card-pos.active{border:2px solid #0d6efd;background:white;box-shadow:0 0 8px #0d6efd40}
.lote{font-size:10px;margin:3px 0;padding:3px;background:white;border-radius:4px;border-left:4px solid {{s}};font-weight:600}
.btn-b{border-radius:8px;font-weight:700}
</style>
</head><body>
<div class="topbar d-flex align-items-center gap-3 flex-wrap">
<h5 class="m-0 fw-bold">Estanteria de Flujo</h5>
<div class="bg-white bg-opacity-25 rounded px-3 py-1"><b>{{total}}</b> est</div>
<div class="bg-white text-dark rounded px-3 py-1 small"><b>Hoy {{hoy_fecha.strftime('%d %b')}} = {{hoy_jul}} JUL</b></div>
<div class="d-flex gap-1">
<span class="badge bg-success">🟢 0-{{config.verde_max}}</span>
<span class="badge bg-warning text-dark">🟡 {{config.verde_max+1}}-{{config.amarillo_max}}</span>
<span class="badge bg-danger">🔴 {{config.amarillo_max+1}}+</span>
</div>
<div class="ms-auto d-flex gap-2">
<a href="/config" class="btn btn-sm btn-light">⚙️ Configurar (B{{config.bloques}} N{{config.niveles}} C{{config.calles}})</a>
</div>
</div>

<div class="container-fluid p-2">
{% if alerta %}<div class="alert alert-danger py-1 fw-bold">{{alerta}}</div>{% endif %}

<div class="bg-white rounded-3 p-2 shadow-sm d-flex gap-1 flex-wrap mb-2">
{% for b in range(1, config.bloques+1) %}
<a href="/?bloque={{b}}" class="btn btn-sm {{'btn-primary' if bloque==b else 'btn-outline-secondary'}} btn-b">B{{b}} ({{tot_bloque.get(b,0)}})</a>
{% endfor %}
<a href="/?bloque=0" class="btn btn-sm {{'btn-dark' if bloque==0 else 'btn-outline-secondary'}}">TODO ({{total}})</a>
</div>

{% for b in bloques_ver %}
<div class="bg-white rounded-3 shadow-sm p-2 mb-3">
<h6 class="fw-bold">BLOQUE {{b}} - {{tot_bloque.get(b,0)}} estibas | {{config.niveles}}N x {{config.calles}}C</h6>
{% for n in range(config.niveles,0,-1) %}
<div class="d-flex">
<div style="width:35px;font-weight:800;padding-top:10px">N{{n}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,config.calles+1) %}
{% set k='B' ~ b ~ '-N' ~ n ~ '-C' ~ c %}
{% set tot=totales.get(k,0) %}
<div class="card-pos">
<div class="fw-bold" style="color:#0d6efd;font-size:10px">B{{b}}-N{{n}}-C{{c}} - {{tot}} est</div>
{% for lote in grupos.get(k,[]) %}
<div class="lote" style="border-left-color:{{lote.sema.color}}">
{{lote.producto}} {{lote.estibas}}e J{{lote.juliano}} {{lote.sema.emoji}} {{lote.sema.txt}}
<div class="d-flex gap-1 mt-1">
<a href="/mover/{{lote.id}}" class="btn btn-warning py-0 px-1" style="font-size:8px">↻ Mover</a>
<a href="/eliminar/{{lote.id}}" class="btn btn-danger py-0 px-1" style="font-size:8px">x</a>
</div>
</div>
{% endfor %}
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="row g-2">
<div class="col-lg-7">
<div class="bg-white rounded-3 shadow-sm p-3">
<h6 class="fw-bold">Alimentar / Despachar - Permite varias referencias en misma calle</h6>
<form method="post" action="/movimiento" class="row g-2 mt-1" onsubmit="return validar(this)">
<div class="col-2"><label class="small fw-bold">BLOQUE</label><select name="bloque" id="b_sel" class="form-select form-select-sm"><option value="1">B1</option>{% for i in range(2,config.bloques+1) %}<option value="{{i}}">B{{i}}</option>{% endfor %}</select></div>
<div class="col-2"><label class="small fw-bold">NIVEL</label><select name="nivel" id="n_sel" class="form-select form-select-sm">{% for i in range(1,config.niveles+1) %}<option value="{{i}}">N{{i}}</option>{% endfor %}</select></div>
<div class="col-2"><label class="small fw-bold">CALLE</label><select name="calle" id="c_sel" class="form-select form-select-sm">{% for i in range(1,config.calles+1) %}<option value="{{i}}">C{{i}}</option>{% endfor %}</select></div>
<div class="col-6"><label class="small fw-bold">MATERIAL COMPLETO (otra referencia si está ocupada)</label><input name="producto" class="form-control form-control-sm fw-bold" value="12005778" required></div>
<div class="col-3"><label class="small fw-bold">JULIANO Hoy {{hoy_jul}}</label><input name="juliano" class="form-control form-control-sm fw-bold" value="{{hoy_jul}}" type="number" required></div>
<div class="col-3"><label class="small fw-bold">ESTIBAS</label><input name="cantidad" id="cant" class="form-control form-control-sm fw-bold" value="1" type="number" min="1"></div>
<div class="col-6 mt-2"><button name="accion" value="alimentar" class="btn btn-success w-100 fw-bold">+ ALIMENTAR (añade referencia si está ocupada)</button></div>
<div class="col-6 mt-2"><button name="accion" value="despachar" class="btn btn-danger w-100 fw-bold">- DESPACHAR</button></div>
</form>
</div>
</div>
<div class="col-lg-5">
<div class="bg-white rounded-3 shadow-sm p-3 small">
<b>¿Cómo funciona ahora?</b><br>
• Si B1-N1-C1 tiene 2e J259 y alimentas 10e J259 de otro material 12009999, se guardan los dos en la misma casilla.<br>
• Si te equivocaste de calle (pusiste C1 y era C2) dale a <b>↻ Mover</b> en el lote.<br>
• Si despachas más de lo que hay, te sale alerta y no resta.<br>
• Desde ⚙️ puedes cambiar bloques, niveles y calles sin perder datos.
</div>
</div>
</div>
</div>
<script>
const totales={{totales_js|safe}};
function validar(f){
 const act=document.activeElement.value;
 if(act!=='despachar') return true;
 const cod=`B${f.bloque.value}-N${f.nivel.value}-C${f.calle.value}`;
 const hay=totales[cod]||0; const pide=parseInt(f.cantidad.value);
 if(pide>hay){ alert(`⚠️ En ${cod} solo hay ${hay} estibas y quieres despachar ${pide}`); return false; }
 return true;
}
</script>
</body></html>
"""

@app.route("/")
def index():
    b_actual=int(request.args.get('bloque','1')); hoy_jul=hoy_juliano(); hoy_fecha=hoy_fecha_col(); alerta=request.args.get('alerta')
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT id,codigo,bloque,producto,juliano,estibas FROM lotes ORDER BY juliano ASC"); rows=cur.fetchall()
    except: rows=[]
    grupos={}; totales={}; tot_bloque={}; total=0
    for r in rows:
        try:
            id_=r[0]; codigo=r[1]; bloque=int(r[2]); producto=r[3]; juliano=int(r[4]); estibas=int(r[5])
            if estibas<=0: continue
            s=semaforo(juliano); obj={"id":id_,"producto":producto,"juliano":juliano,"estibas":estibas,"sema":s}
            grupos.setdefault(codigo, []).append(obj)
            totales[codigo]=totales.get(codigo,0)+estibas
            tot_bloque[bloque]=tot_bloque.get(bloque,0)+estibas
            total+=estibas
        except: continue
    cur.close(); conn.close()
    import json
    bloques_ver=list(range(1,CONFIG["bloques"]+1)) if b_actual==0 else [b_actual]
    return render_template_string(HTML, grupos=grupos, totales=totales, totales_js=json.dumps(totales), tot_bloque=tot_bloque, total=total, bloque=b_actual, bloques_ver=bloques_ver, hoy_jul=hoy_jul, hoy_fecha=hoy_fecha, config=CONFIG, alerta=alerta)

@app.route("/movimiento", methods=["POST"])
def mov():
    try:
        b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
        codigo=f"B{b}-N{n}-C{c}"; producto=request.form['producto'].strip(); cant=int(request.form['cantidad']); jul=int(request.form['juliano']); accion=request.form.get('accion','alimentar')
        conn=get_conn(); cur=conn.cursor(); is_pg=os.environ.get("DATABASE_URL") is not None
        if accion=='despachar':
            cur.execute("SELECT SUM(estibas) FROM lotes WHERE codigo=%s" if is_pg else "SELECT SUM(estibas) FROM lotes WHERE codigo=?",(codigo,))
            hay=int(cur.fetchone()[0] or 0)
            if cant>hay:
                cur.close(); conn.close(); return redirect(f"/?bloque={b}&alerta=En {codigo} solo hay {hay} estibas y tratas de despachar {cant}")
        if accion=='alimentar':
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s AND producto=%s AND juliano=%s" if is_pg else "SELECT id, estibas FROM lotes WHERE codigo=? AND producto=? AND juliano=?",(codigo,producto,jul)); row=cur.fetchone()
            if row: cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if is_pg else "UPDATE lotes SET estibas=? WHERE id=?",(int(row[1])+cant,row[0]))
            else:
                import datetime as dt; f=juliano_a_fecha(jul); f_str=f.isoformat() if f else str(dt.date.today())
                cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)" if is_pg else "INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (?,?,?,?,?,?,?,?)",(codigo,b,n,c,producto,jul,cant,f_str))
        else:
            cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s ORDER BY juliano ASC" if is_pg else "SELECT id, estibas FROM lotes WHERE codigo=? ORDER BY juliano ASC",(codigo,)); por=cant
            for r in cur.fetchall():
                if por<=0: break
                id_,est=r[0],int(r[1])
                if est<=por: por-=est; cur.execute("DELETE FROM lotes WHERE id=%s" if is_pg else "DELETE FROM lotes WHERE id=?",(id_,))
                else: cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if is_pg else "UPDATE lotes SET estibas=? WHERE id=?",(est-por,id_)); por=0
        conn.commit(); cur.close(); conn.close()
    except Exception as e: print(e)
    return redirect(f"/?bloque={b}")

@app.route("/eliminar/<int:lote_id>")
def eliminar(lote_id):
    try: conn=get_conn(); cur=conn.cursor(); is_pg=os.environ.get("DATABASE_URL") is not None; cur.execute("DELETE FROM lotes WHERE id=%s" if is_pg else "DELETE FROM lotes WHERE id=?",(lote_id,)); conn.commit(); cur.close(); conn.close()
    except: pass
    return redirect("/")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
