@echo off
REM 一键启动脚本（仅针对当前电脑内置 Python 缺少 Tcl 库的情况）。
REM 标准 Python 环境可直接执行：python main.py
set TCL_LIBRARY=C:\dev\tcllib\tcl8.6
set TK_LIBRARY=C:\dev\tcllib\tk8.6
cd /d "%~dp0"
python main.py
pause
