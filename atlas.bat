@echo off
chcp 65001 >nul
cd /d "%~dp0"
python atlas_core\agent.py %*
