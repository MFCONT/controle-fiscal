# Guia de Deploy — Controle Fiscal na Nuvem

## Opção 1: Render.com (Recomendado — Gratuito)

### Passo 1 — Criar conta no GitHub
1. Acesse https://github.com e crie uma conta gratuita (se ainda não tiver)

### Passo 2 — Instalar Git no computador
1. Acesse https://git-scm.com/download/win e instale o Git
2. Após instalar, abra o **Prompt de Comando** (cmd) e execute:
   ```
   git --version
   ```
   Deve aparecer algo como: `git version 2.x.x`

### Passo 3 — Enviar o projeto para o GitHub
Abra o **Prompt de Comando**, navegue até a pasta `controle_web`:
```
cd "C:\Users\User\Documents\PROJETOS IA\CONTROLE ATIVIDADES_SETOR FISCAL\controle_web"
git init
git add .
git commit -m "Controle Fiscal Web"
```
Agora crie um repositório no GitHub:
1. Acesse https://github.com/new
2. Nome: `controle-fiscal` (sem espaços)
3. Clique em **Create repository**
4. Copie o link que aparece (ex: `https://github.com/seuusuario/controle-fiscal.git`)

De volta ao Prompt de Comando:
```
git remote add origin https://github.com/seuusuario/controle-fiscal.git
git push -u origin main
```

### Passo 4 — Criar conta no Render e publicar
1. Acesse https://render.com e clique em **Get Started for Free**
2. Faça login com sua conta do GitHub
3. Clique em **New → Web Service**
4. Conecte o repositório `controle-fiscal`
5. Preencha as configurações:
   - **Name:** controle-fiscal
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python server.py`
6. Em **Environment Variables**, adicione:
   - `SECRET_KEY` → qualquer senha forte (ex: `MinhaChaveSecreta2024!`)
   - `PORT` → `10000`
7. Clique em **Create Web Service**

Aguarde 2-3 minutos. O Render vai mostrar uma URL como:
```
https://controle-fiscal.onrender.com
```

Essa URL funciona de qualquer computador, celular ou tablet com internet!

---

## Opção 2: Railway.app (Plano gratuito limitado)

1. Acesse https://railway.app e faça login com o GitHub
2. Clique em **New Project → Deploy from GitHub repo**
3. Selecione o repositório `controle-fiscal`
4. Em **Variables**, adicione:
   - `SECRET_KEY` → senha forte
5. O Railway detecta o `Procfile` automaticamente e publica

---

## Após publicar — Primeiro acesso

1. Abra a URL gerada no navegador
2. Login: **admin** / **admin123**
3. **IMPORTANTE:** Vá em Gerenciar → Alterar Senha e troque a senha do admin imediatamente

---

## Compartilhando com a equipe

Basta enviar a URL pelo WhatsApp ou e-mail para Ângela, Juliana e Rebeca.

Cada pessoa pode criar seu próprio login em **Gerenciar → Usuários** (apenas admin).

---

## Notas importantes

- **O banco de dados fica na nuvem** — todos os computadores acessam os mesmos dados
- **O plano gratuito do Render** pode "adormecer" após 15 min sem uso (demora ~30s para acordar)
- Para uso contínuo sem latência, o plano pago do Render custa ~$7/mês
- **Backups:** para baixar os dados, acesse o painel do Render → Shell e execute:
  ```
  python -c "import sqlite3,json; db=sqlite3.connect('dados.db'); print('ok')"
  ```
