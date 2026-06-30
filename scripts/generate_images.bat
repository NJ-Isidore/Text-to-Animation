@echo off
cd /d "%~dp0.."

set "ARGS=%*"

:loop

if "%ARGS%"=="" goto interactive

echo.
echo ========================================
echo   Generating images...
echo ========================================
echo.
uv run text2anim generate-images %ARGS%
set "ARGS="
goto ask

:interactive
echo.
echo ========================================
echo   Generating images (interactive mode)
echo ========================================
echo.
uv run text2anim generate-images

:ask
echo.
echo ========================================
echo   Done!
echo ========================================
echo.
uv run text2anim post-gen-prompt
if errorlevel 2 goto end
goto loop

:end
echo Bye.
timeout /t 2 >nul
