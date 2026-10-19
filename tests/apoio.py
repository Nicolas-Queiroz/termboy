"""Apoio aos testes: carrega o termboy (arquivo sem .py) e emula um terminal mínimo."""
import hashlib
import importlib.machinery
import importlib.util
import os
import re

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def carregar_termboy():
    # load_module() foi removido no Python 3.12; exec_module funciona em todos.
    loader = importlib.machinery.SourceFileLoader("termboy", os.path.join(RAIZ, "termboy"))
    spec = importlib.util.spec_from_loader("termboy", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod


_SEQ = re.compile(r"\x1b\[(\??[0-9;]*)([A-Za-z])")


class TerminalFalso:
    """Aplica a saída ANSI do render() numa grade de células (caractere, frente, fundo).

    Entende só o que o render emite: limpar (2J), posicionar cursor (H), cores 24 bits e
    reset (m); ignora o início/fim de quadro sincronizado (?2026h/l) e o pedido de status (5n).
    Comparar a grade, e não a string, deixa o teste valer também para o render por
    diferença da Fase 1, que emite menos bytes para o mesmo resultado na tela.
    """

    def __init__(self, cols, rows):
        self.cols, self.rows = cols, rows
        self.celulas = [[(" ", None, None)] * cols for _ in range(rows)]
        self.lin = self.col = 0
        self.fg = self.bg = None

    def escrever(self, saida):
        i = 0
        while i < len(saida):
            m = _SEQ.match(saida, i)
            if m:
                self._csi(m.group(1), m.group(2))
                i = m.end()
                continue
            if 0 <= self.lin < self.rows and 0 <= self.col < self.cols:
                self.celulas[self.lin][self.col] = (saida[i], self.fg, self.bg)
            self.col += 1
            i += 1

    def _csi(self, params, cmd):
        if params in ("?2026", "5"):
            return
        nums = [int(p) if p else 0 for p in params.split(";")] if params else []
        if cmd == "J" and nums == [2]:
            self.celulas = [[(" ", None, None)] * self.cols for _ in range(self.rows)]
        elif cmd == "H":
            self.lin = (nums[0] if nums else 1) - 1
            self.col = (nums[1] if len(nums) > 1 else 1) - 1
        elif cmd == "m":
            k = 0
            while k < len(nums) or not nums:
                n = nums[k] if nums else 0
                if n == 0:
                    self.fg = self.bg = None
                    k += 1
                elif n in (38, 48) and len(nums) >= k + 5 and nums[k + 1] == 2:
                    cor = tuple(nums[k + 2:k + 5])
                    if n == 38:
                        self.fg = cor
                    else:
                        self.bg = cor
                    k += 5
                else:
                    raise ValueError(f"SGR não suportado: {params!r}")
                if not nums:
                    break
        else:
            raise ValueError(f"sequência não suportada: CSI {params}{cmd}")

    def visivel(self):
        """A grade como o olho vê: um espaço mostra só o fundo, nas duas metades da célula."""
        return [[("▀", b, b) if ch == " " else (ch, f, b) for ch, f, b in linha] for linha in self.celulas]

    def hash(self):
        return hashlib.sha256(repr(self.visivel()).encode()).hexdigest()[:16]
