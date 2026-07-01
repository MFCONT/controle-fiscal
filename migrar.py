"""Script de migração do banco PostgreSQL no Render."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DATABASE_URL'] = (
    'postgresql://controle_fiscal_db_user:rkmLoe0YnTry9XXFde8h6fNYEEeRQcHk'
    '@dpg-d8pe1mog4nts73ft9afg-a.oregon-postgres.render.com/controle_fiscal_db'
)
import database as db

conn = db.get_db()

# 1. colunas novas
for sql in [
    "ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS responsavel_nome TEXT DEFAULT ''",
    "ALTER TABLE registros ADD COLUMN IF NOT EXISTS data_conclusao TEXT DEFAULT ''",
]:
    db._ex(conn, sql)
    print("OK:", sql[:60])

# 2. sequence para atividades.id
db._ex(conn, """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_sequences WHERE sequencename='atividades_id_seq') THEN
            CREATE SEQUENCE atividades_id_seq;
            PERFORM setval('atividades_id_seq', COALESCE((SELECT MAX(id) FROM atividades),35)+1);
            ALTER TABLE atividades ALTER COLUMN id SET DEFAULT nextval('atividades_id_seq');
        END IF;
    END $$
""")
print("OK: sequence atividades_id_seq")

db._commit(conn)

# 3. vincula usuários a responsáveis
vinculos = [
    ('Angela',   'Ângela'),
    ('Juliana',  'Juliana'),
    ('Rebeca',   'Rebeca'),
    ('Miqueias', ''),
]
for nome, resp in vinculos:
    db._ex(conn, "UPDATE usuarios SET responsavel_nome=%s WHERE nome=%s", (resp, nome))
    print(f"Vinculado: {nome} -> '{resp}'")

db._commit(conn)
conn.close()
print("Migração concluída!")
