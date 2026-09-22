from flask import Flask, request, redirect, render_template_string, g
import sqlite3, os
from datetime import datetime

app = Flask(__name__)
DB = "estanteria_4bloques_final.db"
NIVELES, CALLES, BLOQUES = 6, 10, 4
COLORES = {1:{"bg":"#0d6efd","light":"#dbe8ff","name":"AZUL"},2:{"bg":"#198754","light":"#d1e7dd","name":"VERDE"},3:{"bg":"#fd7e14","light":"#ffe5cc","name":"NARANJA"},4:{"bg":"#6f42c1","light":"#e2d9f3","name":"MORADO"}}

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DB); db.row_factory = sqlite3.Row
    return db

def init_db():
    with app.app_context():
        db = get_db()
        db.execute("""CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0)""")
        db.execute("""CREATE TABLE IF NOT EXISTS movimientos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, bloque INT, codigo TEXT, producto TEXT, tipo TEXT, cantidad INT, responsable TEXT)""")
        db.execute("""CREATE TABLE IF NOT EXISTS config_calles (bloque INT, calle INT, producto_asignado TEXT, PRIMARY KEY(bloque,calle))""")
        for b in range(1,BLOQUES+1):
            for n in range(1,NIVELES+1):
                for c in range(1,CALLES+1):
                    db.execute("INSERT OR IGNORE INTO posiciones VALUES (?,?,?,?, '',0)", (f"B{b}-N{n}-C{c}",b,n,c))
            for c in range(1,CALLES+1):
                db.execute("INSERT OR IGNORE INTO config_calles VALUES (?,?, '')", (b,c))
        db.commit()

@app.teardown_appcontext
def close_connection(e):
    db = getattr(g, '_database', None)
    if db: db.close()

