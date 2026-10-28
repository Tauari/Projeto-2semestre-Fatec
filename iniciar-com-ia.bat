@echo off
rem Liga o servidor da Aurora com a IA local (Ollama). Feche esta janela para desligar.
cd /d "%~dp0"
set AURORA_IA_PROVEDOR=ollama
start "" /min ollama serve
.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000 --no-access-log
