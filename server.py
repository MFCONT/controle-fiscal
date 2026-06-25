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

# ── API: registros diários ───────────────────────────────────────────────────
@app.route("/api/registros/dia")
@login_required
def api_registros_dia():
    aid     = request.args.get("atividade_id", type=int)
    mes_ano = request.args.get("mes_ano", mes_ano_atual())
    return jsonify(db.listar_registros_dia(aid, mes_ano))

@app.route("/api/registros/dia/mes")
@login_required
def api_registros_dia_mes():
    mes_ano = request.args.get("mes_ano", mes_ano_atual())
    return jsonify(db.listar_registros_dia_mes(mes_ano))

@app.route("/api/registros/dia", methods=["POST"])
@login_required
def api_salvar_registros_dia():
    d = request.json
    aid = d["atividade_id"]
    # permissão
    if not session.get("admin"):
        ativs = db.listar_atividades_mes(d.get("mes_ano", mes_ano_atual()))
        alvo  = next((a for a in ativs if a["id"] == aid), None)
        if alvo and alvo["responsavel"] != session.get("responsavel",""):
            return jsonify({"erro": "Sem permissão."}), 403
    if d.get("datas_add"):
        db.salvar_registros_dia(aid, d["datas_add"],
                                d.get("status","Realizada"),
                                d.get("obs",""), session["usuario"])
    if d.get("datas_rem"):
        db.remover_registros_dia(aid, d["datas_rem"])
    return jsonify({"ok": True})

# ── API: descrições ───────────────────────────────────────────────────────────
@app.route("/api/atividades/<int:aid>/descricao", methods=["PUT"])
@login_required
def api_descricao(aid):
    d = request.json
    # somente admin ou dono da atividade
    if not session.get("admin"):
        ativs = db.listar_atividades_mes(mes_ano_atual())
        alvo  = next((a for a in ativs if a["id"] == aid), None)
        if alvo and alvo["responsavel"] != session.get("responsavel",""):
            return jsonify({"erro": "Sem permissão."}), 403
    db.atualizar_descricao(aid, d.get("descricao",""))
    return jsonify({"ok": True})

@app.route("/api/descricoes")
@login_required
def api_descricoes():
    resp = request.args.get("responsavel","Todos")
    return jsonify(db.listar_atividades_com_descricao(resp))

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

    class PDF(FPDF):
        def header(self): pass
        def footer(self):
            self.set_y(-12)
            self.set_font("Helvetica","I",7)
            self.set_text_color(150,150,150)
            self.cell(0,5,f"Página {self.page_no()}  |  Controle de Atividades - {mes_ano}",align="C")

    pdf = PDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()

    # ── Cabeçalho ──
    pdf.set_fill_color(30,77,120)
    pdf.set_text_color(255,255,255)
    pdf.set_font("Helvetica","B",15)
    titulo = f"Controle de Atividades — {mes_ano}"
    if responsavel != "Todos":
        titulo += f"  |  {responsavel}"
    pdf.cell(0,11,titulo,ln=True,fill=True,align="C")
    pdf.set_text_color(0,0,0)
    pdf.ln(3)

    # ── Resumo ──
    cnt = stats["contagem"]
    pdf.set_font("Helvetica","B",9)
    pdf.set_fill_color(240,244,250)
    resumo = (f"Total: {stats['total']}   |   Realizadas: {cnt.get('Realizada',0)}   |   "
              f"Em Andamento: {cnt.get('Em Andamento',0)}   |   "
              f"Pendentes: {cnt.get('Pendente',0)}   |   "
              f"Não Realizadas: {cnt.get('Não Realizada',0)}   |   "
              f"Conclusão: {stats['pct_conclusao']}%")
    pdf.cell(0,7,resumo,border=1,fill=True,ln=True,align="C")
    pdf.ln(4)

    # ── Tabela ──
    cores_status = {
        "Realizada":     (198,239,206),
        "Não Realizada": (255,199,206),
        "Em Andamento":  (255,235,156),
        "Pendente":      (230,230,230),
    }
    # larguras: total ~277mm (A4 landscape - margens)
    colunas = [
        ("Responsável", 30), ("Atividade", 72), ("Tipo", 20),
        ("Prazo",       22), ("Status",    28), ("Tempo", 16),
        ("Conclusão",   30), ("Obs",       40), ("Atualizado por", 30),
    ]
    pdf.set_font("Helvetica","B",8)
    pdf.set_fill_color(30,77,120)
    pdf.set_text_color(255,255,255)
    for h, w in colunas:
        pdf.cell(w, 7, h, border=1, fill=True, align="C")
    pdf.ln()
    pdf.set_text_color(0,0,0)

    for a in atividades:
        cor = cores_status.get(a["status"], (230,230,230))
        pdf.set_fill_color(*cor)
        pdf.set_font("Helvetica","",7)

        t = int(a.get("tempo_seg") or 0)
        tempo_str = f"{t//3600}h{(t%3600)//60:02d}m" if t else "—"
        prazo_str = f"Dia {a['prazo_dia']}" if a.get("prazo_dia") else "—"
        concl = (a.get("data_conclusao") or "").replace("T"," ")[:16] or "—"
        atu   = a.get("atualizado_por") or "—"
        obs   = (a.get("obs") or "—")[:40]
        nome  = a["nome"]

        # quebra de nome em 2 linhas se necessário
        h_row = 6
        pdf.cell(30, h_row, a["responsavel"][:18],        border=1, fill=True)
        pdf.cell(72, h_row, nome[:52],                    border=1, fill=True)
        pdf.cell(20, h_row, a["tipo"][:12],               border=1, fill=True, align="C")
        pdf.cell(22, h_row, prazo_str,                    border=1, fill=True, align="C")
        pdf.cell(28, h_row, a["status"],                  border=1, fill=True, align="C")
        pdf.cell(16, h_row, tempo_str,                    border=1, fill=True, align="C")
        pdf.cell(30, h_row, concl,                        border=1, fill=True, align="C")
        pdf.cell(40, h_row, obs,                          border=1, fill=True)
        pdf.cell(30, h_row, atu[:18],                     border=1, fill=True, ln=True)

    pdf.ln(4)
    pdf.set_font("Helvetica","I",7)
    pdf.set_text_color(120,120,120)
    pdf.cell(0,5,
        f"Gerado em {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')} "
        f"por {session.get('usuario','')}  |  Total de {len(atividades)} atividades",
        ln=True)
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
