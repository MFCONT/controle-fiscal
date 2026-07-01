"""Apaga registros de julho/2026 em diante."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
os.environ['DATABASE_URL'] = (
    'postgresql://controle_fiscal_db_user:rkmLoe0YnTry9XXFde8h6fNYEEeRQcHk'
    '@dpg-d8pe1mog4nts73ft9afg-a.oregon-postgres.render.com/controle_fiscal_db'
)
import database as db

conn = db.get_db()
cur = db._ex(conn, "SELECT mes_ano, COUNT(*) as n FROM registros GROUP BY mes_ano ORDER BY mes_ano")
todos = db._rows(cur)
print("Registros existentes:")
for r in todos:
    print(f"  {r['mes_ano']}: {r['n']} registros")

# meses a manter: somente até 06/2026
meses_apagar = [r['mes_ano'] for r in todos
                if int(r['mes_ano'].split('/')[1]) > 2026
                or (int(r['mes_ano'].split('/')[1]) == 2026
                    and int(r['mes_ano'].split('/')[0]) >= 7)]

print(f"\nApagando: {meses_apagar}")
for ma in meses_apagar:
    db._ex(conn, "DELETE FROM registros WHERE mes_ano=%s", (ma,))
    print(f"  Deletado: {ma}")

db._commit(conn)
conn.close()
print("Concluído!")
