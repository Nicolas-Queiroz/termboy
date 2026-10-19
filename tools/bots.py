"""Bots que jogam o termboy sozinhos: provam que as fases são passáveis e gravam replays.

Os bots só leem o estado do jogo e devolvem teclas; a partida passa pelo mesmo
Jogo.atualizar() de quem joga de verdade, então o replay gravado é fiel.
"""
import importlib.machinery
import importlib.util
import os
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def carregar_termboy():
    if "termboy" in sys.modules:
        return sys.modules["termboy"]
    loader = importlib.machinery.SourceFileLoader("termboy", os.path.join(RAIZ, "termboy"))
    spec = importlib.util.spec_from_loader("termboy", loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    sys.modules["termboy"] = mod
    return mod


tb = carregar_termboy()


# ---------------------------------------------------------------- Pulo do Gato
def plano_gato(gato, fase, horizonte=60):
    """Busca em profundidade uma sequência de apertos que sobrevive `horizonte` ticks.

    Usa pulo de altura fixa (como no modo fallback), o pior caso para o jogador.
    Prefere não pular, então pula o mais tarde possível. Devolve None se não houver saída."""
    falhou = set()

    def busca(g, k):
        if k == 0:
            return []
        chave = (round(g.x, 3), round(g.y, 3), round(g.vy, 3), g.chao, round(g.coyote, 3), round(g.buffer, 3))
        if chave in falhou:
            return None
        pode_pular = (g.chao or g.coyote > 0) and g.vy >= 0
        for apertar in ((False, True) if pode_pular else (False,)):
            n = g.copia()
            if n.passo(tb.PASSO, fase, apertar, False, False) == "morreu":
                continue
            resto = busca(n, k - 1)
            if resto is not None:
                return [apertar] + resto
        falhou.add(chave)
        return None

    fase.garantir(gato.x + tb.VMAX * tb.PASSO * horizonte + 50)
    return busca(gato, horizonte)


class BotGato:
    """Joga o Pulo do Gato com pulo perfeito. Devolve as teclas de cada tick."""

    def __init__(self, replanejar=10, horizonte=90):
        self.plano, self.replanejar, self.horizonte = [], replanejar, horizonte

    def teclas(self, jogo):
        if len(self.plano) <= self.horizonte - self.replanejar:
            self.plano = plano_gato(jogo.gato, jogo.fase, self.horizonte) or [False]
        return [(" ", 1), (" ", 3)] if self.plano.pop(0) else []


# ---------------------------------------------------------------- Tocha Eterna
SETAS = {(0, -1): "↑", (0, 1): "↓", (-1, 0): "←", (1, 0): "→"}


class BotTocha:
    """Explora a masmorra com o que já viu: ataca o que estiver do lado, busca óleo quando
    a tocha está fraca, junta itens, explora a fronteira e desce a escada."""

    def teclas(self, jogo):
        if jogo.morreu_em is not None or jogo.t - jogo.ultimo_turno < 0.12:
            return []
        h, a = jogo.heroi, jogo.andar
        for c in a.inimigos:
            if abs(c.x - h.x) + abs(c.y - h.y) == 1 and (c.x, c.y) in jogo.visivel:
                return self._tecla(c.x - h.x, c.y - h.y)
        vistos = {p: i for p, i in a.itens.items() if p in jogo.explorado}
        oleo = {p for p, i in vistos.items() if i == "oleo"}
        outros = {p for p, i in vistos.items() if i != "oleo"}
        fronteira = {(x, y) for x, y in jogo.explorado if a.livre(x, y) and any(
            (x + dx, y + dy) not in jogo.explorado for dx, dy in SETAS)}
        escada = {a.escada} if a.escada in jogo.explorado else set()
        for alvo in ((oleo if jogo.oleo < 45 else set()), outros, fronteira, escada, oleo):
            passo = self._caminho(jogo, alvo)
            if passo:
                return self._tecla(*passo)
        return [(" ", 1), (" ", 3)]

    @staticmethod
    def _tecla(dx, dy):
        t = SETAS[(dx, dy)]
        return [(t, 1), (t, 3)]

    @staticmethod
    def _caminho(jogo, alvos):
        """Primeiro passo do menor caminho (BFS no que já foi visto) até algum alvo."""
        h, a = jogo.heroi, jogo.andar
        alvos = alvos - {(h.x, h.y)}
        if not alvos:
            return None
        bloqueio = {(c.x, c.y) for c in a.inimigos}
        origem = (h.x, h.y)
        veio, fila = {origem: None}, [origem]
        for p in fila:
            if p in alvos:
                while veio[p] != origem:
                    p = veio[p]
                return (p[0] - h.x, p[1] - h.y)
            for dx, dy in SETAS:
                q = (p[0] + dx, p[1] + dy)
                if q not in veio and a.livre(*q) and q in jogo.explorado and q not in bloqueio:
                    veio[q] = p
                    fila.append(q)
        return None


# ---------------------------------------------------------------- Turbo Asfalto
class BotTurbo:
    """Foge para a faixa livre mais próxima quando vem rival na sua."""

    def teclas(self, jogo):
        if jogo.batida is not None:
            return []
        perigo = {f: False for f in (-1, 0, 1)}
        rel = jogo.vel * 0.5
        for d, faixa, *_ in jogo.rivais:
            if -0.3 < d < rel * 0.9:
                perigo[faixa] = True
        if not perigo[jogo.faixa]:
            return []
        livres = sorted((abs(f - jogo.faixa), f) for f, p in perigo.items() if not p)
        if not livres:
            return []
        alvo = livres[0][1]
        t = "→" if alvo > jogo.faixa else "←"
        return [(t, 1), (t, 3)]


# ---------------------------------------------------------------- Astro Vértice
class BotAstro:
    """Desvia do que vem na sua coluna e caça drones para atirar."""

    def teclas(self, jogo):
        if jogo.morreu_em is not None:
            return []
        Y = jogo.Y_NAVE
        inseguro = set()
        for tipo, c, y, _ in jogo.inimigos:
            if Y - 0.35 < y < Y + 0.08:
                inseguro.add(c)
        for c, y in jogo.disparos:
            if Y - 0.3 < y < Y + 0.05:
                inseguro.add(c)
        cols = range(jogo.COLUNAS)
        if jogo.col in inseguro:
            seguras = sorted((abs(c - jogo.col), c) for c in cols if c not in inseguro)
            if seguras:
                return self._ir(jogo, seguras[0][1])
            return []
        drones = [c for tipo, c, y, _ in jogo.inimigos if tipo == "drone" and 0 < y < Y - 0.35]
        if jogo.col in drones:
            return [(" ", 1), (" ", 3)] if jogo.recarga == 0 else []
        alvos = sorted((abs(c - jogo.col), c) for c in drones
                       if all(k not in inseguro for k in range(min(c, jogo.col), max(c, jogo.col) + 1)))
        return self._ir(jogo, alvos[0][1]) if alvos else []

    @staticmethod
    def _ir(jogo, alvo):
        if alvo == jogo.col:
            return []
        t = "→" if alvo > jogo.col else "←"
        return [(t, 1), (t, 3)]


# ---------------------------------------------------------------- partida com bot
def partida(nome, semente, bot, max_ticks, modo="fallback", parar=None):
    """Joga com o bot e devolve (replay, jogo). parar(jogo) encerra antes, se der True."""
    jogo = tb.JOGOS[nome]()
    jogo.iniciar(semente)
    ent = tb.Entrada()
    ent.modo = modo
    eventos = []
    tick = 0
    for tick in range(max_ticks):
        for tecla, tipo in bot.teclas(jogo):
            ent.injetar(tecla, tipo)
            eventos.append([tick, tecla, tipo])
        r = jogo.atualizar(tb.PASSO, ent)
        ent.fim_do_tick()
        if r == "fim" or (parar and parar(jogo)):
            break
    dados = {"jogo": nome, "semente": semente, "modo": modo, "ticks": tick + 1,
             "pontos": jogo.pontos(), "eventos": eventos}
    return dados, jogo


# ---------------------------------------------------------------- registro
# (jogo, bot, ticks) das partidas usadas nos testes de replay e nos GIFs
PARTIDAS_DE_TESTE = [
    ("gato", BotGato, 900),
    ("tocha", BotTocha, 900),
    ("turbo", BotTurbo, 900),
    ("astro", BotAstro, 900),
]
