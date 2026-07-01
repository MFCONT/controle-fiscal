"""Migração 2 — adiciona tabela registros_dia e coluna descricao."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DATABASE_URL'] = (
    'postgresql://controle_fiscal_db_user:rkmLoe0YnTry9XXFde8h6fNYEEeRQcHk'
    '@dpg-d8pe1mog4nts73ft9afg-a.oregon-postgres.render.com/controle_fiscal_db'
)
import database as db

conn = db.get_db()

db._ex(conn, "ALTER TABLE atividades ADD COLUMN IF NOT EXISTS descricao TEXT DEFAULT ''")
print("OK: coluna descricao")

db._ex(conn, """
    DO $$
    BEGIN
        IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='registros_dia') THEN
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
print("OK: tabela registros_dia")

db._commit(conn)
conn.close()
print("Migração 2 concluída!")
