"""Gera com o Gemini as capas dos carrosséis comuns pendentes (estilo: pessoa fictícia em cena dramática,
espaço escuro no topo para o título). Precisa da variável GEMINI_API_KEY; sem ela, não faz nada.
Salva em midia/fotos/ia/<slug>.jpg e registra em creditos.json como "ia/<slug>".
Uso: python tools/capas_ia.py <semana.json>"""
import base64, json, os, sys, urllib.request
from datetime import date, timedelta
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
RAIZ = Path(__file__).resolve().parent.parent
MODELOS = ["gemini-3-pro-image-preview", "gemini-2.5-flash-image"]
ESTILO = ("Cinematic editorial advertising photograph, vertical 4:5. {cena} The person is fictional, not a real or famous "
          "person. Dramatic moody lighting, dark graphite and charcoal tones, warm practical lights blurred in the "
          "background, subtle light sparks, slight film grain, shallow depth of field, photorealistic. The subject is "
          "centered in the lower 60% of the frame; the top 40% is dark, clean and out of focus, empty space for a "
          "title. No text, no letters, no logos, no watermarks.")


def gerar(prompt, destino, chave):
    for m in MODELOS:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent?key={chave}"
        corpo = {"contents": [{"parts": [{"text": prompt}]}],
                 "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "4:5"}}}
        try:
            req = urllib.request.Request(url, json.dumps(corpo).encode(), {"Content-Type": "application/json"})
            r = json.load(urllib.request.urlopen(req, timeout=180))
        except Exception as e:
            print("falhou", m, str(e)[:200])
            continue
        for c in r.get("candidates", []):
            for p in c.get("content", {}).get("parts", []):
                if "inlineData" in p:
                    destino.parent.mkdir(parents=True, exist_ok=True)
                    destino.write_bytes(base64.b64decode(p["inlineData"]["data"]))
                    return m
    return None


PADRAO = {
    "cardapio": "a fictional tired restaurant owner behind a busy counter at night, holding a phone full of order messages",
    "agenda": "a fictional stressed hair salon owner at the reception desk, phone ringing, paper agenda full of crossed-out times",
    "catalogo": "a fictional overwhelmed small shop owner surrounded by products, answering many customer messages on a phone",
    "site": "a fictional worried small business owner at a laptop in a small office, searching for his own business online",
}


def main():
    chave = os.environ.get("GEMINI_API_KEY")
    if not chave:
        print("GEMINI_API_KEY ausente: capas com IA não geradas")
        return
    sem = json.load(open(RAIZ / sys.argv[1]))
    fila = {i["id"]: i for i in json.load(open(RAIZ / "fila.json"))}
    cred_f = RAIZ / "midia/fotos/creditos.json"
    cred = json.load(open(cred_f))
    ini = date.fromisoformat(sem["inicio"])
    for k, dia in enumerate(sem["dias"]):
        data = (ini + timedelta(days=k)).isoformat()
        for n, post in enumerate(dia["posts"]):
            pid = f"{sem['prefixo']}_{data}_{n + 1}"
            # Só carrosséis de apresentação de produtos (vitrine). Nunca especialistas nem dicas.
            if not post.get("vitrine"):
                continue
            from src.servicos import LAMINAS
            tipo = post["vitrine"].get("tipo")
            slug = post.get("cenario") or (LAMINAS.get(tipo) or (None, None, None))[1]
            cena = post.get("prompt_capa") or PADRAO.get(tipo)
            if not cena or not slug or fila.get(pid, {}).get("status") != "pendente":
                continue
            destino = RAIZ / f"midia/fotos/ia/{slug}.jpg"
            if destino.exists():
                continue
            m = gerar(ESTILO.format(cena=cena), destino, chave)
            if m:
                cred[f"ia/{slug}"] = {"arquivo": str(destino.relative_to(RAIZ)), "modelo": m,
                                      "credito": "Imagem ilustrativa gerada por IA (Gemini)"}
                print("ok", pid, slug, m)
    json.dump(cred, open(cred_f, "w"), ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
