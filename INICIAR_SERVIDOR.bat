@echo off
title Controle Fiscal - Servidor
cd /d "%~dp0"

echo ============================================
echo   CONTROLE DE ATIVIDADES - SETOR FISCAL
echo ============================================
echo.
echo Instalando/verificando dependencias...
pip install -r requirements.txt -q
echo.
echo Iniciando servidor...
echo.
echo  Acesso LOCAL:  http://localhost:5000
echo  Acesso na REDE (outros PCs): veja o IP abaixo
echo.

:: mostra o IP da maquina na rede local
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /i "IPv4"') do (
    set IP=%%a
    goto :found
)
:found
set IP=%IP: =%
echo  Acesso pela REDE: http://%IP%:5000
echo.
echo  Login inicial: admin / admin123
echo.
echo  Pressione CTRL+C para encerrar o servidor
echo ============================================
echo.

python server.py
pause
