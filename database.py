"""Camada de acesso ao banco — suporta PostgreSQL (nuvem) e SQLite (local)."""
import os, hashlib, datetime

DATABASE_URL = os.environ.get("DATABASE_URL", "")
# Render usa 'postgres://' mas psycopg2 exige 'postgresql://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

USE_PG = bool(DATABASE_URL)

if not USE_PG:
    import sqlite3
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

# ── conexão ────────────────────────────────────────────────────────────────────
def get_db():
    if USE_PG:
        import psycopg2, psycopg2.extras
        conn = psycopg2.connect(DATABASE_URL)
        conn.autocommit = False
        return conn
    else:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

def _rows(cursor):
    """Converte resultado do cursor para lista de dicts."""
    if USE_PG:
        cols = [d[0] for d in cursor.description]
        return [dict(zip(cols, row)) for row in cursor.fetchall()]
    else:
        return [dict(r) for r in cursor.fetchall()]

def _row(cursor):
    r = _rows(cursor)
    return r[0] if r else None

def _ex(conn, sql, params=()):
    """Executa SQL adaptando placeholder e retorna cursor."""
    if USE_PG:
        sql = sql.replace("?", "%s")
    cur = conn.cursor()
    cur.execute(sql, params)
    return cur

def _commit(conn):
    if USE_PG:
        conn.commit()

# ── init ───────────────────────────────────────────────────────────────────────
def init_db():
    conn = get_db()
    try:
        if USE_PG:
            _init_pg(conn)
        else:
            _init_sqlite(conn)
        _commit(conn)
    finally:
        conn.close()

def _init_pg(conn):
    stmts = [
        """CREATE TABLE IF NOT EXISTS usuarios (
            id              SERIAL PRIMARY KEY,
            nome            TEXT UNIQUE NOT NULL,
            senha           TEXT NOT NULL,
            cor             TEXT DEFAULT '#2E75B6',
            admin           INTEGER DEFAULT 0,
            responsavel_nome TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS responsaveis (
            id   SERIAL PRIMARY KEY,
            nome TEXT UNIQUE NOT NULL,
            cor  TEXT DEFAULT '#2E75B6')""",
        """CREATE TABLE IF NOT EXISTS atividades (
            id          SERIAL PRIMARY KEY,
            responsavel TEXT NOT NULL,
            nome        TEXT NOT NULL,
            tipo        TEXT NOT NULL,
            prazo_dia   INTEGER,
            padrao      INTEGER DEFAULT 0,
            ativo       INTEGER DEFAULT 1,
            descricao   TEXT DEFAULT '')""",
        """CREATE TABLE IF NOT EXISTS registros_dia (
            id           SERIAL PRIMARY KEY,
            atividade_id INTEGER NOT NULL,
            data         TEXT NOT NULL,
            status       TEXT DEFAULT 'Realizada',
            obs          TEXT DEFAULT '',
            usuario      TEXT DEFAULT '',
            atualizado_em TEXT DEFAULT '',
            UNIQUE(atividade_id, data))""",
        """CREATE TABLE IF NOT EXISTS registros (
            id              SERIAL PRIMARY KEY,
            atividade_id    INTEGER NOT NULL,
            mes_ano         TEXT NOT NULL,
            status          TEXT DEFAULT 'Pendente',
            tempo_seg       REAL DEFAULT 0,
            obs             TEXT DEFAULT '',
            data_conclusao  TEXT DEFAULT '',
            atualizado_por  TEXT DEFAULT '',
            atualizado_em   TEXT DEFAULT '',
            UNIQUE(atividade_id, mes_ano))""",
    ]
    for s in stmts:
        _ex(conn, s)

    # migrations para tabelas já existentes
    _ex(conn, """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename='atividades_id_seq') THEN
                CREATE SEQUENCE atividades_id_seq;
                PERFORM setval('atividades_id_seq', COALESCE((SELECT MAX(id) FROM atividades),35)+1);
                ALTER TABLE atividades ALTER COLUMN id SET DEFAULT nextval('atividades_id_seq');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='registros' AND column_name='data_conclusao') THEN
                ALTER TABLE registros ADD COLUMN data_conclusao TEXT DEFAULT '';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='usuarios' AND column_name='responsavel_nome') THEN
                ALTER TABLE usuarios ADD COLUMN responsavel_nome TEXT DEFAULT '';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.columns
                           WHERE table_name='atividades' AND column_name='descricao') THEN
                ALTER TABLE atividades ADD COLUMN descricao TEXT DEFAULT '';
            END IF;
            IF NOT EXISTS (SELECT 1 FROM information_schema.tables
                           WHERE table_name='registros_dia') THEN
                CREATE TABLE registros_dia (
                    id            SERIAL PRIMARY KEY,
                    atividade_id  INTEGER NOT NULL,
                    data          TEXT NOT NULL,
                    status        TEXT DEFAULT 'Realizada',
                    obs           TEXT DEFAULT '',
                    usuario       TEXT DEFAULT '',
                    atualizado_em TEXT DEFAULT '',
                    UNIQUE(atividade_id, data));
            END IF;
        END $$
    """)

    for nome, cor in [("Ângela","#5B4FCF"),("Juliana","#28A745"),("Rebeca","#DC3545")]:
        _ex(conn, "INSERT INTO responsaveis(nome,cor) VALUES(%s,%s) ON CONFLICT DO NOTHING", (nome,cor))

    for (aid,resp,nome,tipo,prazo) in ATIVIDADES_PADRAO:
        _ex(conn, """INSERT INTO atividades(id,responsavel,nome,tipo,prazo_dia,padrao,ativo)
                     VALUES(%s,%s,%s,%s,%s,1,1) ON CONFLICT DO NOTHING""",
            (aid,resp,nome,tipo,prazo))

    _ex(conn, """INSERT INTO usuarios(nome,senha,cor,admin,responsavel_nome)
                 VALUES(%s,%s,%s,1,'') ON CONFLICT DO NOTHING""",
        ('admin', _hash('admin123'), '#1F4E79'))

