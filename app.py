import os, traceback
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
        try:
            import psycopg2
            return psycopg2.connect(DATABASE_URL, sslmode='require')
        except:
            pass
    import sqlite3
    c=sqlite3.connect("/tmp/estanteria.db")
    c.row_factory=sqlite3.Row
    return c

def hoy_juliano(): return date.today().timetuple().tm_yday
def juliano_a_fecha(ddd):
    try:
        ddd=int(str(ddd)[-3:]); hoy=date.today(); base=date(hoy.year-1,1,1) if ddd>hoy.timetuple().tm_yday else date(hoy.year,1,1)
        return base+timedelta(days=ddd-1)
    except: return None
def semaforo(ddd):
    f=juliano_a_fecha(ddd)
    if not f: return {"color":"#adb5bd","emoji":"⚪","dias":999,"txt":"-"}
    dias=(date.today()-f).days
    if dias<=3: return {"color":"#198754","emoji":"🟢","dias":dias,"txt":f"{dias}d"}
    if dias<=8: return {"color":"#ffc107","emoji":"🟡","dias":dias,"txt":f"{dias}d"}
    return {"color":"#dc3545","emoji":"🔴","dias":dias,"txt":f"{dias}d"}

def init_db():
    try:
        conn=get_conn(); cur=conn.cursor()
        if DATABASE_URL:
            cur.execute("DROP TABLE IF EXISTS lotes")
            cur.execute("DROP TABLE IF EXISTS posiciones")
            cur.execute("CREATE TABLE posiciones (codigo TEXT PRIMARY KEY, bloque INT, nivel INT, calle INT)")
            cur.execute("CREATE TABLE lotes (id SERIAL PRIMARY KEY, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing DATE)")
            for b in range(1,BLOQUES+1):
                for n in range(1,NIVELES+1):
                    for c in range(1,CALLES+1):
                        cur.execute("INSERT INTO posiciones VALUES (%s,%s,%s,%s) ON CONFLICT DO NOTHING",(f"B{b}-N{n}-C{c}",b,n,c))
        else:
            cur.execute("DROP TABLE IF EXISTS lotes")
            cur.execute("CREATE TABLE lotes (id INTEGER PRIMARY KEY AUTOINCREMENT, codigo TEXT, bloque INT, nivel INT, calle INT, producto TEXT, juliano INT, estibas INT, fecha_ing TEXT)")
        conn.commit(); cur.close(); conn.close()
        print("DB OK - RECREADA")
    except Exception as e:
        print("Error init_db:", e)
        traceback.print_exc()

# lo intentamos pero si falla no tumbamos la app
try:
    init_db()
except:
    pass

@app.errorhandler(500)
def err500(e):
    return f"<h3>Error interno pero la app sigue viva</h3><p>{e}</p><p>{traceback.format_exc()}</p><a href='/reset_db'>CLICK AQUI PARA REPARAR BASE</a>"

@app.route("/reset_db")
def reset_db():
    try:
        conn=get_conn(); cur=conn.cursor()
        cur.execute("DROP TABLE IF EXISTS lotes")
        cur.execute("DROP TABLE IF EXISTS posiciones")
        conn.commit(); cur.close(); conn.close()
    except: pass
    init_db()
    return redirect("/")

