@echo off
setlocal

set PACKAGE_NAME=Codic
REM set INSTALL_DIR=%APPDATA%\Keypirinha\InstalledPackages
set INSTALL_DIR=C:\Applications\Keypirinha\portable\Profile\InstalledPackages
set KEYPIRINHA_SDK_DIRECT=..\Sdk

if "%1"=="" goto help
if "%1"=="-h" goto help
if "%1"=="--help" goto help
if "%1"=="help" (
    :help
    echo Usage:
    echo   make help
    echo   make clean
    echo   make build
    echo   make install
    echo   make py [python_args]
    echo   make env
    echo   make deploy
    goto end
)

REM 環境変数の設定
if "%1"=="env" (
    REM pushd "%~dp0"
    call "%KEYPIRINHA_SDK_DIRECT%\cmd\kpenv.cmd"
    REM popd
    goto end
)

if "%BUILD_DIR%"=="" set BUILD_DIR=%~dp0build
if "%KEYPIRINHA_SDK%"=="" (
    echo ERROR: Keypirinha SDK environment not setup.
    echo        Run SDK's "kpenv" script and try again.
    exit /b 1
)

if "%1"=="clean" (
    if exist "%BUILD_DIR%" rmdir /s /q "%BUILD_DIR%"
    goto end
)

if "%1"=="build" (
    if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
    pushd "%~dp0"
    call "%KEYPIRINHA_SDK%\cmd\kparch" ^
        "%BUILD_DIR%\%PACKAGE_NAME%.keypirinha-package" ^
        -r LICENSE* README* src
    popd
    goto end
)

if "%1"=="install" (
    REM echo TODO: ensure the INSTALL_DIR variable declared at the top of this
    REM echo       script complies to your configuration and remove this message
    REM exit /1

    copy /Y "%BUILD_DIR%\*.keypirinha-package" "%INSTALL_DIR%\"
    goto end
)

if "%1"=="dev" (
    if not exist "%BUILD_DIR%" mkdir "%BUILD_DIR%"
    pushd "%~dp0"
    call "%KEYPIRINHA_SDK%\cmd\kparch" ^
        "%BUILD_DIR%\%PACKAGE_NAME%.keypirinha-package" ^
        -r LICENSE* README* src
    popd

    echo TODO: ensure the INSTALL_DIR variable declared at the top of this
    echo       script complies to your configuration and remove this message
    exit /1

    copy /Y "%BUILD_DIR%\*.keypirinha-package" "%INSTALL_DIR%\"
    goto end
)

if "%1"=="py" (
    call "%KEYPIRINHA_SDK%\cmd\kpy" %2 %3 %4 %5 %6 %7 %8 %9
    goto end
)

REM BuildしてInstall
if "%1"=="deploy" (
    call %0 build
    call %0 install
    goto end
)

:end
