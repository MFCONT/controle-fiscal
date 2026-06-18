"""Servidor Flask — Controle de Atividades Setor Fiscal."""
import io, sys, os, calendar, datetime
from functools import wraps
from flask import (Flask, render_template, request, session, redirect,
                   url_for, jsonify, send_file, abort)

sys.path.insert(0, os.path.dirname(__file__))
import database as db

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "fiscal2024@setor#secret")

# inicializa banco ao importar (funciona com gunicorn e python direto)
db.init_db()

# ── helpers ──────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*a, **kw):
        if "usuario" not in session:
            return redirect(url_for("login"))
        return f(*a, **kw)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*a, **kw):
        if not session.get("admin"):
            return abort(403)
        return f(*a, **kw)
    return decorated

def mes_ano_atual():
    h = datetime.date.today()
    return f"{h.month:02d}/{h.year}"

# ── auth ──────────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    if "usuario" not in session:
        return redirect(url_for("login"))
    return redirect(url_for("painel"))

@app.route("/login", methods=["GET","POST"])
def login():
    erro = None
    if request.method == "POST":
        u = db.login(request.form["nome"].strip(), request.form["senha"])
        if u:
            session["usuario"]    = u["nome"]
            session["admin"]      = bool(u["admin"])
            session["cor"]        = u["cor"]
            session["responsavel"]= u.get("responsavel_nome","")
            return redirect(url_for("painel"))
        erro = "Usuário ou senha incorretos."
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ── páginas ────────────────────────────────────────────────────────────────────
@app.route("/painel")
@login_required
def painel():
    return render_template("index.html",
                           usuario=session["usuario"],
                           admin=session.get("admin", False),
                           responsavel=session.get("responsavel",""))

# ── API: atividades ───────────────────────────────────────────────────────────
@app.route("/api/atividades")
@login_required
def api_atividades():
    mes_ano    = request.args.get("mes_ano", mes_ano_atual())
    responsavel = request.args.get("responsavel", "Todos")
    status     = request.args.get("status", "Todos")
    return jsonify(db.listar_atividades_mes(mes_ano, responsavel, status))

@app.route("/api/atividades", methods=["POST"])
@login_required
def api_criar_atividade():
    d = request.json
    aid = db.criar_atividade(d["responsavel"], d["nome"], d["tipo"],
                              d.get("prazo_dia"))
    return jsonify({"id": aid}), 201

@app.route("/api/atividades/<int:aid>", methods=["PUT"])
@login_required
def api_editar_atividade(aid):
    d = request.json
    if session.get("admin"):
        db.editar_atividade(aid, d["responsavel"], d["nome"], d["tipo"],
                            d.get("prazo_dia"))
    return jsonify({"ok": True})

@app.route("/api/atividades/<int:aid>", methods=["DELETE"])
@login_required
def api_excluir_atividade(aid):
    permanente = request.args.get("permanente") == "1"
    if permanente and session.get("admin"):
        db.excluir_atividade_permanente(aid)
    else:
        db.excluir_atividade(aid)
    return jsonify({"ok": True})

@app.route("/api/atividades/<int:aid>/restaurar", methods=["POST"])
@login_required
def api_restaurar_atividade(aid):
    db.restaurar_atividade(aid)
    return jsonify({"ok": True})

@app.route("/api/atividades/ocultas")
@login_required
def api_ocultas():
    return jsonify(db.atividades_ocultas())

# ── API: registros ────────────────────────────────────────────────────────────
@app.route("/api/registros", methods=["POST"])
@login_required
def api_salvar_registro():
    d = request.json
    # verifica permissão: admin pode tudo; usuário comum só suas atividades
    if not session.get("admin"):
        ativs = db.listar_atividades_mes(d["mes_ano"])
        alvo  = next((a for a in ativs if a["id"] == d["atividade_id"]), None)
        if alvo and alvo["responsavel"] != session.get("responsavel",""):
            return jsonify({"erro": "Sem permissão para editar esta atividade."}), 403
    db.salvar_registro(d["atividade_id"], d["mes_ano"],
                       d["status"], d.get("tempo_seg", 0),
                       d.get("obs", ""), session["usuario"],
                       d.get("data_conclusao",""))
    return jsonify({"ok": True})

@app.route("/api/registros/replicar", methods=["POST"])
@login_required
def api_replicar_registro():
    d = request.json
    # mesma verificação de permissão
    if not session.get("admin"):
        ativs = db.listar_atividades_mes(d["mes_ano_origem"])
        alvo  = next((a for a in ativs if a["id"] == d["atividade_id"]), None)
        if alvo and alvo["responsavel"] != session.get("responsavel",""):
            return jsonify({"erro": "Sem permissão."}), 403
    db.replicar_registro(d["atividade_id"], d["mes_ano_origem"],
                         d["meses_destino"], session["usuario"])
    return jsonify({"ok": True})

# ── API: responsáveis ─────────────────────────────────────────────────────────
@app.route("/api/responsaveis")
@login_required
def api_responsaveis():
    return jsonify(db.listar_responsaveis())

@app.route("/api/responsaveis", methods=["POST"])
@login_required
def api_criar_responsavel():
    d = request.json
    ok = db.criar_responsavel(d["nome"], d.get("cor","#2E75B6"))
    return (jsonify({"ok": True}), 201) if ok else (jsonify({"erro":"Já existe"}), 409)

