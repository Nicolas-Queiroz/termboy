#!/usr/bin/env python3
"""Gera os GIFs de demonstração em docs/ a partir do próprio código das aberturas.

Uso (na raiz do repositório):  python3 tools/gerar_gifs.py
Requer: Pillow  (pip install pillow)
"""
import importlib.machinery
import importlib.util
import functools
import math
import os

from PIL import Image, ImageDraw, ImageFont

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(RAIZ, "docs")

_loader = importlib.machinery.SourceFileLoader("termboy", os.path.join(RAIZ, "termboy"))
_spec = importlib.util.spec_from_loader("termboy", _loader)
ab = importlib.util.module_from_spec(_spec)
_loader.exec_module(ab)


FONTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf",
    "/usr/share/fonts/TTF/DejaVuSansMono-Bold.ttf",
    "/Library/Fonts/Courier New Bold.ttf",
    "C:/Windows/Fonts/consolab.ttf",
]


@functools.lru_cache(maxsize=8)
def fonte(tamanho):
    for caminho in FONTES:
        if os.path.exists(caminho):
            return ImageFont.truetype(caminho, tamanho)
    try:
        return ImageFont.load_default(size=tamanho)
    except TypeError:
        return ImageFont.load_default()


def imagem(tela, escala):
    im = Image.new("RGB", (tela.W, tela.H))
    im.putdata([c for linha in tela.px for c in linha])
    im = im.resize((tela.W * escala, tela.H * escala), Image.NEAREST)
    if tela.textos:
        d = ImageDraw.Draw(im)
        f = fonte(max(10, int(escala * 2 * 1.5)))
        for linha, txt, cor in tela.textos:
            if not 0 <= linha < tela.rows:
                continue
            larg = d.textlength(txt, font=f)
            x, y = (im.width - larg) / 2, linha * 2 * escala
            d.text((x + 1, y + 1), txt, font=f, fill=(0, 0, 0))
            d.text((x, y), txt, font=f, fill=tela.c(cor))
    return im


def salvar(nome, quadros, fps):
    caminho = os.path.join(DOCS, nome)
    pal = [q.quantize(colors=255, dither=Image.Dither.NONE) for q in quadros]
    pal[0].save(caminho, save_all=True, append_images=pal[1:], duration=int(1000 / fps), loop=0, optimize=True)
    print(f"  {nome:<16} {len(quadros):>4} quadros  {os.path.getsize(caminho) // 1024:>5} KB")


