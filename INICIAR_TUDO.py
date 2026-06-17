"""Inicia Flask + ngrok e mostra o link publico."""
import subprocess, time, urllib.request, json, os, sys, webbrowser

BASE = os.path.dirname(os.path.abspath(__file__))

# mata processos anteriores
os.system("taskkill /f /im ngrok.exe >nul 2>&1")
os.system("taskkill /f /im python.exe >nul 2>&1")
time.sleep(1)

print("=" * 52)
print("   CONTROLE DE ATIVIDADES - SETOR FISCAL")
print("=" * 52)
print()
print("[1/3] Iniciando servidor Flask...")
flask_proc = subprocess.Popen(
    [sys.executable, os.path.join(BASE, "server.py")],
    cwd=BASE,
    creationflags=subprocess.CREATE_NO_WINDOW
)
time.sleep(3)

# verifica se flask subiu
try:
    urllib.request.urlopen("http://localhost:5000/login", timeout=5)
    print("      OK - servidor rodando na porta 5000")
except Exception as e:
    print(f"      ERRO no servidor Flask: {e}")
    input("Pressione Enter para sair...")
    sys.exit(1)

print()
print("[2/3] Abrindo tunel ngrok para internet...")
ngrok_exe = os.path.join(BASE, "ngrok.exe")
ngrok_proc = subprocess.Popen(
    [ngrok_exe, "http", "5000"],
    cwd=BASE,
    creationflags=subprocess.CREATE_NO_WINDOW
)
time.sleep(4)

# pega URL publica
url_publica = None
for tentativa in range(10):
    try:
        r = urllib.request.urlopen("http://localhost:4040/api/tunnels", timeout=3)
        data = json.loads(r.read())
        for t in data.get("tunnels", []):
            if t.get("proto") == "https":
                url_publica = t["public_url"]
                break
        if url_publica:
            break
    except:
        pass
    time.sleep(1)

print()
if url_publica:
    print("[3/3] Sistema online!")
    print()
    print("=" * 52)
    print(f"  LINK PARA COMPARTILHAR:")
    print(f"  {url_publica}")
    print()
    print("  Login:  admin")
    print("  Senha:  admin123")
    print("=" * 52)
    print()
    print("  Envie o link acima para a equipe.")
    print("  O link funciona enquanto esta janela")
    print("  estiver aberta.")
    print()
    webbrowser.open(url_publica)
else:
    print("[3/3] ERRO: nao foi possivel obter o link do ngrok.")
    print("      Verifique sua conexao com a internet.")

print()
print("Pressione CTRL+C ou feche a janela para encerrar.")
try:
    flask_proc.wait()
except KeyboardInterrupt:
    pass
finally:
    flask_proc.terminate()
    ngrok_proc.terminate()
    print("Servidor encerrado.")
