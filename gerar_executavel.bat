@echo off
setlocal
cd /d "%~dp0"
echo Instalando dependencias...
python -m pip install -r requirements.txt
echo.
echo Limpando build anterior...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
echo.
echo Gerando executavel...
pyinstaller --clean --noconfirm FichasTecnicas.spec
if not exist "dist\FichasTecnicas\data" mkdir "dist\FichasTecnicas\data"
if not exist "dist\FichasTecnicas\pdfs" mkdir "dist\FichasTecnicas\pdfs"
if not exist "dist\FichasTecnicas\backups" mkdir "dist\FichasTecnicas\backups"
if not exist "dist\FichasTecnicas\icon" mkdir "dist\FichasTecnicas\icon"
if exist "icon\icon.ico" copy /Y "icon\icon.ico" "dist\FichasTecnicas\icon\icon.ico" >nul
echo.
echo Finalizado.
echo O executavel fica em dist\FichasTecnicas\FichasTecnicas.exe.
echo O icone usado no executavel e na janela e icon\icon.ico.
endlocal
pause