def _init_sqlite(conn):
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        nome             TEXT UNIQUE NOT NULL,
        senha            TEXT NOT NULL,
        cor              TEXT DEFAULT '#2E75B6',
        admin            INTEGER DEFAULT 0,
        responsavel_nome TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS responsaveis (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        nome TEXT UNIQUE NOT NULL,
        cor  TEXT DEFAULT '#2E75B6');
    CREATE TABLE IF NOT EXISTS atividades (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        responsavel TEXT NOT NULL,
        nome        TEXT NOT NULL,
        tipo        TEXT NOT NULL,
        prazo_dia   INTEGER,
        padrao      INTEGER DEFAULT 0,
        ativo       INTEGER DEFAULT 1,
        descricao   TEXT DEFAULT '');
    CREATE TABLE IF NOT EXISTS registros_dia (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        atividade_id  INTEGER NOT NULL,
        data          TEXT NOT NULL,
        status        TEXT DEFAULT 'Realizada',
        obs           TEXT DEFAULT '',
        usuario       TEXT DEFAULT '',
        atualizado_em TEXT DEFAULT '',
        UNIQUE(atividade_id, data));
    CREATE TABLE IF NOT EXISTS registros (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        atividade_id   INTEGER NOT NULL,
        mes_ano        TEXT NOT NULL,
        status         TEXT DEFAULT 'Pendente',
        tempo_seg      REAL DEFAULT 0,
        obs            TEXT DEFAULT '',
        data_conclusao TEXT DEFAULT '',
        atualizado_por TEXT DEFAULT '',
        atualizado_em  TEXT DEFAULT '',
        UNIQUE(atividade_id, mes_ano));
    """)
    # migrations para banco existente
    for col_sql in [
        "ALTER TABLE registros ADD COLUMN data_conclusao TEXT DEFAULT ''",
        "ALTER TABLE usuarios ADD COLUMN responsavel_nome TEXT DEFAULT ''",
        "ALTER TABLE atividades ADD COLUMN descricao TEXT DEFAULT ''",
    ]:
        try: conn.execute(col_sql)
        except: pass
    for nome,cor in [("Ângela","#5B4FCF"),("Juliana","#28A745"),("Rebeca","#DC3545")]:
        conn.execute("INSERT OR IGNORE INTO responsaveis(nome,cor) VALUES(?,?)",(nome,cor))
    for (aid,resp,nome,tipo,prazo) in ATIVIDADES_PADRAO:
        conn.execute("INSERT OR IGNORE INTO atividades(id,responsavel,nome,tipo,prazo_dia,padrao,ativo) VALUES(?,?,?,?,?,1,1)",
                     (aid,resp,nome,tipo,prazo))
    conn.execute("INSERT OR IGNORE INTO usuarios(nome,senha,cor,admin,responsavel_nome) VALUES(?,?,?,1,'')",
                 ('admin',_hash('admin123'),'#1F4E79'))
    conn.commit()

# ── usuários ───────────────────────────────────────────────────────────────────
def login(nome, senha):
    conn = get_db()
    try:
        cur = _ex(conn, "SELECT * FROM usuarios WHERE nome=? AND senha=?", (nome, _hash(senha)))
        return _row(cur)
    finally: conn.close()

def listar_usuarios():
    conn = get_db()
    try:
        return _rows(_ex(conn, "SELECT id,nome,cor,admin FROM usuarios"))
    finally: conn.close()

def criar_usuario(nome, senha, cor="#2E75B6", admin=0, responsavel_nome=""):
    conn = get_db()
    try:
        try:
            _ex(conn, "INSERT INTO usuarios(nome,senha,cor,admin,responsavel_nome) VALUES(?,?,?,?,?)",
                (nome, _hash(senha), cor, admin, responsavel_nome))
            _commit(conn); return True
        except Exception: conn.rollback() if USE_PG else None; return False
    finally: conn.close()

def alterar_senha(nome, nova_senha):
    conn = get_db()
    try:
        _ex(conn, "UPDATE usuarios SET senha=? WHERE nome=?", (_hash(nova_senha), nome))
        _commit(conn)
    finally: conn.close()

def excluir_usuario(uid):
    conn = get_db()
    try:
        _ex(conn, "DELETE FROM usuarios WHERE id=? AND admin=0", (uid,))
        _commit(conn)
    finally: conn.close()

# ── responsáveis ───────────────────────────────────────────────────────────────
def listar_responsaveis():
    conn = get_db()
    try:
        return _rows(_ex(conn, "SELECT * FROM responsaveis ORDER BY nome"))
    finally: conn.close()

def criar_responsavel(nome, cor):
    conn = get_db()
    try:
        try:
            _ex(conn, "INSERT INTO responsaveis(nome,cor) VALUES(?,?)", (nome, cor))
            _commit(conn); return True
        except Exception: conn.rollback() if USE_PG else None; return False
    finally: conn.close()

def excluir_responsavel(rid):
    nomes_padrao = {a[1] for a in ATIVIDADES_PADRAO}
    conn = get_db()
    try:
        cur = _ex(conn, "SELECT nome FROM responsaveis WHERE id=?", (rid,))
        row = _row(cur)
        if not row or row["nome"] in nomes_padrao:
            return False
        _ex(conn, "UPDATE atividades SET ativo=0 WHERE responsavel=? AND padrao=0", (row["nome"],))
        _ex(conn, "DELETE FROM responsaveis WHERE id=?", (rid,))
        _commit(conn); return True
    finally: conn.close()

# ── atividades ─────────────────────────────────────────────────────────────────
def listar_atividades_mes(mes_ano, responsavel=None, status=None):
    conn = get_db()
    try:
        q = """SELECT a.id, a.responsavel, a.nome, a.tipo, a.prazo_dia, a.padrao,
                      COALESCE(r.status,'Pendente')       AS status,
                      COALESCE(r.tempo_seg,0)             AS tempo_seg,
                      COALESCE(r.obs,'')                  AS obs,
                      COALESCE(r.data_conclusao,'')       AS data_conclusao,
                      COALESCE(r.atualizado_por,'')       AS atualizado_por,
                      COALESCE(r.atualizado_em,'')        AS atualizado_em
               FROM atividades a
               LEFT JOIN registros r ON r.atividade_id=a.id AND r.mes_ano=?
               WHERE a.ativo=1"""
        params = [mes_ano]
        if responsavel and responsavel != "Todos":
            q += " AND a.responsavel=?"; params.append(responsavel)
        if status and status != "Todos":
            q += " AND COALESCE(r.status,'Pendente')=?"; params.append(status)
        q += " ORDER BY a.responsavel, a.id"
        return _rows(_ex(conn, q, params))
    finally: conn.close()

def criar_atividade(responsavel, nome, tipo, prazo_dia):
    conn = get_db()
    try:
        if USE_PG:
            cur = _ex(conn,
                "INSERT INTO atividades(responsavel,nome,tipo,prazo_dia,padrao,ativo) VALUES(%s,%s,%s,%s,0,1) RETURNING id",
                (responsavel, nome, tipo, prazo_dia))
            aid = cur.fetchone()[0]
        else:
            cur = _ex(conn,
                "INSERT INTO atividades(responsavel,nome,tipo,prazo_dia,padrao,ativo) VALUES(?,?,?,?,0,1)",
                (responsavel, nome, tipo, prazo_dia))
            aid = cur.lastrowid
        _commit(conn); return aid
    finally: conn.close()

def editar_atividade(aid, responsavel, nome, tipo, prazo_dia):
    conn = get_db()
    try:
        _ex(conn, "UPDATE atividades SET responsavel=?,nome=?,tipo=?,prazo_dia=? WHERE id=?",
            (responsavel, nome, tipo, prazo_dia, aid))
        _commit(conn)
    finally: conn.close()

def excluir_atividade(aid):
    conn = get_db()
    try:
        _ex(conn, "UPDATE atividades SET ativo=0 WHERE id=?", (aid,))
        _commit(conn)
    finally: conn.close()

def excluir_atividade_permanente(aid):
    conn = get_db()
    try:
        _ex(conn, "DELETE FROM registros WHERE atividade_id=?", (aid,))
        _ex(conn, "DELETE FROM atividades WHERE id=?", (aid,))
        _commit(conn)
    finally: conn.close()

def restaurar_atividade(aid):
    conn = get_db()
    try:
        _ex(conn, "UPDATE atividades SET ativo=1 WHERE id=?", (aid,))
        _commit(conn)
    finally: conn.close()

def atividades_ocultas():
    conn = get_db()
    try:
        return _rows(_ex(conn,
            "SELECT id,responsavel,nome FROM atividades WHERE ativo=0 AND padrao=1"))
    finally: conn.close()

# ── registros ──────────────────────────────────────────────────────────────────
def salvar_registro(atividade_id, mes_ano, status, tempo_seg, obs, usuario, data_conclusao=""):
    ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    conn = get_db()
    try:
        if USE_PG:
            _ex(conn, """INSERT INTO registros(atividade_id,mes_ano,status,tempo_seg,obs,data_conclusao,atualizado_por,atualizado_em)
                         VALUES(%s,%s,%s,%s,%s,%s,%s,%s)
                         ON CONFLICT(atividade_id,mes_ano) DO UPDATE SET
                             status=EXCLUDED.status, tempo_seg=EXCLUDED.tempo_seg,
                             obs=EXCLUDED.obs, data_conclusao=EXCLUDED.data_conclusao,
                             atualizado_por=EXCLUDED.atualizado_por,
                             atualizado_em=EXCLUDED.atualizado_em""",
                (atividade_id, mes_ano, status, tempo_seg, obs, data_conclusao, usuario, ts))
        else:
            _ex(conn, """INSERT INTO registros(atividade_id,mes_ano,status,tempo_seg,obs,data_conclusao,atualizado_por,atualizado_em)
                         VALUES(?,?,?,?,?,?,?,?)
                         ON CONFLICT(atividade_id,mes_ano) DO UPDATE SET
                             status=excluded.status, tempo_seg=excluded.tempo_seg,
                             obs=excluded.obs, data_conclusao=excluded.data_conclusao,
                             atualizado_por=excluded.atualizado_por,
                             atualizado_em=excluded.atualizado_em""",
                (atividade_id, mes_ano, status, tempo_seg, obs, data_conclusao, usuario, ts))
        _commit(conn)
    finally: conn.close()

def replicar_registro(atividade_id, mes_ano_origem, meses_destino, usuario):
    """Copia status/obs do mês origem para os meses de destino."""
    conn = get_db()
    try:
        cur = _ex(conn, "SELECT status,tempo_seg,obs FROM registros WHERE atividade_id=? AND mes_ano=?",
                  (atividade_id, mes_ano_origem))
        orig = _row(cur)
        if not orig:
            return
        ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        for ma in meses_destino:
            if USE_PG:
                _ex(conn, """INSERT INTO registros(atividade_id,mes_ano,status,tempo_seg,obs,data_conclusao,atualizado_por,atualizado_em)
                             VALUES(%s,%s,%s,%s,%s,'', %s,%s)
                             ON CONFLICT(atividade_id,mes_ano) DO UPDATE SET
                                 status=EXCLUDED.status, tempo_seg=EXCLUDED.tempo_seg,
                                 obs=EXCLUDED.obs, atualizado_por=EXCLUDED.atualizado_por,
                                 atualizado_em=EXCLUDED.atualizado_em""",
                    (atividade_id, ma, orig["status"], orig["tempo_seg"], orig["obs"], usuario, ts))
            else:
                _ex(conn, """INSERT INTO registros(atividade_id,mes_ano,status,tempo_seg,obs,data_conclusao,atualizado_por,atualizado_em)
                             VALUES(?,?,?,?,?,'',?,?)
                             ON CONFLICT(atividade_id,mes_ano) DO UPDATE SET
                                 status=excluded.status, tempo_seg=excluded.tempo_seg,
                                 obs=excluded.obs, atualizado_por=excluded.atualizado_por,
                                 atualizado_em=excluded.atualizado_em""",
                    (atividade_id, ma, orig["status"], orig["tempo_seg"], orig["obs"], usuario, ts))
        _commit(conn)
    finally: conn.close()

# ── registros diários ──────────────────────────────────────────────────────────
def listar_registros_dia(atividade_id, mes_ano):
    """Retorna lista de datas (DD/MM/YYYY) com registro para o mês."""
    m, y = mes_ano.split('/')
    prefixo = f"/{m}/{y}"
    conn = get_db()
    try:
        cur = _ex(conn,
            "SELECT data, status, obs FROM registros_dia WHERE atividade_id=? AND data LIKE ?",
            (atividade_id, f"%{prefixo}"))
        return _rows(cur)
    finally: conn.close()

def listar_registros_dia_mes(mes_ano):
    """Retorna todos os registros diários do mês para o calendário."""
    m, y = mes_ano.split('/')
    prefixo = f"/{m}/{y}"
    conn = get_db()
    try:
        cur = _ex(conn, """
            SELECT rd.atividade_id, rd.data, rd.status, rd.obs,
                   a.nome, a.responsavel
            FROM registros_dia rd
            JOIN atividades a ON a.id=rd.atividade_id
            WHERE rd.data LIKE ? AND a.ativo=1
        """, (f"%{prefixo}",))
        return _rows(cur)
    finally: conn.close()

def salvar_registros_dia(atividade_id, datas, status, obs, usuario):
    """Salva (upsert) registros diários para lista de datas."""
    ts = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
    conn = get_db()
    try:
        if USE_PG:
            for data in datas:
                _ex(conn, """INSERT INTO registros_dia(atividade_id,data,status,obs,usuario,atualizado_em)
                             VALUES(%s,%s,%s,%s,%s,%s)
                             ON CONFLICT(atividade_id,data) DO UPDATE SET
                             status=EXCLUDED.status, obs=EXCLUDED.obs,
                             usuario=EXCLUDED.usuario, atualizado_em=EXCLUDED.atualizado_em""",
                    (atividade_id, data, status, obs, usuario, ts))
        else:
            for data in datas:
                _ex(conn, """INSERT INTO registros_dia(atividade_id,data,status,obs,usuario,atualizado_em)
                             VALUES(?,?,?,?,?,?)
                             ON CONFLICT(atividade_id,data) DO UPDATE SET
                             status=excluded.status, obs=excluded.obs,
                             usuario=excluded.usuario, atualizado_em=excluded.atualizado_em""",
                    (atividade_id, data, status, obs, usuario, ts))
        _commit(conn)
    finally: conn.close()

def remover_registros_dia(atividade_id, datas):
    """Remove registros diários para datas desmarcadas."""
    conn = get_db()
    try:
        for data in datas:
            _ex(conn, "DELETE FROM registros_dia WHERE atividade_id=? AND data=?",
                (atividade_id, data))
        _commit(conn)
    finally: conn.close()

def atualizar_descricao(aid, descricao):
    conn = get_db()
    try:
        _ex(conn, "UPDATE atividades SET descricao=? WHERE id=?", (descricao, aid))
        _commit(conn)
    finally: conn.close()

def listar_atividades_com_descricao(responsavel=None):
    conn = get_db()
    try:
        q = "SELECT id, responsavel, nome, tipo, descricao FROM atividades WHERE ativo=1"
        params = []
        if responsavel and responsavel != "Todos":
            q += " AND responsavel=?"; params.append(responsavel)
        q += " ORDER BY responsavel, id"
        return _rows(_ex(conn, q, params))
    finally: conn.close()

# ── dashboard ──────────────────────────────────────────────────────────────────
def stats_mes(mes_ano):
    ativs = listar_atividades_mes(mes_ano)
    cnt = {"Pendente":0,"Em Andamento":0,"Realizada":0,"Não Realizada":0}
    tempo_resp = {}
    for a in ativs:
        cnt[a["status"]] = cnt.get(a["status"], 0) + 1
        tempo_resp[a["responsavel"]] = tempo_resp.get(a["responsavel"], 0) + a["tempo_seg"]
    total = len(ativs)
    pct   = round(cnt["Realizada"]/total*100) if total else 0
    return {"contagem": cnt, "total": total, "pct_conclusao": pct,
            "tempo_por_responsavel": tempo_resp}

def tendencia_6meses():
    hoje = datetime.date.today()
    result = []
    conn = get_db()
    try:
        cur = _ex(conn, "SELECT COUNT(*) FROM atividades WHERE ativo=1")
        total_ativ = cur.fetchone()[0]
    finally: conn.close()

    for d in range(-5, 1):
        m = hoje.month + d
        y = hoje.year + (m-1)//12
        m = ((m-1)%12)+1
        ma = f"{m:02d}/{y}"
        conn = get_db()
        try:
            cur = _ex(conn,
                "SELECT COUNT(*) FROM registros WHERE mes_ano=? AND status='Realizada'", (ma,))
            real = cur.fetchone()[0]
        finally: conn.close()
        result.append({"mes_ano": ma, "realizadas": real, "total": total_ativ})
    return result
