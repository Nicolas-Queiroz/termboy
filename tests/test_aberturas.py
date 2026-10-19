"""Não-regressão das aberturas: o que aparece na tela tem que continuar igual.

Para cada abertura, estilo e instante, desenha o quadro numa Tela de tamanho fixo,
passa a saída do render() por um terminal falso e compara o hash da grade com
tests/referencia.json.

Depois de uma mudança visual intencional, regrave as referências com:
    TERMBOY_REGRAVAR=1 python3 -m unittest discover -s tests -p test_aberturas.py
"""
import json
import os
import unittest

from apoio import TerminalFalso, carregar_termboy

tb = carregar_termboy()

REFERENCIA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "referencia.json")
REGRAVAR = bool(os.environ.get("TERMBOY_REGRAVAR"))

# 1.5 s: cena de abertura | 5 s: ação | 13.5 s: tela de título com texto e PRESS START
INSTANTES = (1.5, 5.0, 13.5)
CASOS = [((80, 24), estilo) for estilo in tb.ORDEM_ESTILOS] + [((123, 37), "gba")]


def chave(nome, tamanho, estilo, t):
    return f"{nome} {tamanho[0]}x{tamanho[1]} {estilo} t={t}"


def hash_quadro(nome, tamanho, estilo, t):
    tela = tb.quadro(nome, estilo, t, tamanho)
    term = TerminalFalso(*tamanho)
    term.escrever(tela.render())
    return term.hash()


class TestAberturas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.atuais = {chave(n, tam, est, t): hash_quadro(n, tam, est, t)
                      for n in tb.ABERTURAS for tam, est in CASOS for t in INSTANTES}
        if REGRAVAR:
            with open(REFERENCIA + ".tmp", "w") as f:
                json.dump(cls.atuais, f, indent=1, sort_keys=True)
                f.write("\n")
            os.replace(REFERENCIA + ".tmp", REFERENCIA)
        with open(REFERENCIA) as f:
            cls.referencia = json.load(f)

    def test_mesmos_casos(self):
        self.assertEqual(sorted(self.atuais), sorted(self.referencia))

    def test_quadros_iguais(self):
        for k, h in self.atuais.items():
            with self.subTest(k):
                self.assertEqual(h, self.referencia.get(k))

    def test_todos_os_quadros_desenham(self):
        """Varre cada abertura a 10 quadros/s, em tamanhos pequeno e normal: nada pode quebrar."""
        for nome, (_, _, dur, _) in tb.ABERTURAS.items():
            for tam in ((40, 12), (80, 24)):
                with self.subTest(nome=nome, tam=tam):
                    for k in range(int(dur * 10) + 1):
                        tb.quadro(nome, "gba", k / 10, tam).celulas()

    def test_terminal_falso_cobre_tela_inteira(self):
        """Garante que o teste enxerga cada célula, e não só as que mudaram."""
        tela = tb.quadro("reino", "gba", 13.5, (80, 24))
        term = TerminalFalso(80, 24)
        term.escrever(tela.render())
        vazias = sum(c == (" ", None, None) for linha in term.celulas for c in linha)
        self.assertEqual(vazias, 0)


if __name__ == "__main__":
    unittest.main()
