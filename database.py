"""Camada de acesso ao banco SQLite."""
import sqlite3, os, hashlib, datetime

DB_PATH = os.environ.get("DB_PATH", os.path.join(os.path.dirname(__file__), "dados.db"))

ATIVIDADES_PADRAO = [
    (1,  "Ângela",  "Apuração de ISSQN",                                 "Mensal",    15),
    (2,  "Ângela",  "Lançamentos de Guias e DAM",                        "Diária",    None),
    (3,  "Ângela",  "Cancelamentos de Nota Fiscal",                      "Diária",    None),
    (4,  "Ângela",  "Desconhecimento de Notas Fiscal",                   "Diária",    None),
    (5,  "Ângela",  "Conferência de Notas Uso e Consumo",                "Diária",    None),
    (6,  "Ângela",  "Lançamentos de Notas de Uso/Consumo e Imobilizado", "Diária",    None),
    (7,  "Ângela",  "Lançamentos de Notas Fiscais de Serviço",           "Diária",    None),
    (8,  "Ângela",  "Envio da EFD-Reinf",                                "Declaração",None),
    (9,  "Ângela",  "Envio do MIT",                                      "Declaração",None),
    (10, "Ângela",  "Suporte às Lojas",                                  "Diária",    None),
    (11, "Juliana", "Relatório ICMS Desonerado",                         "Mensal",    20),
    (12, "Juliana", "Relatório Notas de Saída XML",                      "Mensal",    20),
    (13, "Juliana", "Faturamento",                                       "Mensal",    25),
    (14, "Juliana", "Registro de PIN",                                   "Diária",    None),
    (15, "Juliana", "Relatório de Análise de Notas",                     "Mensal",    25),
    (16, "Rebeca",  "Relatório de PIN para Autorizar",                   "Diária",    None),
    (17, "Rebeca",  "Enviar XML de Saída para o Contador (Vetor)",       "Mensal",    10),
    (18, "Rebeca",  "Conferência de Parcelamentos Federal (ECAC)",       "Mensal",    10),
    (19, "Rebeca",  "Conferência de Parcelamentos Municipal (SEMEF)",    "Mensal",    10),
    (20, "Rebeca",  "Emitir Guias SUFRAMA (GRU)",                        "Mensal",    10),
    (21, "Rebeca",  "Regerar Filiais - Domínio",                         "Mensal",    13),
    (22, "Rebeca",  "Enviar Relatórios para EFD Contribuições",          "Declaração",15),
    (23, "Rebeca",  "Enviar Faturamento - Planilha",                     "Mensal",    15),
    (24, "Rebeca",  "Declarar Faturamento IBGE",                         "Mensal",    18),
    (25, "Rebeca",  "Relatório de Conta de Energia (CFOP 1253)",         "Mensal",    None),
    (26, "Rebeca",  "Relatório de Bonificações (CFOP 1910/2910)",        "Mensal",    None),
    (27, "Rebeca",  "Relatório de ICMS Desonerados (Vetor)",             "Mensal",    None),
    (28, "Rebeca",  "Relatório de Pagamento de Aluguéis PJ",            "Mensal",    None),
    (29, "Rebeca",  "Enviar Nota e Boleto Fornecedor IOB",               "Mensal",    None),
    (30, "Rebeca",  "Enviar Nota e Boleto Fornecedor SYSCONV",           "Mensal",    None),
    (31, "Rebeca",  "Controle das Notas Fiscais",                        "Mensal",    None),
    (32, "Rebeca",  "Controle de Pagamento dos Locatários",              "Mensal",    None),
    (33, "Rebeca",  "Processo de Fechamento",                            "Mensal",    None),
    (34, "Rebeca",  "IPVA - Consulta RENAVAM na SEFAZ",                  "Mensal",    None),
    (35, "Rebeca",  "Alvará - Inscrição Municipal",                      "Mensal",    None),
]

