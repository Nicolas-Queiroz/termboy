#!/usr/bin/env python3
"""Grava em tools/replays/ uma partida de cada jogo jogada pelos bots.

Uso (na raiz do repositório):  python3 tools/gravar_replays.py
Os replays alimentam os GIFs (tools/gerar_gifs.py) e o teste de não-regressão dos jogos.
Regrave depois de mudar a lógica de um jogo: replay antigo + lógica nova = outra partida.
"""
import json
import os

import bots

PASTA = os.path.join(bots.RAIZ, "tools", "replays")
# (jogo, semente, ticks): ~25 s de partida, o bastante para um GIF
GRAVAR = [(nome, 3, 30 * 25) for nome, _, _ in bots.PARTIDAS_DE_TESTE]


def main():
    os.makedirs(PASTA, exist_ok=True)
    tipos = {nome: bot for nome, bot, _ in bots.PARTIDAS_DE_TESTE}
    for nome, semente, ticks in GRAVAR:
        dados, _ = bots.partida(nome, semente, tipos[nome](), ticks)
        caminho = os.path.join(PASTA, f"{nome}.json")
        with open(caminho + ".tmp", "w") as f:
            json.dump(dados, f, separators=(",", ":"))
        os.replace(caminho + ".tmp", caminho)
        print(f"  {nome:<8} {dados['ticks']:>5} ticks  {dados['pontos']:>6} pontos  {len(dados['eventos'])} eventos")


if __name__ == "__main__":
    main()
