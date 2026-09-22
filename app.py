import os, json
from flask import Flask, request, redirect, render_template_string
from datetime import datetime

app = Flask(__name__)
NIVELES, CALLES, BLOQUES = 6, 10, 4
COLORES = {1:{"bg":"#0d6efd","light":"#dbe8ff","name":"AZUL"},2:{"bg":"#198754","light":"#d1e7dd","name":"VERDE"},3:{"bg":"#fd7e14","light":"#ffe5cc","name":"NARANJA"},4:{"bg":"#6f42c1","light":"#e2d9f3","name":"MORADO"}}

DATABASE_URL = os.environ.get("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

def get_conn():
    if DATABASE_URL:
        import psycopg2
        return psycopg2.connect(DATABASE_URL, sslmode='require')
    else:
        import sqlite3
        conn = sqlite3.connect("/tmp/estanteria.db")
        conn.row_factory = sqlite3.Row
        return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    if DATABASE_URL:
        cur.execute("DROP TABLE IF EXISTS movimientos")
        cur.execute("DROP TABLE IF EXISTS config_calles")
        cur.execute("DROP TABLE IF EXISTS posiciones")
        cur.execute("CREATE TABLE posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0)")
        cur.execute("CREATE TABLE config_calles (bloque INT, calle INT, producto_asignado TEXT, PRIMARY KEY(bloque,calle))")
        cur.execute("CREATE TABLE movimientos (id SERIAL PRIMARY KEY, fecha TEXT, bloque INT, codigo TEXT, producto TEXT, tipo TEXT, cantidad INT, responsable TEXT)")
        conn.commit()
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0] == 0:
            for b in range(1, BLOQUES+1):
                for n in range(1, NIVELES+1):
                    for c in range(1, CALLES+1):
                        cur.execute("INSERT INTO posiciones VALUES (%s,%s,%s,%s,'',0)", (f"B{b}-N{n}-C{c}",b,n,c))
                for c in range(1, CALLES+1):
                    cur.execute("INSERT INTO config_calles VALUES (%s,%s,'')", (b,c))
    else:
        cur.execute("CREATE TABLE IF NOT EXISTS posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT, producto TEXT, estibas INT DEFAULT 0)")
        cur.execute("CREATE TABLE IF NOT EXISTS config_calles (bloque INT, calle INT, producto_asignado TEXT, PRIMARY KEY(bloque,calle))")
        cur.execute("CREATE TABLE IF NOT EXISTS movimientos (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT, bloque INT, codigo TEXT, producto TEXT, tipo TEXT, cantidad INT, responsable TEXT)")
        cur.execute("SELECT COUNT(*) FROM posiciones")
        if cur.fetchone()[0] == 0:
            for b in range(1, BLOQUES+1):
                for n in range(1, NIVELES+1):
                    for c in range(1, CALLES+1):
                        cur.execute("INSERT OR IGNORE INTO posiciones VALUES (?,?,?,?, '',0)", (f"B{b}-N{n}-C{c}",b,n,c))
                for c in range(1, CALLES+1):
                    cur.execute("INSERT OR IGNORE INTO config_calles VALUES (?,?, '')", (b,c))
    conn.commit()
    cur.close()
    conn.close()

init_db()

# --- PLANTILLAS ---
T_MAIN = """<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>body{background:#f2f4f8}.pos{border:2px solid; border-radius:6px; padding:3px; margin:2px; min-height:65px; background:#fff; font-size:10px; width:9.1%; text-align:center}</style>
</head><body class="p-2"><div class="container-fluid">
<h5>📦 4 BLOQUES - {{total}} estibas - PERMANENTE</h5>
<a href="/configuracion" class="btn btn-dark btn-sm">⚙️ CONFIG</a>
<ul class="nav nav-pills my-2">{% for b in range(1,BLOQUES+1) %}<li class="nav-item me-1"><a class="nav-link {{'active' if bloque==b else ''}}" style="background:{{COLORES[b].bg}};color:white" href="/?bloque={{b}}">B{{b}} ({{tot[b]}})</a></li>{% endfor %}</ul>
<div class="row"><div class="col-lg-9">{% for b in bloques_ver %}<div class="p-1 text-white small" style="background:{{COLORES[b].bg}}">BLOQUE {{b}} {{COLORES[b].name}}</div><div class="card p-1 mb-2">{% for n in range(NIVELES,0,-1) %}<div class="d-flex"><div style="width:40px">N{{n}}</div>{% for c in range(1,CALLES+1) %}{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set p=pos[k] %}<div class="pos" style="border-color:{{COLORES[b].bg}}">{{p.producto[:6]}}<br>{{p.estibas}}</div>{% endfor %}</div>{% endfor %}</div>{% endfor %}</div>
<div class="col-lg-3"><form method="post" action="/movimiento" class="card p-2"><select name="bloque" class="form-select form-select-sm">{% for b in range(1,BLOQUES+1) %}<option value="{{b}}" {{'selected' if b==bloque else ''}}>B{{b}}</option>{% endfor %}</select><div class="d-flex gap-1 mt-1"><select name="nivel" class="form-select form-select-sm">{% for n in range(1,NIVELES+1) %}<option>N{{n}}</option>{% endfor %}</select><select name="calle" class="form-select form-select-sm">{% for c in range(1,CALLES+1) %}<option>C{{c}}</option>{% endfor %}</select></div><input name="producto" class="form-control form-control-sm mt-1" placeholder="Producto" required><select name="tipo" class="form-select form-select-sm mt-1"><option value="ALIMENTACION">+ ALIM</option><option value="DESPACHO">- DESP</option></select><input type="number" name="cantidad" class="form-control form-control-sm mt-1" value="1"><input name="responsable" class="form-control form-control-sm mt-1" value="John"><button class="btn btn-primary btn-sm w-100 mt-1">Guardar</button></form></div></div></div></body></html>
"""
T_CONFIG="""<!doctype html><html><head><meta charset="utf-8"><link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet"></head><body class="p-3"><div class="container"><a href="/" class="btn btn-secondary btn-sm">Volver</a><h4>CONFIG</h4><form method="post">{% for b in range(1,BLOQUES+1) %}<div class="card mb-2"><div class="card-header text-white" style="background:{{COLORES[b].bg}}">BLOQUE {{b}}</div><div class="card-body row">{% for c in range(1,CALLES+1) %}<div class="col-2"><label>C{{c}}</label><input name="prod_B{{b}}_C{{c}}" value="{{config[b][c]}}" class="form-control form-control-sm"></div>{% endfor %}</div></div>{% endfor %}<button class="btn btn-success w-100">GUARDAR</button></form></div></body></html>"""

