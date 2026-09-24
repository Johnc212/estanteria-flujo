import os
import sqlite3
from flask import Flask, request, redirect, render_template_string
from datetime import date, datetime, timedelta

app = Flask(__name__)

# Config
BLOQUES, NIVELES, CALLES = 4, 6, 10

def get_conn():
    db_url = os.environ.get("DATABASE_URL", "")
    if db_url:
        try:
            if db_url.startswith("postgres://"):
                db_url = db_url.replace("postgres://", "postgresql://", 1)
            import psycopg2
            return psycopg2.connect(db_url, sslmode='require')
        except Exception as e:
            print(f"Postgres fallo, usando SQLite: {e}")
    # Fallback SQLite - NUNCA falla
    conn = sqlite3.connect("/tmp/estanteria.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        if os.environ.get("DATABASE_URL"):
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lotes (
                    id SERIAL PRIMARY KEY,
                    codigo TEXT, bloque INT, nivel INT, calle INT,
                    producto TEXT, juliano INT, estibas INT, fecha_ing DATE
                )
            """)
        else:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS lotes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    codigo TEXT, bloque INT, nivel INT, calle INT,
                    producto TEXT, juliano INT, estibas INT, fecha_ing TEXT
                )
            """)
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"init_db error: {e}")

def hoy_juliano():
    # Hora Colombia UTC-5 para cambio a medianoche Cali
    now_col = datetime.utcnow() - timedelta(hours=5)
    return now_col.timetuple().tm_yday

def hoy_fecha_col():
    return (datetime.utcnow() - timedelta(hours=5)).date()

def juliano_a_fecha(ddd):
    try:
        ddd = int(str(ddd)[-3:])
        hoy = hoy_fecha_col()
        base = date(hoy.year-1,1,1) if ddd > hoy.timetuple().tm_yday else date(hoy.year,1,1)
        return base + timedelta(days=ddd-1)
    except:
        return None

def semaforo(ddd):
    f = juliano_a_fecha(ddd)
    if not f:
        return {"color":"#6c757d","emoji":"⚪","dias":999,"txt":"-"}
    dias = (hoy_fecha_col() - f).days
    if dias < 0: dias = 0
    if dias <= 3: return {"color":"#198754","emoji":"🟢","dias":dias,"txt":f"{dias}d"}
    if dias <= 8: return {"color":"#ffc107","emoji":"🟡","dias":dias,"txt":f"{dias}d"}
    return {"color":"#dc3545","emoji":"🔴","dias":dias,"txt":f"{dias}d"}

# Intenta crear tabla pero no tumba la app si falla
init_db()

@app.route("/reset_db")
def reset_db():
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute("DROP TABLE IF EXISTS lotes")
        conn.commit()
        cur.close()
        conn.close()
    except: pass
    init_db()
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
<div class="d-flex align-items-center gap-2"><h4 class="m-0 fw-bold">Estanteria de<br>Flujo</h4></div>
<div class="bg-white bg-opacity-25 rounded px-3 py-1"><b>{{total}}</b> estibas</div>
<div class="bg-white text-dark rounded px-3 py-1"><b>Hoy {{hoy_fecha.strftime('%d %b')}} = {{hoy_jul}} JULIANO</b><br><small>Cambia auto 00:00 Cali</small></div>
<div class="ms-3 d-flex gap-2">
<span class="badge bg-success fs-6">🟢 0-3d</span>
<span class="badge bg-warning text-dark fs-6">🟡 4-8d</span>
<span class="badge bg-danger fs-6">🔴 9+d</span>
</div>
</div>

