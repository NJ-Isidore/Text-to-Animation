@echo off
chcp 65001 >nul
cd /d "%~dp0.."

if not "%~1"=="" goto run_args

uv run text2anim generate-ppt
goto end

:run_args
uv run text2anim generate-ppt %*
goto end

:end
