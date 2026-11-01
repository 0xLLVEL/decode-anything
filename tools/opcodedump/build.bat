@echo off
rem Rebuild php_opcodedump.dll from tools\opcodedump\opcodedump.c.
rem
rem The PHP 7.2 headers and the output directory live in the runtime bundle
rem (loader\refs\ic72dump-opcodes, gitignored), so point this script at it with
rem IONCUBE_OPCODEDUMP_HOME or fall back to the default path.
rem
rem Requires the Visual Studio x86 toolchain; edit VC_VARS if yours is elsewhere.
rem After a successful build, copy build\out\php_opcodedump.dll over
rem <bundle>\runtime\ext\php_opcodedump.dll.

setlocal
set SCRIPT_DIR=%~dp0
rem drop the trailing backslash: /I"<dir>\" would escape the closing quote
set SCRIPT_DIR=%SCRIPT_DIR:~0,-1%
set REPO_ROOT=%SCRIPT_DIR%\..\..
set SRC=%SCRIPT_DIR%\opcodedump.c

if "%IONCUBE_OPCODEDUMP_HOME%"=="" (
    set BUNDLE=%REPO_ROOT%\loader\refs\ic72dump-opcodes
) else (
    set BUNDLE=%IONCUBE_OPCODEDUMP_HOME%\ic72dump-opcodes
)

set DEVEL=%BUNDLE%\build\devel\php-7.2.34-devel-VC15-x86
set PHP_INC=%DEVEL%\include
set OUT=%BUNDLE%\build\out
set VC_VARS=C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Auxiliary\Build\vcvars32.bat

if not exist "%PHP_INC%\main\php.h" (
    echo ERROR: PHP 7.2 devel headers not found at %PHP_INC%\main\php.h
    exit /b 1
)
if not exist "%OUT%" mkdir "%OUT%"

call "%VC_VARS%" > nul 2>&1
if errorlevel 1 (
    echo ERROR: cannot initialise the x86 toolchain from "%VC_VARS%"
    exit /b 1
)

echo [1/2] Compiling opcodedump.c ...
cl.exe /nologo /c /MD /O2 /W3 /wd4996 ^
    /DWIN32 /D_WINDOWS /DZEND_WIN32=1 /DPHP_WIN32=1 ^
    /DCOMPILE_DL_OPCODEDUMP /DZEND_DEBUG=0 ^
    /D_USE_32BIT_TIME_T=1 ^
    /I"%PHP_INC%" /I"%PHP_INC%\main" /I"%PHP_INC%\Zend" ^
    /I"%PHP_INC%\TSRM" /I"%PHP_INC%\win32" /I"%PHP_INC%\ext" ^
    /I"%SCRIPT_DIR%" ^
    /Fo"%OUT%\opcodedump.obj" ^
    "%SRC%"
if errorlevel 1 ( echo ERROR: Compilation failed. & exit /b 1 )

echo [2/2] Linking php_opcodedump.dll ...
link.exe /nologo /DLL ^
    /OUT:"%OUT%\php_opcodedump.dll" ^
    /LIBPATH:"%DEVEL%\lib" ^
    "%OUT%\opcodedump.obj" ^
    php7.lib
if errorlevel 1 ( echo ERROR: Linking failed. & exit /b 1 )

echo SUCCESS: %OUT%\php_opcodedump.dll
echo Deploy: copy it to %BUNDLE%\runtime\ext\php_opcodedump.dll
endlocal