@app.route("/")
def index():
    b_actual=int(request.args.get('bloque','1'))
    conn=get_conn(); cur=conn.cursor()
    cur.execute("SELECT * FROM posiciones")
    rows=cur.fetchall()
    pos={}
    for r in rows:
        if DATABASE_URL: pos[r[0]]={'codigo':r[0],'bloque':r[1],'nivel':r[2],'calle':r[3],'producto':r[4],'estibas':r[5]}
        else: pos[r['codigo']]=dict(r)
    cur.execute("SELECT * FROM config_calles")
    rows=cur.fetchall()
    config={b:{c:'' for c in range(1,CALLES+1)} for b in range(1,BLOQUES+1)}
    for r in rows:
        if DATABASE_URL: config[r[0]][r[1]]=r[2]
        else: config[r['bloque']][r['calle']]=r['producto_asignado']
    tot={b:0 for b in range(1,BLOQUES+1)}; total=0
    for p in pos.values(): tot[p['bloque']]+=p['estibas']; total+=p['estibas']
    ver=list(range(1,BLOQUES+1)) if b_actual==0 else [b_actual]
    cur.close(); conn.close()
    import json
    return render_template_string(T_MAIN, pos=pos, config=config, tot=tot, total=total, bloque=b_actual, bloques_ver=ver, NIVELES=NIVELES, CALLES=CALLES, BLOQUES=BLOQUES, COLORES=COLORES)

@app.route("/configuracion", methods=["GET","POST"])
def conf():
    conn=get_conn(); cur=conn.cursor()
    if request.method=="POST":
        for b in range(1,BLOQUES+1):
            for c in range(1,CALLES+1):
                prod=request.form.get(f"prod_B{b}_C{c}","").strip()
                if DATABASE_URL: cur.execute("INSERT INTO config_calles VALUES (%s,%s,%s) ON CONFLICT (bloque,calle) DO UPDATE SET producto_asignado=%s",(b,c,prod,prod))
                else: cur.execute("UPDATE config_calles SET producto_asignado=? WHERE bloque=? AND calle=?",(prod,b,c))
        conn.commit(); cur.close(); conn.close()
        return redirect("/")
    cur.execute("SELECT * FROM config_calles")
    rows=cur.fetchall()
    config={b:{c:'' for c in range(1,CALLES+1)} for b in range(1,BLOQUES+1)}
    for r in rows:
        if DATABASE_URL: config[r[0]][r[1]]=r[2]
        else: config[r['bloque']][r['calle']]=r['producto_asignado']
    cur.close(); conn.close()
    return render_template_string(T_CONFIG, config=config, BLOQUES=BLOQUES, CALLES=CALLES, COLORES=COLORES)

@app.route("/movimiento", methods=["POST"])
def mov():
    conn=get_conn(); cur=conn.cursor()
    b=int(request.form['bloque'].replace('B','').replace('N','').replace('C','')); n=int(str(request.form['nivel']).replace('N','')); c=int(str(request.form['calle']).replace('C',''))
    # fix si vienen con N y C
    try: b=int(request.form['bloque'])
    except: pass
    try: n=int(request.form['nivel'])
    except: n=int(request.form['nivel'].replace('N',''))
    try: c=int(request.form['calle'])
    except: c=int(request.form['calle'].replace('C',''))
    codigo=f"B{b}-N{n}-C{c}"; prod=request.form['producto']; tipo=request.form['tipo']; cant=int(request.form['cantidad'])
    if DATABASE_URL: cur.execute("SELECT estibas FROM posiciones WHERE codigo=%s",(codigo,))
    else: cur.execute("SELECT estibas FROM posiciones WHERE codigo=?",(codigo,))
    actual=cur.fetchone()[0]
    if tipo=="DESPACHO" and cant>actual:
        cur.close(); conn.close()
        return f"Error solo {actual} en {codigo} <a href='/'>Volver</a>"
    nuevo=actual+cant if tipo=="ALIMENTACION" else actual-cant
    if DATABASE_URL:
        cur.execute("UPDATE posiciones SET estibas=%s, producto=%s WHERE codigo=%s",(nuevo,prod,codigo))
        cur.execute("INSERT INTO movimientos (fecha,bloque,codigo,producto,tipo,cantidad,responsable) VALUES (%s,%s,%s,%s,%s,%s,%s)",(datetime.now().strftime("%d/%m %H:%M"),b,codigo,prod,tipo,cant,"John"))
    else:
        cur.execute("UPDATE posiciones SET estibas=?, producto=? WHERE codigo=?",(nuevo,prod,codigo))
    conn.commit(); cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