# HTML corto para que abra seguro
HTML = """
<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Estantería de Flujo</title>
<link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
<style>.pos{border:1.5px solid #ccc; border-radius:6px; background:white; padding:3px; min-height:75px; margin:2px; flex:1; font-size:10px}.lote{font-size:9px; background:#f8f9fa; margin:1px 0}</style>
</head><body class="p-2"><div class="container-fluid">
<div class="d-flex gap-2 mb-2"><h6 class="fw-bold">📦 Estantería de Flujo {{total}} estibas</h6><span class="badge bg-primary ms-auto">Hoy={{hoy_jul}} JULIANO</span></div>
<div class="d-flex gap-1 mb-2">
{% for b in range(1,5) %}<a href="/?bloque={{b}}" class="btn btn-sm {{'btn-primary' if bloque==b else 'btn-outline-primary'}}">B{{b}} ({{tot_bloque[b]}})</a>{% endfor %}
<a href="/?bloque=0" class="btn btn-sm {{'btn-dark' if bloque==0 else 'btn-outline-dark'}}">TODO</a>
<a href="/reset_db" class="btn btn-sm btn-danger ms-auto">Reparar</a>
</div>
{% for b in bloques_ver %}
<div class="bg-dark text-white p-1 small">BLOQUE {{b}}</div>
<div class="bg-white border p-1 mb-2">
{% for n in range(6,0,-1) %}
<div class="d-flex">{% for c in range(1,11) %}
{% set k='B{}-N{}-C{}'.format(b,n,c) %}{% set lotes=grupos.get(k,[]) %}{% set total=sum(l.estibas for l in lotes) %}
<div class="pos"><b>N{{n}}-C{{c}}</b><br>{{total}} est.<br>
{% for l in lotes %}<div class="lote">{{l.producto}} {{l.estibas}}e J{{l.juliano}} {{l.sema.emoji}}</div>{% endfor %}
</div>
{% endfor %}</div>
{% endfor %}
</div>
{% endfor %}
<div class="card mt-2"><div class="card-body">
<form method="post" action="/movimiento" class="row g-1">
<div class="col-2"><select name="bloque" class="form-select form-select-sm">{% for b in range(1,5) %}<option value="{{b}}">B{{b}}</option>{% endfor %}</select></div>
<div class="col-2"><select name="nivel" class="form-select form-select-sm">{% for n in range(1,7) %}<option value="{{n}}">N{{n}}</option>{% endfor %}</select></div>
<div class="col-2"><select name="calle" class="form-select form-select-sm">{% for c in range(1,11) %}<option value="{{c}}">C{{c}}</option>{% endfor %}</select></div>
<div class="col-2"><input name="producto" class="form-control form-control-sm" value="12005778" required></div>
<div class="col-2"><input name="juliano" class="form-control form-control-sm" value="{{hoy_jul}}" type="number" required></div>
<div class="col-1"><input name="cantidad" class="form-control form-control-sm" value="1" type="number"></div>
<div class="col-1"><button class="btn btn-primary btn-sm w-100">+</button></div>
</form>
</div></div>
</div></body></html>
"""

@app.route("/")
def index():
    b_actual = int(request.args.get('bloque','1'))
    hoy_jul=hoy_juliano()
    conn=get_conn(); cur=conn.cursor()
    try: cur.execute("SELECT id,codigo,bloque,nivel,calle,producto,juliano,estibas FROM lotes ORDER BY juliano ASC"); rows=cur.fetchall()
    except: rows=[]
    grupos={}; tot_bloque={b:0 for b in range(1,5)}; total=0
    for r in rows:
        try:
            id_=r[0] if DATABASE_URL else r['id']; codigo=r[1] if DATABASE_URL else r['codigo']; bloque=r[2] if DATABASE_URL else r['bloque']
            producto=r[5] if DATABASE_URL else r['producto']; juliano=r[6] if DATABASE_URL else r['juliano']; estibas=r[7] if DATABASE_URL else r['estibas']
            s=semaforo(juliano)
            obj={"producto":producto,"juliano":juliano,"estibas":estibas,"sema":s}
            grupos.setdefault(codigo, []).append(obj); tot_bloque[bloque]+=estibas; total+=estibas
        except: continue
    bloques_ver=list(range(1,5)) if b_actual==0 else [b_actual]
    cur.close(); conn.close()
    return render_template_string(HTML, grupos=grupos, tot_bloque=tot_bloque, total=total, bloque=b_actual, bloques_ver=bloques_ver, hoy_jul=hoy_jul)

@app.route("/movimiento", methods=["POST"])
def mov():
    b=int(request.form['bloque']); n=int(request.form['nivel']); c=int(request.form['calle'])
    codigo=f"B{b}-N{n}-C{c}"; producto=request.form['producto']; cant=int(request.form['cantidad']); jul=int(request.form['juliano'])
    conn=get_conn(); cur=conn.cursor()
    try:
        f=juliano_a_fecha(jul)
        cur.execute("SELECT id, estibas FROM lotes WHERE codigo=%s AND producto=%s AND juliano=%s" if DATABASE_URL else "SELECT id, estibas FROM lotes WHERE codigo=? AND producto=? AND juliano=?",(codigo,producto,jul))
        row=cur.fetchone()
        if row:
            new_est=row[1]+cant
            cur.execute("UPDATE lotes SET estibas=%s WHERE id=%s" if DATABASE_URL else "UPDATE lotes SET estibas=? WHERE id=?",(new_est,row[0]))
        else:
            cur.execute("INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)" if DATABASE_URL else "INSERT INTO lotes (codigo,bloque,nivel,calle,producto,juliano,estibas,fecha_ing) VALUES (?,?,?,?,?,?,?,?)",(codigo,b,n,c,producto,jul,cant,f))
        conn.commit()
    except Exception as e:
        print(e)
    finally:
        cur.close(); conn.close()
    return redirect(f"/?bloque={b}")

if __name__=="__main__":
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT",5000)))
