@echo off
echo ============================================
echo   Financeiro - Bruna e Vinicius
echo ============================================
echo.
echo Iniciando o dashboard...
echo.
echo Para o Vinicius acessar, mande o IP que vai aparecer na tela
echo do dashboard (canto superior direito).
echo.
cd /d "%~dp0"
streamlit run dashboard.py --server.headless false --server.port 8503
pause
