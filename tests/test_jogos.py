"""Testes da estrutura dos jogos (Fase 2) e dos jogos em si (Fases 3 a 5)."""
import hashlib
import json
import os
import sys
import tempfile
import unittest

from apoio import RAIZ, carregar_termboy

sys.path.insert(0, os.path.join(RAIZ, "tools"))
import bots  # noqa: E402

tb = bots.tb
# o bot e os testes precisam do mesmo módulo (mesmas classes)
assert carregar_termboy is not None


def hash_tela(jogo, tam=(80, 24)):
    tela = tb.Tela("gba", tam)
    jogo.desenhar(tela)
    return hashlib.sha256(repr(tela.celulas()).encode()).hexdigest()[:16]


class TestFliperama(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.rec = tb.Recordes(os.path.join(self.dir.name, "recordes.json"))
        self.fl = tb.Fliperama(["gato"], {"estilo": "gba"}, self.rec, semente=7)
        self.ent = tb.Entrada()

    def tearDown(self):
        self.dir.cleanup()

    def ticks(self, n, teclas=()):
        for k in range(n):
            if k == 0:
                for t in teclas:
                    self.ent.injetar(t, 1)
                    self.ent.injetar(t, 3)
            r = self.fl.atualizar(tb.PASSO, self.ent)
            self.ent.fim_do_tick()
            self.fl.desenhar(tb.Tela("gba", (80, 24)))
            if r:
                return r

    def ate(self, modo, limite=30 * 30):
        for _ in range(limite):
            if self.fl.modo == modo:
                return
            self.ticks(1)
        self.fail(f"não chegou em {modo}; está em {self.fl.modo}")

    def test_ciclo_completo(self):
        self.ticks(15)
        self.assertEqual(self.fl.modo, "abertura")
        self.ticks(1, ["enter"])
        self.assertEqual(self.fl.modo, "jogando")
        self.ticks(1, ["p"])
        self.assertEqual(self.fl.modo, "pausa")
        x = self.fl.jogo.gato.x
        self.ticks(30)
        self.assertEqual(self.fl.jogo.gato.x, x, "pausado não anda")
        self.ticks(1, ["p"])
        self.assertEqual(self.fl.modo, "jogando")
        self.ate("fim")  # sem pular, o gato cai no primeiro buraco
        self.ate("recorde", 30 * 3)
        self.assertEqual(len(self.rec.tabela("gato")), 1)
        self.ate("abertura", 30 * 7)

    def test_continue_recomeca(self):
        self.ticks(15)
        self.ticks(1, ["enter"])
        self.ate("fim")
        self.ticks(20)
        self.ticks(1, ["enter"])
        self.assertEqual(self.fl.modo, "jogando")
        self.assertLess(self.fl.jogo.gato.x, 30)

    def test_modo_atracao_recomeca_a_abertura(self):
        dur = tb.ABERTURAS["gato"][2]
        self.ticks(int(dur * 30) + 5)
        self.assertEqual(self.fl.modo, "abertura")
        self.assertLess(self.fl.t, 1.0)

    def test_q_sai(self):
        self.assertEqual(self.ticks(1, ["q"]), "sair")

    def test_terminal_pequeno_pausa_o_jogo(self):
        self.ticks(15)
        self.ticks(1, ["enter"])
        self.fl.desenhar(tb.Tela("gba", (60, 20)))
        x = self.fl.jogo.gato.x
        self.fl.atualizar(tb.PASSO, self.ent)
        self.assertEqual(self.fl.jogo.gato.x, x)

    def test_gravar_replay(self):
        arq = os.path.join(self.dir.name, "r.json")
        fl = tb.Fliperama(["gato"], {"estilo": "gba"}, self.rec, semente=3, gravar=arq)
        self.fl = fl
        self.ticks(15)
        self.ticks(1, ["enter"])
        self.ate("recorde")
        with open(arq) as f:
            dados = json.load(f)
        self.assertEqual(dados["jogo"], "gato")
        pontos = None
        for _, jogo in tb.replay(dados):
            pontos = jogo.pontos()
        self.assertEqual(pontos, dados["pontos"])


class TestPuloDoGato(unittest.TestCase):
    def test_fase_e_deterministica(self):
        a, b = tb.Fase(42), tb.Fase(42)
        a.garantir(20000)
        b.garantir(20000)
        self.assertEqual(a.historico, b.historico)
        self.assertNotEqual(a.historico, (lambda f: (f.garantir(20000), f.historico)[1])(tb.Fase(43)))

    def test_alcancabilidade_10_mil_metros(self):
        """Com pulo perfeito (e de altura fixa, como no fallback), nunca morre."""
        for semente in (1, 2, 3, 4):
            with self.subTest(semente=semente):
                _, jogo = bots.partida("gato", semente, bots.BotGato(), 10 ** 6,
                                       parar=lambda j: j.gato.x / tb.METRO >= 10000)
                self.assertIsNone(jogo.gato.morto, f"morreu em {jogo.metros()} m")
                self.assertGreaterEqual(jogo.metros(), 10000)

    def test_sem_pular_morre_logo(self):
        class Parado:
            def teclas(self, jogo):
                return []
        _, jogo = bots.partida("gato", 1, Parado(), 3000)
        self.assertIsNotNone(jogo.gato.morto)

    def test_todos_os_pedacos_aparecem(self):
        f = tb.Fase(5)
        f.garantir(40000)
        nomes = {n for _, n in f.historico}
        self.assertEqual(len(nomes), 8)

    def test_pulo_variavel_so_com_soltar_de_verdade(self):
        alturas = {}
        for modo in ("kitty", "fallback"):
            jogo = tb.PuloDoGato()
            jogo.iniciar(1)
            ent = tb.Entrada()
            ent.modo = modo
            ent.injetar(" ", 1)
            jogo.atualizar(tb.PASSO, ent)
            ent.fim_do_tick()
            ent.injetar(" ", 3)
            menor = tb.CHAO
            for _ in range(20):
                jogo.atualizar(tb.PASSO, ent)
                ent.fim_do_tick()
                menor = min(menor, jogo.gato.y)
            alturas[modo] = tb.CHAO - menor
        self.assertLess(alturas["kitty"], alturas["fallback"] * 0.6)

    def test_coyote_e_buffer(self):
        fase = tb.Fase(1)
        g = tb.Gato(0)
        g.chao, g.coyote = False, 0.05  # acabou de sair da beirada
        self.assertEqual(g.passo(tb.PASSO, fase, True, False, False), "pulou")
        g = tb.Gato(0)
        g.y, g.vy, g.chao = tb.CHAO - 2, 60.0, False  # quase tocando o chão
        g.passo(tb.PASSO, fase, True, False, False)  # apertou cedo demais
        eventos = [g.passo(tb.PASSO, fase, False, False, False) for _ in range(3)]
        self.assertIn("pulou", eventos)


class TestTochaEterna(unittest.TestCase):
    def test_todo_andar_e_conexo(self):
        """Flood fill da entrada alcança a escada e todo o piso do andar."""
        for semente in range(30):
            for numero in (1, 2, 5, 9):
                with self.subTest(semente=semente, andar=numero):
                    a = tb.Andar(semente, numero)
                    dist = a.distancias(a.entrada)
                    piso = {(x, y) for y in range(a.H) for x in range(a.W) if a.grade[y][x] == tb.PISO}
                    self.assertIn(a.escada, dist)
                    self.assertEqual(set(dist), piso)
                    for p in list(a.itens) + [(c.x, c.y) for c in a.inimigos]:
                        self.assertIn(p, piso)

    def test_mesma_semente_mesmo_andar(self):
        a, b, c = tb.Andar(7, 3), tb.Andar(7, 3), tb.Andar(8, 3)
        self.assertEqual(a.grade, b.grade)
        self.assertEqual((a.entrada, a.escada, a.itens), (b.entrada, b.escada, b.itens))
        self.assertNotEqual(a.grade, c.grade)

    def test_paredes_bloqueiam_a_visao(self):
        a = tb.Andar(1, 1)
        x, y = a.entrada
        vis = a.visiveis((x, y), 30)
        for (vx, vy) in vis:
            self.assertTrue(a._linha_livre(x, y, vx, vy))
        self.assertLess(len(vis), sum(r.count(tb.PISO) for r in a.grade))

    def jogo(self):
        j = tb.TochaEterna()
        j.iniciar(1)
        j.andar.inimigos.clear()
        j.andar.itens.clear()
        return j

    def andar_aberto(self, j):
        """Troca o andar por uma sala grande e vazia para testar comportamentos."""
        a = j.andar
        a.grade = [[tb.PISO if 0 < x < a.W - 1 and 0 < y < a.H - 1 else tb.PAREDE for x in range(a.W)]
                   for y in range(a.H)]
        a.escada = (a.W - 2, a.H - 2)
        j.heroi.x, j.heroi.y = 10, 10
        j._ver()

    def test_tocha_gasta_e_oleo_recarrega(self):
        j = self.jogo()
        self.andar_aberto(j)
        r0 = j.raio()
        for _ in range(40):
            j._turno(0, 0)
        self.assertLess(j.raio(), r0)
        j.andar.itens[(11, 10)] = "oleo"
        oleo = j.oleo
        j._turno(1, 0)
        self.assertGreater(j.oleo, oleo)
        j.oleo = 0.4
        j._turno(0, 0)
        self.assertEqual(j.raio(), 1.5)  # apagada: só enxerga em volta

    def test_inimigos_tem_comportamentos_diferentes(self):
        j = self.jogo()
        self.andar_aberto(j)
        g = tb.Criatura("gosma", 14, 10, 2)
        v = tb.Criatura("vulto", 13, 11, 1)
        p = tb.Criatura("pedrusco", 10, 15, 3)
        j.andar.inimigos[:] = [g, v, p]
        j._ver()
        j._turno(0, 0)
        self.assertEqual((g.x, g.y), (13, 10), "a gosma persegue")
        self.assertGreater(abs(v.x - 10) + abs(v.y - 10), 4, "o vulto foge da luz")
        movidas = []
        for _ in range(4):
            antes = (p.x, p.y)
            j._turno(0, 0)
            movidas.append(antes != (p.x, p.y))
        self.assertEqual(movidas.count(True), 2, "o pedrusco anda a cada dois turnos")

    def test_esbarrao_ataca(self):
        j = self.jogo()
        self.andar_aberto(j)
        g = tb.Criatura("gosma", 11, 10, 2)
        j.andar.inimigos[:] = [g]
        j._turno(1, 0)
        self.assertEqual((j.heroi.x, g.vida), (10, 1))
        j._turno(1, 0)
        self.assertEqual(j.andar.inimigos, [])
        self.assertEqual(j.abatidos, ["gosma"])

    def test_tocha_apagada_esconde_inimigos(self):
        j = self.jogo()
        self.andar_aberto(j)
        j.andar.inimigos[:] = [tb.Criatura("gosma", 11, 10, 2)]
        acesa = hash_tela(j)
        j.oleo = 0
        j._ver()
        apagada = hash_tela(j)
        j.andar.inimigos.clear()
        sem = hash_tela(j)
        self.assertNotEqual(acesa, apagada)
        self.assertEqual(apagada, sem)

    def test_escada_leva_ao_proximo_andar(self):
        j = self.jogo()
        self.andar_aberto(j)
        j.heroi.x, j.heroi.y = j.andar.escada[0] - 1, j.andar.escada[1]
        j._turno(1, 0)
        self.assertEqual(j.andar.numero, 2)
        self.assertEqual(j.pontos(), 250)


class TestTurboAsfalto(unittest.TestCase):
    def test_sempre_sobra_faixa_e_tempo_entre_fileiras(self):
        for semente in range(8):
            jogo = tb.TurboAsfalto()
            jogo.iniciar(semente)
            ent = tb.Entrada()
            chegadas = {}
            for _ in range(30 * 120):
                jogo.batida = None  # invencível: só queremos ver o que o gerador cria
                antes = len(jogo.rivais)
                jogo.atualizar(tb.PASSO, ent)
                novos = jogo.rivais[antes:] if len(jogo.rivais) > antes else []
                if novos:
                    chegadas[round(jogo.t, 4)] = {r[1] for r in novos}
            tempos = sorted(chegadas)
            with self.subTest(semente=semente):
                self.assertTrue(all(len(f) <= 2 for f in chegadas.values()))
                self.assertGreaterEqual(min(b - a for a, b in zip(tempos, tempos[1:])), tb.TurboAsfalto.INTERVALO - 0.05)

    def test_bot_sobrevive_dois_minutos(self):
        for semente in (1, 2, 3):
            with self.subTest(semente=semente):
                _, jogo = bots.partida("turbo", semente, bots.BotTurbo(), 30 * 120)
                self.assertIsNone(jogo.batida)
                self.assertGreater(jogo.ultrapassou, 30)

    def test_batida_encerra(self):
        class Parado:
            def teclas(self, jogo):
                return []
        dados, jogo = bots.partida("turbo", 1, Parado(), 30 * 120)
        self.assertIsNotNone(jogo.batida)
        self.assertLess(dados["ticks"], 30 * 120)


class TestAstroVertice(unittest.TestCase):
    def test_ondas_deixam_colunas_livres(self):
        jogo = tb.AstroVertice()
        jogo.iniciar(5)
        for k in range(300):
            jogo.t = k * 2.0
            antes = len(jogo.inimigos)
            jogo._onda()
            novos = jogo.inimigos[antes:]
            cols = [e[1] for e in novos]
            self.assertEqual(len(cols), len(set(cols)))
            self.assertLessEqual(len(cols), 3)
            self.assertLessEqual(sum(e[0] == "rocha" for e in novos), 2)

    def test_tiro_derruba_drone_e_nao_rocha(self):
        jogo = tb.AstroVertice()
        jogo.iniciar(1)
        jogo.proxima = 99
        jogo.inimigos = [["drone", 2, 0.3, 1], ["rocha", 3, 0.3, 1]]
        ent = tb.Entrada()
        ent.injetar(" ", 1)
        for _ in range(30):
            jogo.atualizar(tb.PASSO, ent)
            ent.fim_do_tick()
        self.assertEqual(jogo.abatidos, 1)
        ent.injetar("→", 1)
        jogo.atualizar(tb.PASSO, ent)
        ent.fim_do_tick()
        ent.injetar(" ", 1)
        for _ in range(30):
            jogo.atualizar(tb.PASSO, ent)
            ent.fim_do_tick()
        self.assertEqual([e[0] for e in jogo.inimigos], ["rocha"])

    def test_bot_sobrevive_dois_minutos(self):
        for semente in (1, 2, 3):
            with self.subTest(semente=semente):
                _, jogo = bots.partida("astro", semente, bots.BotAstro(), 30 * 120)
                self.assertIsNone(jogo.morreu_em)
                self.assertGreater(jogo.abatidos, 20)

    def test_nave_girada_aponta_para_cima(self):
        spr = tb.girar(tb.nave, 10)
        orig = tb.nave(10)
        self.assertEqual((spr.w, spr.h), (orig.h, orig.w))
        bico = max(x for x, _ in orig.px)  # a nave original aponta para a direita
        self.assertEqual(min(y for _, y in spr.px), orig.w - 1 - bico)
        self.assertEqual(len(spr.px), len(orig.px))


class TestDesenho(unittest.TestCase):
    def test_jogos_desenham_em_varios_tamanhos(self):
        """Durante uma partida de bot, cada jogo desenha sem quebrar em tamanhos variados."""
        for nome, bot, _ in bots.PARTIDAS_DE_TESTE:
            with self.subTest(nome):
                jogo = tb.JOGOS[nome]()
                jogo.iniciar(2)
                ent, b = tb.Entrada(), bot()
                for k in range(30 * 40):
                    for tecla, tipo in b.teclas(jogo):
                        ent.injetar(tecla, tipo)
                    fim = jogo.atualizar(tb.PASSO, ent)
                    ent.fim_do_tick()
                    if k % 45 == 0 or fim:
                        for tam in ((80, 24), (123, 37), (200, 60), (81, 50)):
                            jogo.desenhar(tb.Tela("gba", tam))
                    if fim:
                        break

    def test_fliperama_desenha_todos_os_modos(self):
        with tempfile.TemporaryDirectory() as d:
            fl = tb.Fliperama(list(tb.JOGOS), {"estilo": "gb"}, tb.Recordes(os.path.join(d, "r.json")), semente=1)
            ent = tb.Entrada()
            vistos = set()
            for k in range(30 * 60):
                if k % 40 == 20:
                    ent.injetar("enter" if fl.modo == "abertura" else "p", 1)
                if fl.modo == "pausa" and k % 40 == 30:
                    ent.injetar("p", 1)
                fl.atualizar(tb.PASSO, ent)
                ent.fim_do_tick()
                fl.desenhar(tb.Tela("gb", (80, 24)))
                vistos.add(fl.modo)
            self.assertTrue({"abertura", "jogando", "pausa"} <= vistos)


class TestReplays(unittest.TestCase):
    def test_replay_e_deterministico(self):
        """O replay de uma partida do bot termina no mesmo estado, quadro por quadro."""
        for nome, bot, ticks in bots.PARTIDAS_DE_TESTE:
            with self.subTest(nome):
                dados, jogo = bots.partida(nome, 11, bot(), ticks)
                fim = hash_tela(jogo)
                ultimo = None
                for _, ultimo in tb.replay(dados):
                    pass
                self.assertEqual(ultimo.pontos(), dados["pontos"])
                self.assertEqual(hash_tela(ultimo), fim)

    def test_replays_gravados_continuam_valendo(self):
        pasta = os.path.join(RAIZ, "tools", "replays")
        for arq in sorted(os.listdir(pasta)):
            with self.subTest(arq):
                with open(os.path.join(pasta, arq)) as f:
                    dados = json.load(f)
                ultimo = None
                for _, ultimo in tb.replay(dados):
                    pass
                self.assertEqual(ultimo.pontos(), dados["pontos"])


if __name__ == "__main__":
    unittest.main()