def _hash(pwd): return hashlib.sha256(pwd.encode()).hexdigest()

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            nome      TEXT    UNIQUE NOT NULL,
            senha     TEXT    NOT NULL,
            cor       TEXT    DEFAULT '#2E75B6',
            admin     INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS responsaveis (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT UNIQUE NOT NULL,
            cor  TEXT DEFAULT '#2E75B6'
        );
        CREATE TABLE IF NOT EXISTS atividades (
            id          INTEGER PRIMARY KEY,
            responsavel TEXT    NOT NULL,
            nome        TEXT    NOT NULL,
            tipo        TEXT    NOT NULL,
            prazo_dia   INTEGER,
            padrao      INTEGER DEFAULT 0,
            ativo       INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS registros (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            atividade_id INTEGER NOT NULL,
            mes_ano      TEXT    NOT NULL,
            status       TEXT    DEFAULT 'Pendente',
            tempo_seg    REAL    DEFAULT 0,
            obs          TEXT    DEFAULT '',
            atualizado_por TEXT  DEFAULT '',
            atualizado_em  TEXT  DEFAULT '',
            UNIQUE(atividade_id, mes_ano)
        );
        """)

        # responsáveis padrão
        for nome, cor in [("Ângela","#5B4FCF"),("Juliana","#28A745"),("Rebeca","#DC3545")]:
            db.execute("INSERT OR IGNORE INTO responsaveis(nome,cor) VALUES(?,?)", (nome,cor))

        # atividades padrão
        for (aid, resp, nome, tipo, prazo) in ATIVIDADES_PADRAO:
            db.execute("""INSERT OR IGNORE INTO atividades(id,responsavel,nome,tipo,prazo_dia,padrao,ativo)
                          VALUES(?,?,?,?,?,1,1)""", (aid, resp, nome, tipo, prazo))

        # usuário admin padrão
        db.execute("""INSERT OR IGNORE INTO usuarios(nome,senha,cor,admin)
                      VALUES('admin',?,?,1)""", (_hash('admin123'), '#1F4E79'))
        db.commit()

# ── usuários ──────────────────────────────────────────────────────────────────
def login(nome, senha):
    with get_db() as db:
        row = db.execute("SELECT * FROM usuarios WHERE nome=? AND senha=?",
                         (nome, _hash(senha))).fetchone()
        return dict(row) if row else None

def listar_usuarios():
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT id,nome,cor,admin FROM usuarios")]

def criar_usuario(nome, senha, cor="#2E75B6", admin=0):
    with get_db() as db:
        try:
            db.execute("INSERT INTO usuarios(nome,senha,cor,admin) VALUES(?,?,?,?)",
                       (nome, _hash(senha), cor, admin))
            db.commit(); return True
        except sqlite3.IntegrityError:
            return False

def alterar_senha(nome, nova_senha):
    with get_db() as db:
        db.execute("UPDATE usuarios SET senha=? WHERE nome=?", (_hash(nova_senha), nome))
        db.commit()

def excluir_usuario(uid):
    with get_db() as db:
        db.execute("DELETE FROM usuarios WHERE id=? AND admin=0", (uid,))
        db.commit()

# ── responsáveis ─────────────────────────────────────────────────────────────
def listar_responsaveis():
    with get_db() as db:
        return [dict(r) for r in db.execute("SELECT * FROM responsaveis ORDER BY nome")]

def criar_responsavel(nome, cor):
    with get_db() as db:
        try:
            db.execute("INSERT INTO responsaveis(nome,cor) VALUES(?,?)", (nome, cor))
            db.commit(); return True
        except sqlite3.IntegrityError:
            return False

def excluir_responsavel(rid):
    nomes_padrao = {a[1] for a in ATIVIDADES_PADRAO}
    with get_db() as db:
        row = db.execute("SELECT nome FROM responsaveis WHERE id=?", (rid,)).fetchone()
        if not row or row["nome"] in nomes_padrao:
            return False
        db.execute("UPDATE atividades SET ativo=0 WHERE responsavel=? AND padrao=0",
                   (row["nome"],))
        db.execute("DELETE FROM responsaveis WHERE id=?", (rid,))
        db.commit(); return True

# ── atividades ────────────────────────────────────────────────────────────────
def listar_atividades_mes(mes_ano, responsavel=None, status=None):
    with get_db() as db:
        q = """
            SELECT a.id, a.responsavel, a.nome, a.tipo, a.prazo_dia, a.padrao,
                   COALESCE(r.status,'Pendente')  AS status,
                   COALESCE(r.tempo_seg,0)        AS tempo_seg,
                   COALESCE(r.obs,'')             AS obs,
                   COALESCE(r.atualizado_por,'')  AS atualizado_por,
                   COALESCE(r.atualizado_em,'')   AS atualizado_em
            FROM atividades a
            LEFT JOIN registros r ON r.atividade_id=a.id AND r.mes_ano=?
            WHERE a.ativo=1
        """
        params = [mes_ano]
        if responsavel and responsavel != "Todos":
            q += " AND a.responsavel=?"; params.append(responsavel)
        if status and status != "Todos":
            q += " AND COALESCE(r.status,'Pendente')=?"; params.append(status)
        q += " ORDER BY a.responsavel, a.id"
        return [dict(r) for r in db.execute(q, params)]

def criar_atividade(responsavel, nome, tipo, prazo_dia):
    with get_db() as db:
        cur = db.execute(
            "INSERT INTO atividades(responsavel,nome,tipo,prazo_dia,padrao,ativo) VALUES(?,?,?,?,0,1)",
            (responsavel, nome, tipo, prazo_dia))
        db.commit(); return cur.lastrowid

def editar_atividade(aid, responsavel, nome, tipo, prazo_dia):
    with get_db() as db:
        db.execute("UPDATE atividades SET responsavel=?,nome=?,tipo=?,prazo_dia=? WHERE id=?",
                   (responsavel, nome, tipo, prazo_dia, aid))
        db.commit()

def excluir_atividade(aid):
    with get_db() as db:
        db.execute("UPDATE atividades SET ativo=0 WHERE id=?", (aid,))
        db.commit()

def restaurar_atividade(aid):
    with get_db() as db:
        db.execute("UPDATE atividades SET ativo=1 WHERE id=?", (aid,))
        db.commit()

def atividades_ocultas():
    with get_db() as db:
        return [dict(r) for r in db.execute(
            "SELECT id,responsavel,nome FROM atividades WHERE ativo=0 AND padrao=1")]

# ── registros ─────────────────────────────────────────────────────────────────
def salvar_registro(atividade_id, mes_ano, status, tempo_seg, obs, usuario):
    ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    with get_db() as db:
        db.execute("""
            INSERT INTO registros(atividade_id,mes_ano,status,tempo_seg,obs,atualizado_por,atualizado_em)
            VALUES(?,?,?,?,?,?,?)
            ON CONFLICT(atividade_id,mes_ano) DO UPDATE SET
                status=excluded.status,
                tempo_seg=excluded.tempo_seg,
                obs=excluded.obs,
                atualizado_por=excluded.atualizado_por,
                atualizado_em=excluded.atualizado_em
        """, (atividade_id, mes_ano, status, tempo_seg, obs, usuario, ts))
        db.commit()

# ── dashboard ─────────────────────────────────────────────────────────────────
def stats_mes(mes_ano):
    ativs = listar_atividades_mes(mes_ano)
    cnt = {"Pendente":0,"Em Andamento":0,"Realizada":0,"Não Realizada":0}
    tempo_resp = {}
    for a in ativs:
        cnt[a["status"]] = cnt.get(a["status"], 0) + 1
        tempo_resp[a["responsavel"]] = tempo_resp.get(a["responsavel"],0) + a["tempo_seg"]
    total = len(ativs)
    pct   = round(cnt["Realizada"]/total*100) if total else 0
    return {"contagem": cnt, "total": total, "pct_conclusao": pct,
            "tempo_por_responsavel": tempo_resp}

def tendencia_6meses():
    hoje  = datetime.date.today()
    result = []
    with get_db() as db:
        total_ativ = db.execute("SELECT COUNT(*) FROM atividades WHERE ativo=1").fetchone()[0]
    for d in range(-5, 1):
        m = hoje.month + d
        y = hoje.year + (m-1)//12
        m = ((m-1)%12)+1
        ma = f"{m:02d}/{y}"
        with get_db() as db:
            real = db.execute(
                "SELECT COUNT(*) FROM registros WHERE mes_ano=? AND status='Realizada'",
                (ma,)).fetchone()[0]
        result.append({"mes_ano": ma, "realizadas": real, "total": total_ativ})
    return result
