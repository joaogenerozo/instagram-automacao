"""Prepara a próxima semana: cria conteúdo novo com IA (se houver ANTHROPIC_API_KEY)
ou reaproveita as semanas existentes em rodízio. Depois gera as imagens e agenda."""
import os
import subprocess
import sys

from src.comum import RAIZ, carregar_fila
from gerar import proxima_segunda

inicio = proxima_segunda()
if any(p["id"].startswith(inicio.isoformat()) for p in carregar_fila()):
    sys.exit(f"Semana de {inicio} já está agendada.")

arquivos = sorted((RAIZ / "conteudo").glob("semana-*.json"))
arquivo = None
if os.environ.get("ANTHROPIC_API_KEY"):
    r = subprocess.run([sys.executable, "gerar_conteudo_ia.py"], capture_output=True, text=True, cwd=RAIZ)
    print(r.stdout, r.stderr)
    if r.returncode == 0:
        arquivo = r.stdout.strip().splitlines()[-1]
if not arquivo:
    semanas_agendadas = len({p["id"][:10] for p in carregar_fila()}) // 7
    arquivo = str(arquivos[semanas_agendadas % len(arquivos)].relative_to(RAIZ))
    print("Reaproveitando", arquivo)

subprocess.run([sys.executable, "gerar.py", arquivo, "--inicio", inicio.isoformat()], check=True, cwd=RAIZ)
