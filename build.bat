@echo off
cd /d "%~dp0"

echo Limpando builds antigos...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo Iniciando build...

pyinstaller --clean --noconfirm CIEC.spec

echo.
echo Build concluido.
pause