"""Controle de qualidade das fotos de personagens (pedido do João, 06/11: nada de foto desfocada).
- nitidez(): mede a nitidez da região central (rosto) já no tamanho em que a foto vai aparecer.
- ampliacao(): quanto a foto precisa ser ampliada para cobrir a área (>1 = upscale, perde definição).
- preparar(): recorta com LANCZOS e aplica um realce de nitidez leve (unsharp mask).
- aprovada(): só libera a foto se passar nos dois testes. Foto reprovada não vai para tela cheia."""
from PIL import Image, ImageFilter, ImageOps, ImageStat

LIMIAR_NITIDEZ = 220      # variância das bordas na região do rosto (calibrado em 06/11)
LIMIAR_AMPLIACAO = 1.10   # no máximo 10% de ampliação


def ampliacao(foto, tam):
    im = Image.open(foto)
    w, h = tam
    return max(w / im.width, h / im.height)


def preparar(foto, tam, centering=(0.5, 0.2), realce=True):
    im = ImageOps.fit(Image.open(foto).convert("RGB"), tam, Image.LANCZOS, centering=centering)
    if realce:
        im = im.filter(ImageFilter.UnsharpMask(radius=1.4, percent=60, threshold=2))
    return im


def nitidez(foto, tam, centering=(0.5, 0.2)):
    im = preparar(foto, tam, centering, realce=False).convert("L")
    w, h = im.size
    rosto = im.crop((int(w * 0.25), int(h * 0.08), int(w * 0.75), int(h * 0.6)))
    return ImageStat.Stat(rosto.filter(ImageFilter.FIND_EDGES)).var[0]


def aprovada(foto, tam, centering=(0.5, 0.2)):
    n, a = nitidez(foto, tam, centering), ampliacao(foto, tam)
    return n >= LIMIAR_NITIDEZ and a <= LIMIAR_AMPLIACAO, round(n), round(a, 2)
