@echo off
chcp 65001 >nul
cd /d "%~dp0.."

if not "%~1"=="" goto run_args

set FOLDER_NAME=
set /p FOLDER_NAME="请输入图片子文件夹名称（可选，直接回车自动选择）："
if not defined FOLDER_NAME goto run_interactive

uv run text2anim generate-ppt --folder "%FOLDER_NAME%"
goto end

:run_interactive
uv run text2anim generate-ppt
goto end

:run_args
uv run text2anim generate-ppt %*
goto end

:end
