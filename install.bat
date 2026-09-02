@echo off
echo ========================================
echo   GM Components - Instalacion
echo ========================================
echo.

echo Instalando dependencias...
pip install -r requirements.txt

echo.
echo Instalando faiss-cpu...
pip install faiss-cpu

echo.
echo Instalando sentence-transformers...
pip install sentence-transformers

echo.
echo ========================================
echo   Instalacion completada
echo   Ejecuta run.bat para iniciar
echo ========================================
pause