<div class="container-fluid p-3">
<div class="bg-white rounded-3 p-3 shadow-sm d-flex gap-2 flex-wrap align-items-center mb-3">
<a href="/?bloque=1" class="btn {{'btn-primary' if bloque==1 else 'btn-outline-secondary'}} btn-b">B1 ({{tot_bloque[1]}})</a>
<a href="/?bloque=2" class="btn {{'btn-success' if bloque==2 else 'btn-outline-secondary'}} btn-b">B2 ({{tot_bloque[2]}})</a>
<a href="/?bloque=3" class="btn {{'btn-warning' if bloque==3 else 'btn-outline-secondary'}} btn-b">B3 ({{tot_bloque[3]}})</a>
<a href="/?bloque=4" class="btn {{'btn-secondary' if bloque==4 else 'btn-outline-secondary'}} btn-b">B4 ({{tot_bloque[4]}})</a>
<a href="/?bloque=0" class="btn {{'btn-dark' if bloque==0 else 'btn-outline-secondary'}} btn-b">TODO ({{total}})</a>
<div class="ms-2 d-flex gap-2 align-items-center">
<label class="small fw-bold">BLOQUE:</label><select class="form-select form-select-sm" style="width:65px"><option>B1</option></select>
<label class="small fw-bold">NIVEL:</label><select class="form-select form-select-sm" style="width:65px"><option>N1</option></select>
<label class="small fw-bold">CALLE:</label><select class="form-select form-select-sm" style="width:65px"><option>C1</option></select>
</div>
<a href="/reset_db" class="btn btn-sm btn-danger ms-auto">Reparar DB</a>
</div>

{% for b in bloques_ver %}
<div class="bg-white rounded-3 shadow-sm p-3 mb-3">
<div class="d-flex justify-content-between mb-2"><h5 class="fw-bold m-0">BLOQUE {{b}}</h5><small>Mostrando 6x10 = 60 ubicaciones</small></div>
{% for n in range(6,0,-1) %}
<div class="d-flex">
<div style="width:40px; font-weight:800; padding-top:12px">N{{n}}</div>
<div class="d-flex flex-grow-1">
{% for c in range(1,11) %}
{% set k = 'B' ~ b ~ '-N' ~ n ~ '-C' ~ c %}
{% set tot = totales.get(k,0) %}
{% set es_activo = (n==1 and c==1 and b==bloque) %}
<div class="card-pos {{'active' if es_activo else ''}}">
<div class="fw-bold" style="color:#0d6efd">B{{b}}-N{{n}}-C{{c}} - {{tot}} est</div>
{% for lote in grupos.get(k,[]) %}
<div class="lote"><span style="color:{{lote.sema.color}}">●</span> {{lote.producto}} {{lote.estibas}}e J{{lote.juliano}} {{lote.sema.emoji}} {{lote.sema.txt}}</div>
{% endfor %}
</div>
{% endfor %}
</div>
</div>
{% endfor %}
</div>
{% endfor %}

<div class="row g-3">
<div class="col-lg-7">
<div class="bg-white rounded-3 shadow-sm p-3">
<div class="d-flex justify-content-between"><h6 class="fw-bold">Alimentar / Despachar</h6><span class="badge bg-light text-dark border">Hoy {{hoy_jul}} = {{hoy_fecha.strftime('%d %b')}}</span></div>
<form method="post" action="/movimiento" class="row g-2 mt-2">
<div class="col-2"><label class="small fw-bold">BLOQUE</label><select name="bloque" class="form-select form-select-sm fw-bold"><option value="1">B1</option><option value="2">B2</option><option value="3">B3</option><option value="4">B4</option></select></div>
<div class="col-2"><label class="small fw-bold">NIVEL</label><select name="nivel" class="form-select form-select-sm fw-bold"><option value="1">N1</option><option value="2">N2</option><option value="3">N3</option><option value="4">N4</option><option value="5">N5</option><option value="6">N6</option></select></div>
<div class="col-2"><label class="small fw-bold">CALLE</label><select name="calle" class="form-select form-select-sm fw-bold"><option value="1">C1</option><option value="2">C2</option><option value="3">C3</option><option value="4">C4</option><option value="5">C5</option><option value="6">C6</option><option value="7">C7</option><option value="8">C8</option><option value="9">C9</option><option value="10">C10</option></select></div>
<div class="col-6"><label class="small fw-bold">MATERIAL COMPLETO</label><input name="producto" class="form-control fw-bold" value="12005778" required></div>
<div class="col-3"><label class="small fw-bold">JULIANO Hoy {{hoy_jul}}</label><input name="juliano" class="form-control fw-bold" value="{{hoy_jul}}" type="number" required></div>
<div class="col-3"><label class="small fw-bold">ESTIBAS</label><input name="cantidad" class="form-control fw-bold" value="1" type="number" min="1" required></div>
<div class="col-6 mt-3"><button name="accion" value="alimentar" class="btn btn-success w-100 fw-bold py-2">+ ALIMENTAR</button></div>
<div class="col-6 mt-3"><button name="accion" value="despachar" class="btn btn-danger w-100 fw-bold py-2">- DESPACHAR</button></div>
</form>
</div>
</div>
<div class="col-lg-5">
<div class="bg-white rounded-3 shadow-sm p-3">
<h6 class="fw-bold">Resumen</h6>
<table class="table table-sm mt-2"><tr><td>Total Estibas:</td><td class="fw-bold">{{total}}</td></tr><tr><td>Lotes activos:</td><td class="fw-bold">{{lotes_count}}</td></tr><tr><td>Ultimo:</td><td class="fw-bold text-success">J{{hoy_jul}} (Hoy)</td></tr></table>
</div>
</div>
</div>

