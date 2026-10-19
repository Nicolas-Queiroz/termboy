#!/usr/bin/env python3
"""Demo mínima do motor: um quadrado que pula com espaço.

    python3 tests/demo_pulo.py

Serve para sentir o pulo e conferir o teclado num terminal de verdade (no zellij,
no tmux...). A linha de baixo mostra o modo de entrada detectado: com "kitty",
segurar o espaço dá um pulo mais alto; no "fallback", todo pulo é igual.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from apoio import carregar_termboy  # noqa: E402

tb = carregar_termboy()
CHAO = tb.MUNDO_H * 0.8


class Quadrado:
    def __init__(self):
        self.x, self.y, self.vy, self.no_chao = 20.0, CHAO, 0.0, True

    def atualizar(self, dt, ent):
        if ent.apertou("pular") and self.no_chao:
            self.vy, self.no_chao = -90.0, False
        if ent.soltou("pular") and self.vy < 0:
            self.vy *= 0.5
        self.vy += (260 if self.vy < 0 else 420) * dt
        self.y += self.vy * dt
        if self.y >= CHAO:
            self.y, self.vy, self.no_chao = CHAO, 0.0, True
        self.x += 30 * dt


def main():
    estado = {"estilo": "gba"}
    q, cam = Quadrado(), tb.Camera()
    with tb.Terminal(estado, kitty=True) as term:
        laco = tb.Laco(term.entrada, term.saida)

        def atualizar(dt, ent):
            if ent.apertou({"q", "esc", "ctrl+c"}):
                return "sair"
            q.atualizar(dt, ent)
            if estado.pop("redimensionou", False):
                laco.redimensionou = True

        def desenhar():
            tela = tb.Tela(estado["estilo"])
            cam.ajustar(tela)
            cam.x = q.x - 20
            tela.ceu(tb.CEU_DIA)
            tb.montanhas(tela, cam.ty(CHAO), cam.px(14), cam.x * cam.escala * 0.3, (90, 140, 110), 1.3)
            tela.retangulo(0, cam.ty(CHAO), tela.W, tela.H, (110, 76, 50))
            tela.retangulo(0, cam.ty(CHAO), tela.W, cam.ty(CHAO) + 1, (90, 180, 70))
            tela.retangulo(cam.tx(q.x), cam.ty(q.y - 6), cam.tx(q.x + 6), cam.ty(q.y), (230, 80, 60))
            tela.texto(tela.rows - 1, f"espaço pula | q sai | modo: {term.entrada.modo}", (255, 255, 255))
            return tela

        laco.rodar(atualizar, desenhar)


if __name__ == "__main__":
    main()
