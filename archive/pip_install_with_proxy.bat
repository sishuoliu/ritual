@echo off
REM 通过公司代理安装 pip 包（如 reportlab）
REM 用法: pip_install_with_proxy.bat 或 双击运行后输入 pip install reportlab
set http_proxy=http://hkproxy.cicc.group:8080
set https_proxy=http://hkproxy.cicc.group:8080
pip install %*
pause
