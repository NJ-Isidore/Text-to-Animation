@echo off
chcp 65001 >nul
cd /d "%~dp0.."

if not "%~1"=="" goto run_args

set FOLDER_NAME=
set /p FOLDER_NAME="请输入子文件夹名称（可选，直接回车跳过）："
if not defined FOLDER_NAME goto run_interactive

uv run text2anim generate-images --name "%FOLDER_NAME%"
goto end

:run_interactive
uv run text2anim generate-images
goto end

:run_args
uv run text2anim generate-images %*
goto end

:end
