@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Busca os pedais novos no Strava, classifica e regera o painel.
REM Dois cliques neste arquivo fazem tudo.

call .venv\Scripts\activate.bat
if errorlevel 1 goto erro

echo.
echo === buscando pedais novos ===
python src\atualizar.py
if errorlevel 1 goto erro

echo.
echo === classificando ===
python src\classificar.py
if errorlevel 1 goto erro

echo.
echo === gerando o painel ===
python src\gerar_site.py
if errorlevel 1 goto erro

echo.
echo pronto. abrindo o painel...
start "" "docs\site\index.html"
goto fim

:erro
echo.
echo *** algo deu errado — veja a mensagem acima ***

:fim
echo.
pause
