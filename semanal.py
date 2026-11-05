"""Prepara a próxima semana: cria conteúdo novo com IA (se houver ANTHROPIC_API_KEY)
ou reaproveita as semanas existentes em rodízio. Depois gera as imagens e agenda."""
import os
import subprocess
import sys

from src.comum import RAIZ, carregar_fila
from datetime import date, datetime, timedelta

from gerar import proxima_segunda

# começa no dia seguinte ao último já agendado (sem sobrepor semanas), ou na próxima segunda
fila = carregar_fila()
ultimo = max((datetime.fromisoformat(p["quando"]).date() for p in fila), default=None)
inicio = max(proxima_segunda(), ultimo + timedelta(days=1)) if ultimo else proxima_segunda()
if ultimo and (ultimo - date.today()).days >= 7:
    sys.exit(f"Já há conteúdo agendado até {ultimo}. Nada a fazer.")

arquivos = sorted((RAIZ / "conteudo").glob("semana-*.json"))
arquivo = None
if os.environ.get("ANTHROPIC_API_KEY"):
    r = subprocess.run([sys.executable, "gerar_conteudo_ia.py"], capture_output=True, text=True, cwd=RAIZ)
    print(r.stdout, r.stderr)
    if r.returncode == 0:
        arquivo = r.stdout.strip().splitlines()[-1]
if not arquivo:
    semanas_agendadas = len({p["quando"][:10] for p in fila}) // 7
    arquivo = str(arquivos[semanas_agendadas % len(arquivos)].relative_to(RAIZ))
    print("Reaproveitando", arquivo)

# o dono autorizou publicar sem aprovação prévia; defina PEDIR_APROVACAO=1 para voltar a exigir
extra = ["--aprovacao"] if os.environ.get("PEDIR_APROVACAO") == "1" else []
subprocess.run([sys.executable, "gerar.py", arquivo, "--inicio", inicio.isoformat(), *extra], check=True, cwd=RAIZ)