@app.route("/api/responsaveis/<int:rid>", methods=["DELETE"])
@login_required
def api_excluir_responsavel(rid):
    ok = db.excluir_responsavel(rid)
    return jsonify({"ok": ok})

# ── API: usuários (admin) ─────────────────────────────────────────────────────
@app.route("/api/usuarios")
@login_required
@admin_required
def api_usuarios():
    return jsonify(db.listar_usuarios())

@app.route("/api/usuarios", methods=["POST"])
@login_required
@admin_required
def api_criar_usuario():
    d = request.json
    ok = db.criar_usuario(d["nome"], d["senha"], d.get("cor","#2E75B6"),
                          d.get("admin",0), d.get("responsavel_nome",""))
    return (jsonify({"ok": True}), 201) if ok else (jsonify({"erro":"Já existe"}), 409)

@app.route("/api/usuarios/<int:uid>", methods=["DELETE"])
@login_required
@admin_required
def api_excluir_usuario(uid):
    db.excluir_usuario(uid)
    return jsonify({"ok": True})

@app.route("/api/senha", methods=["POST"])
@login_required
def api_alterar_senha():
    d = request.json
    db.alterar_senha(session["usuario"], d["nova_senha"])
    return jsonify({"ok": True})

# ── API: dashboard ────────────────────────────────────────────────────────────
@app.route("/api/stats")
@login_required
def api_stats():
    mes_ano = request.args.get("mes_ano", mes_ano_atual())
    return jsonify(db.stats_mes(mes_ano))

@app.route("/api/tendencia")
@login_required
def api_tendencia():
    return jsonify(db.tendencia_6meses())

# ── PDF ───────────────────────────────────────────────────────────────────────
@app.route("/api/relatorio/pdf")
@login_required
def api_pdf():
    mes_ano     = request.args.get("mes_ano", mes_ano_atual())
    responsavel = request.args.get("responsavel", "Todos")
    atividades  = db.listar_atividades_mes(mes_ano, responsavel)
    stats       = db.stats_mes(mes_ano)
    pdf_bytes   = _gerar_pdf(mes_ano, responsavel, atividades, stats)
    nome        = f"Relatorio_{mes_ano.replace('/','_')}.pdf"
    return send_file(io.BytesIO(pdf_bytes), mimetype="application/pdf",
                     as_attachment=True, download_name=nome)

def _gerar_pdf(mes_ano, responsavel, atividades, stats):
    from fpdf import FPDF
    pdf = FPDF()
    pdf.add_page()
    # cabeçalho
    pdf.set_fill_color(30, 77, 120)
    pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica","B",16)
    pdf.cell(0,12,f"Controle de Atividades - {mes_ano}",ln=True,fill=True,align="C")
    pdf.set_text_color(0,0,0)
    if responsavel != "Todos":
        pdf.set_font("Helvetica","",10)
        pdf.cell(0,7,f"Responsável: {responsavel}",ln=True)
    pdf.ln(2)
    # resumo
    pdf.set_font("Helvetica","B",11)
    pdf.cell(0,7,"Resumo",ln=True)
    pdf.set_font("Helvetica","",10)
    cnt = stats["contagem"]
    pdf.cell(0,6,f"Total: {stats['total']}   Realizadas: {cnt.get('Realizada',0)}   "
             f"Pendentes: {cnt.get('Pendente',0)}   Em Andamento: {cnt.get('Em Andamento',0)}   "
             f"Conclusão: {stats['pct_conclusao']}%", ln=True)
    pdf.ln(3)
    # tabela
    cores_status = {"Realizada":(198,239,206),"Não Realizada":(255,199,206),
                    "Em Andamento":(255,235,156),"Pendente":(230,230,230)}
    pdf.set_font("Helvetica","B",9)
    pdf.set_fill_color(30,77,120); pdf.set_text_color(255,255,255)
    for h,w in [("Responsável",35),("Atividade",80),("Tipo",22),("Status",28),("Tempo",18),("Obs",20)]:
        pdf.cell(w,7,h,border=1,fill=True)
    pdf.ln(); pdf.set_text_color(0,0,0)
    for a in atividades:
        cor = cores_status.get(a["status"],(230,230,230))
        pdf.set_fill_color(*cor)
        pdf.set_font("Helvetica","",8)
        t = int(a["tempo_seg"])
        tempo_str = f"{t//3600}h{(t%3600)//60:02d}m" if t else "-"
        pdf.cell(35,6,a["responsavel"][:20],border=1,fill=True)
        pdf.cell(80,6,a["nome"][:50],border=1,fill=True)
        pdf.cell(22,6,a["tipo"][:12],border=1,fill=True)
        pdf.cell(28,6,a["status"],border=1,fill=True)
        pdf.cell(18,6,tempo_str,border=1,fill=True,align="C")
        pdf.cell(20,6,(a["obs"] or "")[:18],border=1,fill=True,ln=True)
    pdf.ln(4)
    pdf.set_font("Helvetica","I",8)
    pdf.set_text_color(100,100,100)
    pdf.cell(0,5,f"Gerado em {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} "
             f"por {session.get('usuario','')}",ln=True)
    return pdf.output()

# ── main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    db.init_db()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("DEBUG", "false").lower() == "true"
    if debug:
        app.run(host="0.0.0.0", port=port, debug=True)
    else:
        try:
            from waitress import serve
            print(f"Servidor rodando em http://0.0.0.0:{port}")
            serve(app, host="0.0.0.0", port=port)
        except ImportError:
            app.run(host="0.0.0.0", port=port)