# PLANTILLA PRINCIPAL
T_MAIN = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f2f4f8}.pos{border:2px solid; border-radius:6px; padding:3px; margin:2px; min-height:65px; background:#fff; font-size:10px; width:9.1%; text-align:center}.lleno{font-weight:bold}.vacio{background:#e9ecef; opacity:0.7}</style>
</head><body class="p-2"><div class="container-fluid">
<div class="d-flex justify-content-between">
<h5>📦 4 BLOQUES - {{total}} estibas</h5>
<div>
<a href="/configuracion" class="btn btn-dark btn-sm">⚙️ CONFIGURAR PRODUCTOS POR CALLE</a>
<a href="/tarjetas" target="_blank" class="btn btn-warning btn-sm">🖨️ IMPRIMIR</a>
</div></div>

<ul class="nav nav-pills my-2">
{% for b in range(1,BLOQUES+1) %}<li class="nav-item me-1"><a class="nav-link {{'active' if bloque==b else ''}}" style="{{'background:'+COLORES[b].bg+';color:white' if bloque==b else 'border:1px solid '+COLORES[b].bg+';color:'+COLORES[b].bg}}" href="/?bloque={{b}}">B{{b}} {{COLORES[b].name}} ({{tot[b]}})</a></li>{% endfor %}
<li class="nav-item"><a class="nav-link {{'active' if bloque==0 else ''}}" href="/?bloque=0">TODO</a></li></ul>

<div class="row"><div class="col-lg-9">
{% for b in bloques_ver %}
<div class="p-1 text-white small rounded-top" style="background:{{COLORES[b].bg}}">BLOQUE {{b}} - {{COLORES[b].name}} | {% for c in range(1,CALLES+1) %}C{{c}}:{{config[b][c] or 'LIBRE'}} | {% endfor %}</div>
<div class="card p-1 mb-2" style="border-top:4px solid {{COLORES[b].bg}}">
{% for n in range(NIVELES,0,-1) %}<div class="d-flex"><div style="width:50px" class="small fw-bold">N{{n}}</div>
{% for c in range(1,CALLES+1) %}{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set p=pos[k] %}
<div class="pos {{'lleno' if p.estibas>0 else 'vacio'}}" style="border-color:{{COLORES[b].bg}}; {{'background:'+COLORES[b].light if p.estibas>0 else ''}}"><b>N{{n}}-C{{c}}</b><br>{{p.producto[:7]}}<br>{{p.estibas}} est.</div>
{% endfor %}</div>{% endfor %}</div>{% endfor %}</div>

<div class="col-lg-3"><div class="card p-2 shadow-sm">
<h6>Registrar</h6>
<form method="post" action="/movimiento">
<select name="bloque" id="bloque_sel" class="form-select form-select-sm" required onchange="actualizarProducto()">
{% for b in range(1,BLOQUES+1) %}<option value="{{b}}" {{'selected' if b==bloque else ''}}>BLOQUE {{b}}</option>{% endfor %}
</select>
<div class="d-flex gap-1 mt-1">
<select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option>N{{n}}</option>{% endfor %}</select>
<select name="calle" id="calle_sel" class="form-select form-select-sm" onchange="actualizarProducto()">{% for c in range(1,CALLES+1) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select>
</div>
<input name="producto" id="producto_input" class="form-control form-control-sm mt-2" placeholder="Producto" required>
<select name="tipo" class="form-select form-select-sm mt-1"><option value="ALIMENTACION">+ ALIMENTACION</option><option value="DESPACHO">- DESPACHO</option></select>
<input type="number" name="cantidad" class="form-control form-control-sm mt-1" value="1" min="1">
<input name="responsable" class="form-control form-control-sm mt-1" value="John">
<button class="btn btn-primary btn-sm w-100 mt-2">Guardar</button>
</form></div></div></div>

<script>
var configData = {{config_json|safe}};
function actualizarProducto(){
  let b = document.getElementById('bloque_sel').value;
  let c = document.getElementById('calle_sel').value;
  let prod = configData[b][c];
  if(prod){ document.getElementById('producto_input').value = prod; }
}
actualizarProducto();
</script>
</div></body></html>
"""

# PLANTILLA CONFIGURACION
T_CONFIG = """
<!doctype html><html><head><meta charset="utf-8"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head>
<body class="p-3"><div class="container">
<a href="/" class="btn btn-secondary btn-sm mb-3">⬅ Volver al mapa</a>
<h4>⚙️ CONFIGURACIÓN - Qué producto va en cada calle</h4>
<p class="small text-muted">Define qué producto debe ir en cada calle. Después en el mapa se pone automático. Si dejas LIBRE, puedes poner cualquier producto.</p>

<form method="post">
{% for b in range(1,BLOQUES+1) %}
<div class="card mb-3" style="border-left:5px solid {{COLORES[b].bg}}">
<div class="card-header text-white" style="background:{{COLORES[b].bg}}">BLOQUE {{b}} - {{COLORES[b].name}}</div>
<div class="card-body"><div class="row">
{% for c in range(1,CALLES+1) %}
<div class="col-md-2 col-6 mb-2">
<label class="small fw-bold">Calle {{c}}</label>
<input name="prod_B{{b}}_C{{c}}" value="{{config[b][c]}}" list="listaProd" class="form-control form-control-sm" placeholder="LIBRE">
</div>{% endfor %}
</div></div></div>{% endfor %}

<datalist id="listaProd"><option value="Kimi PH"><option value="Familia"><option value="Scott"><option value="Elite"><option value="Kleenex"><option value="LIBRE"></datalist>

<button class="btn btn-success w-100">💾 GUARDAR CONFIGURACIÓN</button>
</form>

<hr><h6>Configuración actual:</h6>
<table class="table table-sm table-bordered small"><tr><th></th>{% for c in range(1,CALLES+1) %}<th>C{{c}}</th>{% endfor %}</tr>
{% for b in range(1,BLOQUES+1) %}<tr><th style="background:{{COLORES[b].light}}">BLOQUE {{b}}</th>{% for c in range(1,CALLES+1) %}<td>{{config[b][c] or '-LIBRE-'}}</td>{% endfor %}</tr>{% endfor %}
</table>
</div></body></html>
"""

@app.route("/")
def index():
    b_actual = int(request.args.get('bloque','1'))
    db = get_db()
    pos = {r['codigo']: r for r in db.execute("SELECT * FROM posiciones")}
    conf_rows = db.execute("SELECT * FROM config_calles").fetchall()
    config = {b:{c:'' for c in range(1,CALLES+1)} for b in range(1,BLOQUES+1)}
    for r in conf_rows: config[r['bloque']][r['calle']] = r['producto_asignado']
    import json
    config_json = json.dumps(config)
    tot = {b:0 for b in range(1,BLOQUES+1)}; total=0
    for p in pos.values(): tot[p['bloque']]+=p['estibas']; total+=p['estibas']
    ver = list(range(1,BLOQUES+1)) if b_actual==0 else [b_actual]
    return render_template_string(T_MAIN, pos=pos, config=config, config_json=config_json, tot=tot, total=total, bloque=b_actual, bloques_ver=ver, NIVELES=NIVELES, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES)

@app.route("/configuracion", methods=["GET","POST"])
def configuracion():
    db = get_db()
    if request.method=="POST":
        for b in range(1,BLOQUES+1):
            for c in range(1,CALLES+1):
                prod = request.form.get(f"prod_B{b}_C{c}", "").strip()
                db.execute("UPDATE config_calles SET producto_asignado=? WHERE bloque=? AND calle=?", (prod,b,c))
        db.commit()
        return redirect("/")
    conf_rows = db.execute("SELECT * FROM config_calles").fetchall()
    config = {b:{c:'' for c in range(1,CALLES+1)} for b in range(1,BLOQUES+1)}
    for r in conf_rows: config[r['bloque']][r['calle']] = r['producto_asignado']
    return render_template_string(T_CONFIG, config=config, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES)

@app.route("/movimiento", methods=["POST"])
def movimiento():
    db=get_db()
    b=int(request.form['bloque']); n=int(request.form['nivel'].replace('N','')); c=int(request.form['calle'].replace('C',''))
    codigo=f"B{b}-N{n}-C{c}"; prod=request.form['producto']; tipo=request.form['tipo']; cant=int(request.form['cantidad']); resp=request.form['responsable']
    actual=db.execute("SELECT estibas FROM posiciones WHERE codigo=?", (codigo,)).fetchone()[0]
    if tipo=="DESPACHO" and cant>actual: return f"<h3>Error: solo hay {actual} en {codigo}</h3><a href='/'>Volver</a>"
    nuevo=actual+cant if tipo=="ALIMENTACION" else actual-cant
    db.execute("UPDATE posiciones SET estibas=?, producto=? WHERE codigo=?", (nuevo,prod,codigo))
    db.execute("INSERT INTO movimientos VALUES (NULL,?,?,?,?,?,?,?)", (datetime.now().strftime("%d/%m %H:%M"),b,codigo,prod,tipo,cant,resp))
    db.commit()
    return redirect(f"/?bloque={b}")

@app.route("/tarjetas")
def tarjetas():
    db=get_db()
    pos={r['codigo']: r for r in db.execute("SELECT * FROM posiciones")}
    tot={b:0 for b in range(1,BLOQUES+1)}
    for p in pos.values(): tot[p['bloque']]+=p['estibas']
    html="<body><a href='/'>Volver</a><button onclick='window.print()'>IMPRIMIR</button><br>"
    for b in range(1,BLOQUES+1):
        html+=f"<div style='border:3px solid {COLORES[b]['bg']}; padding:10px; margin:10px; display:inline-block; width:45%'><h1 style='color:{COLORES[b]['bg']}'>BLOQUE {b} {COLORES[b]['name']}</h1>Total:{tot[b]} estibas</div>"
    return html

if __name__=="__main__":
    if not os.path.exists(DB): 
        init_db()
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=False, host='0.0.0.0', port=port)