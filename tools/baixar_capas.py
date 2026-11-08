"""Baixa capas de IA prontas (ex.: exportadas do Canva) para midia/fotos/ia/<slug>.jpg.

Recebe um JSON {"site-barbearia": "https://...", ...} na variável CAPAS ou no 1º argumento.
Confere se é imagem, ajusta para 1080x1350 (corte central) e registra o crédito
"Imagem ilustrativa gerada por IA" em midia/fotos/creditos.json.
Uso: CAPAS='{"site-loja": "https://..."}' python tools/baixar_capas.py [--modelo "Canva (IA)"]"""
import argparse
import io
import json
import os
import sys
from pathlib import Path

import requests
from PIL import Image, ImageOps

RAIZ = Path(__file__).resolve().parent.parent
CREDITOS = RAIZ / "midia" / "fotos" / "creditos.json"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("capas", nargs="?", default=os.environ.get("CAPAS", ""))
    ap.add_argument("--modelo", default="Canva (IA)")
    args = ap.parse_args()
    capas = json.loads(args.capas or "{}")
    if not capas:
        sys.exit("Nenhuma capa informada.")
    cred = json.loads(CREDITOS.read_text(encoding="utf-8"))
    falhas = []
    for slug, url in capas.items():
        try:
            r = requests.get(url, timeout=120)
            r.raise_for_status()
            img = ImageOps.fit(Image.open(io.BytesIO(r.content)).convert("RGB"), (1080, 1350), Image.LANCZOS)
        except Exception as e:  # noqa: BLE001
            falhas.append(f"{slug}: {e}")
            continue
        destino = RAIZ / "midia" / "fotos" / "ia" / f"{slug}.jpg"
        destino.parent.mkdir(parents=True, exist_ok=True)
        img.save(destino, "JPEG", quality=92, optimize=True)
        cred[f"ia/{slug}"] = {"arquivo": str(destino.relative_to(RAIZ)), "modelo": args.modelo,
                              "credito": "Imagem ilustrativa gerada por IA"}
        print("capa ok", slug)
    CREDITOS.write_text(json.dumps(cred, ensure_ascii=False, indent=2), encoding="utf-8")
    if falhas:
        sys.exit("Falharam: " + "; ".join(falhas))


if __name__ == "__main__":
    main()