</div>
</body></html>
"""

@app.route("/")
def index():
    try:
        b_actual = int(request.args.get('bloque','1'))
        hoy_jul = hoy_juliano()
        hoy_fecha = hoy_fecha_col()
        conn = get_conn()
        cur = conn.cursor()
        try:
            cur.execute("SELECT codigo,bloque,producto,juliano,estibas FROM lotes ORDER BY juliano ASC")
            rows = cur.fetchall()
        except:
            rows = []

        grupos = {}; totales = {}; tot_bloque = {1:0,2:0,3:0,4:0}; total = 0
        for r in rows:
            try:
                codigo = r[0]; bloque = int(r[1]); producto = r[2]; juliano = int(r[3]); estibas = int(r[4])
                if estibas <= 0: continue
                s = semaforo(juliano)
                obj = {"producto":producto,"juliano":juliano,"estibas":estibas,"sema":s}
                if codigo not in grupos: grupos[codigo] = []
                grupos[codigo].append(obj)
                totales[codigo] = totales.get(codigo,0) + estibas
                tot_bloque[bloque] = tot_bloque.get(bloque,0) + estibas
                total += estibas
            except: continue
        cur.close()
        conn.close()
        bloques_ver = [1,2,3,4] if b_actual==0 else [b_actual]
        return render_template_string(HTML, grupos=grupos, totales=totales, tot_bloque=tot_bloque, total=total, bloque=b_actual, bloques_ver=bloques_ver, hoy_jul=hoy_jul, hoy_fecha=hoy_fecha, lotes_count=len(rows))
    except Exception as e:
        return f"<h3>Error temporal: {e}</h3><a href='/reset_db'>Reparar DB</a>", 500

@app.route("/movimiento", methods=["POST"])
def mov():
    try:
        b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
        codigo=f"B{b}-N{n}-C{c}"; producto=request.form['producto'].strip()
        cant=int(request.form['cantidad']); jul=int(request.form['juliano'])
        accion=request.form.get('accion','alimentar')

        conn=get_conn(); cur=conn.cursor()
        is_postgres = os.environ.get("DATABASE_URL") is not None

        if accion=='alimentar':
            q = "SELECT id, estibas FROM lotes WHERE codigo=%s AND producto=%s AND juliano=%s" if is_postgres else "SELECT id, estibas FROM lotes WHERE codigo=? AND producto=? AND juliano=?"
            cur.execute(q, (codigo,producto,jul))
            row=cur.fetchone()
            if row:
                new_est = int(row[1]) + cant
                q2 = "UPDATE lotes SET estibas=%s WHERE id=%s" if is_postgres else "UPDATE lotes SET estibas=? WHERE id=?"
                cur.execute(q2, (new_est, row[0]))
            else:
                f = juliano_a_fecha(jul)
                f_str = f.isoformat() if f else str(date.today())
                q3 = "INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)" if is_postgres else "INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (?,?,?,?,?,?,?,?)"
                cur.execute(q3, (codigo,b,n,c,producto,jul,cant,f_str))
        else: # DESPACHAR FIFO
            q = "SELECT id, estibas FROM lotes WHERE codigo=%s ORDER BY juliano ASC" if is_postgres else "SELECT id, estibas FROM lotes WHERE codigo=? ORDER BY juliano ASC"
            cur.execute(q, (codigo,))
            por=cant
            for r in cur.fetchall():
                if por<=0: break
                id_,est = r[0], int(r[1])
                if est <= por:
                    por -= est
                    cur.execute("DELETE FROM lotes WHERE id=%s" if is_postgres else "DELETE FROM lotes WHERE id=?", (id_,))
                else:
                    cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if is_postgres else "UPDATE lotes SET estibas=? WHERE id=?", (est-por, id_))
                    por=0
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error movimiento: {e}")
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
