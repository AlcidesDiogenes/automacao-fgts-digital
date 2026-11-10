@echo off
cd /d "%~dp0"
title FGTS Digital - Compilador do Instalador Windows

echo ========================================================
echo   FGTS Digital - Compilador do Instalador Profissional
echo ========================================================
echo.

if not exist "venv\Scripts\python.exe" (
    echo [ERRO] Ambiente virtual venv nao encontrado.
    pause
    exit /b 1
)

echo [1/4] Gerando assets visuais (icones e banners)...
"venv\Scripts\python.exe" "scripts\create_installer_assets.py"
if %errorlevel% neq 0 (
    echo [ERRO] Falha ao gerar assets.
    pause
    exit /b 1
)

echo.
echo [2/4] Empacotando aplicacao com PyInstaller...
"venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "fgts_digital.spec"
if %errorlevel% neq 0 (
    echo [ERRO] Falha no empacotamento com PyInstaller.
    pause
    exit /b 1
)

echo.
echo [3/4] Localizando compilador Inno Setup (ISCC.exe)...
set "ISCC_PATH="
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
) else if exist "C:\Program Files\Inno Setup 6\ISCC.exe" (
    set "ISCC_PATH=C:\Program Files\Inno Setup 6\ISCC.exe"
)

if "%ISCC_PATH%"=="" (
    echo [AVISO] ISCC.exe nao encontrado nos caminhos padrao. Tentando comando global...
    where iscc >nul 2>nul
    if %errorlevel% equ 0 (
        set "ISCC_PATH=iscc"
    ) else (
        echo [ERRO] Inno Setup 6 nao encontrado!
        echo Instale via winget: winget install JRSoftware.InnoSetup
        pause
        exit /b 1
    )
)

echo Compilador encontrado: %ISCC_PATH%

echo.
echo [4/4] Compilando instalador final...
"%ISCC_PATH%" "installer\FGTS_Digital_Setup.iss"
if %errorlevel% neq 0 (
    echo [ERRO] Falha na compilacao do instalador com Inno Setup.
    pause
    exit /b 1
)

echo.
echo ========================================================
echo   Instalador gerado com sucesso em: dist_installer\
echo ========================================================
echo.
pause