def grade(imagens, colunas, espaco=8, fundo=(13, 13, 20)):
    w, h = imagens[0].size
    linhas = math.ceil(len(imagens) / colunas)
    out = Image.new("RGB", (colunas * w + (colunas - 1) * espaco, linhas * h + (linhas - 1) * espaco), fundo)
    for i, im in enumerate(imagens):
        out.paste(im, ((i % colunas) * (w + espaco), (i // colunas) * (h + espaco)))
    return out


def gif_aberturas(tamanho=(100, 26), escala=4, fps=8):
    for nome, (_, _, dur, _) in ab.ABERTURAS.items():
        quadros, t = [], 0.0
        while t < dur:
            quadros.append(imagem(ab.quadro(nome, "gba", t, tamanho), escala))
            t += 1 / fps
        salvar(f"{nome}.gif", quadros, fps)


def gif_trailer(tamanho=(100, 26), escala=5, fps=10):
    cortes = [
        ("elementra", 4.6, 6.0), ("turbo", 2.4, 3.4), ("turbo", 6.6, 8.6), ("astro", 4.8, 6.4),
        ("reino", 0.6, 1.4), ("reino", 7.6, 9.0), ("elementra", 7.8, 9.8), ("astro", 9.0, 10.4),
        ("elementra", 13.4, 14.8), ("turbo", 12.2, 13.6), ("astro", 12.4, 13.8), ("reino", 11.8, 13.2),
    ]
    quadros = []
    for nome, ini, fim in cortes:
        t = ini
        while t < fim:
            quadros.append(imagem(ab.quadro(nome, "gba", t, tamanho), escala))
            t += 1 / fps
    salvar("trailer.gif", quadros, fps)


def gif_titulos(tamanho=(96, 24), escala=3, fps=8, dur=3.0):
    inicio = {"elementra": 14.6, "turbo": 13.6, "astro": 13.8, "reino": 12.8}
    quadros = []
    for k in range(int(dur * fps)):
        t = k / fps
        quadros.append(grade([imagem(ab.quadro(n, "gba", inicio[n] + t, tamanho), escala) for n in ab.ABERTURAS], 2))
    salvar("titulos.gif", quadros, fps)


def gif_estilos(tamanho=(64, 20), escala=3, fps=8):
    quadros, t = [], 6.0
    while t < 9.0:
        quadros.append(grade([imagem(ab.quadro("turbo", e, t, tamanho), escala) for e in ("gb", "gbc", "gba")], 3))
        t += 1 / fps
    salvar("estilos.gif", quadros, fps)


def gif_elenco(escala=3, fps=10, dur=3.0):
    cw, ch = 58, 58
    colunas, linhas = 4, 2
    tamanho = (cw * colunas, ch * linhas // 2)
    elenco = [
        ("FOFOLUME", lambda t, h: ab.fofolume(h, (t % 1.5) < 0.12), 1.0),
        ("CUBRASA", lambda t, h: ab.cubrasa(h, int(t * 6) % 2), 1.0),
        ("RUBRO-7", lambda t, h: ab.carro(int(h * 1.5), (220, 36, 48)), 1.0),
        ("FALCAO", lambda t, h: ab.nave(int(h * 0.7)), 1.0),
        ("DRONE", lambda t, h: ab.drone(int(h * 0.8)), 1.0),
        ("COLOSSO", lambda t, h: ab.colosso(int(h * 1.05)), 1.0),
        ("GUARDIAO", lambda t, h: ab.cavaleiro(int(h * 1.05), int(t * 6) % 4, (t % 3.0) > 1.5), 1.0),
        ("DRAGAO", lambda t, h: ab.dragao(int(h * 0.95), int(t * 5) % 2), 1.0),
    ]
    quadros = []
    for k in range(int(dur * fps)):
        t = k / fps
        tela = ab.Tela("gba", tamanho)
        tela.ceu([(0, (10, 8, 30)), (1, (40, 22, 70))])
        ab.estrelas(tela, t, vel=4)
        for i, (nome, fazer, _) in enumerate(elenco):
            cx, cy = (i % colunas) * cw, (i // colunas) * ch
            tela.retangulo(cx + 2, cy + ch - 9, cx + cw - 2, cy + ch - 8, (70, 50, 110))
            h = 30
            spr = fazer(t, h)
            bob = math.sin(t * 4 + i) * 1.2 if nome in ("CUBRASA", "FALCAO", "DRONE", "DRAGAO") else 0
            sx = cx + (cw - spr.w) / 2
            sy = cy + ch - 10 - spr.h + bob
            if nome == "FALCAO":
                tela.brilho(sx, sy + spr.h * 0.5, spr.h * (0.5 + 0.1 * math.sin(t * 30)), (120, 200, 255), 0.9)
            if nome == "RUBRO-7":
                for fx in (0.17, 0.83):
                    tela.brilho(sx + spr.w * fx, sy + spr.h * 0.56, spr.w * 0.12, (255, 60, 60), 0.6)
            if nome in ("COLOSSO", "DRAGAO"):
                fundo = (250, 225, 190) if nome == "DRAGAO" else (150, 90, 200)
                tela.brilho(sx + spr.w / 2, sy + spr.h / 2, spr.h * 0.9, fundo, 0.55)
                if nome == "DRAGAO":
                    tela.circulo(sx + spr.w * 0.55, sy + spr.h * 0.45, spr.h * 0.42, (240, 220, 190))
            tela.sombra(cx + cw / 2, cy + ch - 9, spr.w * 0.35, 1.2, 0.5)
            tela.desenhar(spr, sx, sy)
            if nome == "COLOSSO":
                for fx in (0.36, 0.6):
                    tela.brilho(sx + spr.w * fx, sy + spr.h * 0.42, spr.h * 0.14, (255, 40, 40), 1.0)
                    tela.ponto(sx + spr.w * fx, sy + spr.h * 0.42, (255, 230, 200))
            larg = len(nome) * 6 - 1
            for n, letra in enumerate(nome):
                x = cx + (cw - larg) / 2 + n * 6
                tela.letra(letra, x + 1, cy + ch - 6 + 1, 1, (20, 10, 30))
                tela.letra(letra, x, cy + ch - 6, 1, (255, 225, 120))
        quadros.append(imagem(tela, escala))
    salvar("elenco.gif", quadros, fps)


if __name__ == "__main__":
    os.makedirs(DOCS, exist_ok=True)
    print("Gerando GIFs em docs/:")
    gif_trailer()
    gif_elenco()
    gif_titulos()
    gif_estilos()
    gif_aberturas()
