"""Testes do motor de jogo (Fase 1): render por diferença, entrada, câmera e utilitários."""
import os
import pty
import select
import subprocess
import sys
import tempfile
import time
import unittest

from apoio import RAIZ, TerminalFalso, carregar_termboy

tb = carregar_termboy()


class TestRenderDiferenca(unittest.TestCase):
    def test_diff_reproduz_o_quadro_cheio(self):
        """Aplicar quadros por diferença sobre o mesmo terminal dá a mesma tela que redesenhar tudo."""
        for nome in tb.ABERTURAS:
            with self.subTest(nome):
                term, ant = TerminalFalso(80, 24), None
                for k in range(12):
                    tela = tb.quadro(nome, "gba", 3.5 + k * 0.4, (80, 24))
                    grade = tela.celulas()
                    term.escrever(tb.emitir(grade, ant))
                    ant = grade
                    cheio = TerminalFalso(80, 24)
                    cheio.escrever(tela.render())
                    self.assertEqual(term.celulas, cheio.celulas, f"quadro {k}")

    def test_quadro_igual_nao_emite_nada(self):
        grade = tb.quadro("reino", "gba", 5.0, (80, 24)).celulas()
        self.assertEqual(tb.emitir(grade, grade), "")

    def test_saida_redesenha_tudo_ao_mudar_de_tamanho(self):
        escrito = []
        saida = tb.Saida(escrito.append)
        saida.mostrar(tb.quadro("turbo", "gba", 5.0, (80, 24)))
        saida.mostrar(tb.quadro("turbo", "gba", 5.0, (80, 24)))
        saida.mostrar(tb.quadro("turbo", "gba", 5.0, (90, 30)))
        self.assertEqual(len(escrito), 2)  # o quadro repetido não escreve nada
        self.assertTrue(escrito[1].startswith("\x1b[0m\x1b[2J"))

    def test_texto_alinhado(self):
        tela = tb.Tela("gba", (20, 4))
        tela.texto(0, "AB", (255, 255, 255), coluna=0)
        tela.texto(1, "CD", (255, 255, 255), coluna=-1)
        tela.texto(2, "EF", (255, 255, 255))
        g = tela.celulas()
        self.assertEqual([g[0][0][0], g[0][1][0]], ["A", "B"])
        self.assertEqual([g[1][18][0], g[1][19][0]], ["C", "D"])
        self.assertEqual([g[2][9][0], g[2][10][0]], ["E", "F"])


class TestTeclas(unittest.TestCase):
    def test_bytes_comuns(self):
        ev = tb.ler_teclas(" q\x1b[A\x1bOD\r\x1b")
        self.assertEqual([e[0] for e in ev], [" ", "q", "↑", "←", "enter", "esc"])
        self.assertTrue(all(not e[2] for e in ev))

    def test_kitty(self):
        # espaço apertou, repetiu, soltou; seta para cima soltou; ctrl+c; esc; resposta de consulta
        ev = tb.ler_teclas("\x1b[32u\x1b[32;1:2u\x1b[32;1:3u\x1b[1;1:3A\x1b[99;5u\x1b[27u\x1b[?11u")
        self.assertEqual(ev, [(" ", 1, True), (" ", 2, True), (" ", 3, True), ("↑", 3, True),
                              ("ctrl+c", 1, True), ("esc", 1, True)])

    def test_maiuscula_e_modificadores_viram_a_tecla_base(self):
        ev = tb.ler_teclas("Q\x1b[113;2u")
        self.assertEqual([e[0] for e in ev], ["q", "q"])


class TestEntrada(unittest.TestCase):
    def test_kitty_apertou_segurando_soltou(self):
        e = tb.Entrada()
        e.injetar(" ", 1)
        self.assertTrue(e.apertou("pular") and e.segurando("pular"))
        e.fim_do_tick()
        self.assertFalse(e.apertou("pular"))
        self.assertTrue(e.segurando("pular"))
        e.injetar(" ", 2)
        self.assertFalse(e.apertou("pular"))
        self.assertTrue(e.apertou("pular", repetir=True))
        e.fim_do_tick()
        e.injetar(" ", 3)
        self.assertTrue(e.soltou("pular"))
        self.assertFalse(e.segurando("pular"))

    def test_fallback_solta_por_tempo(self):
        e = tb.Entrada()
        e.injetar("w", 1, quando=10.0)
        self.assertTrue(e.apertou("pular"))
        e.fim_do_tick()
        e.injetar("w", 1, quando=10.1)  # autorepetição: não é um aperto novo
        self.assertFalse(e.apertou("pular"))
        e.ler(agora=10.2)
        self.assertTrue(e.segurando("pular"))
        e.ler(agora=10.3)
        self.assertTrue(e.soltou("pular"))
        self.assertFalse(e.segurando("pular"))


class TestKittyNoPty(unittest.TestCase):
    """Roda o termboy num pty fingindo ser um terminal com o protocolo do kitty."""

    def rodar(self, responder_kitty):
        pid, fd = pty.fork()
        if pid == 0:
            os.execvp(sys.executable, [sys.executable, os.path.join(RAIZ, "termboy"), "--teclado"])
        saida, respondeu, fim = b"", False, time.monotonic() + 5
        try:
            while time.monotonic() < fim:
                if select.select([fd], [], [], 0.05)[0]:
                    try:
                        saida += os.read(fd, 65536)
                    except OSError:
                        break
                if not respondeu and b"\x1b[c" in saida:
                    os.write(fd, (b"\x1b[?0u" if responder_kitty else b"") + b"\x1b[?62;22c")
                    respondeu = True
                if respondeu and b"modo" in saida:
                    os.write(fd, b"\x1b[113;1:1u" if responder_kitty else b"q")
                    respondeu = None
        finally:
            _, status = os.waitpid(pid, 0)
        return saida, status

    def test_ativa_e_desativa_kitty(self):
        saida, status = self.rodar(True)
        self.assertEqual(status, 0)
        self.assertIn(b"modo: kitty", saida)
        self.assertIn(b"\x1b[>11u", saida)
        self.assertTrue(saida.index(b"\x1b[<u") > saida.index(b"\x1b[>11u"))

    def test_sem_kitty_usa_fallback(self):
        saida, status = self.rodar(False)
        self.assertEqual(status, 0)
        self.assertIn(b"modo: fallback", saida)
        self.assertNotIn(b"\x1b[>11u", saida)


class TestMundo(unittest.TestCase):
    def test_camera_mantem_o_mundo_e_mostra_mais_a_frente(self):
        cam = tb.Camera()
        for tam in ((80, 24), (160, 48), (200, 30)):
            tela = tb.Tela("gba", tam)
            cam.ajustar(tela)
            self.assertAlmostEqual(cam.ty(tb.MUNDO_H), tela.H)
            self.assertGreaterEqual(cam.largura_visivel(), tb.MUNDO_W_MIN - 1e-9)
            self.assertLessEqual(tela.H - cam.ty(0), tela.H + 1e-9)

    def test_colide_com_folga(self):
        self.assertTrue(tb.colide((0, 0, 10, 10), (5, 5, 10, 10)))
        self.assertFalse(tb.colide((0, 0, 10, 10), (9, 0, 10, 10)))  # raspou
        self.assertFalse(tb.colide((0, 0, 10, 10), (20, 0, 10, 10)))

    def test_particulas_reaproveitam_o_pool(self):
        p = tb.Particulas(4)
        for _ in range(10):
            p.emitir(0, 0, 1, 0, 0.5, (255, 0, 0), grav=10)
        self.assertEqual(len(p.vivas()), 4)
        for _ in range(20):
            p.atualizar(1 / 30)
        self.assertEqual(len(p.vivas()), 0)
        p.emitir(0, 0, 1, 0, 0.5, (255, 0, 0))
        self.assertEqual(len(p.vivas()), 1)

    def test_recordes(self):
        with tempfile.TemporaryDirectory() as d:
            r = tb.Recordes(os.path.join(d, "x", "recordes.json"))
            self.assertEqual(r.registrar("gato", 100), 0)
            self.assertEqual(r.registrar("gato", 300), 0)
            self.assertEqual(r.registrar("gato", 200), 1)
            for p in (1, 2, 3):
                r.registrar("gato", p)
            self.assertIsNone(r.registrar("gato", 0))
            self.assertEqual([x["pontos"] for x in r.tabela("gato")], [300, 200, 100, 3, 2])
            self.assertFalse(os.path.exists(r.caminho + ".tmp"))
            with open(r.caminho, "w") as f:
                f.write("{corrompido")
            self.assertEqual(r.tabela("gato"), [])

    def test_xdg_data_home(self):
        with tempfile.TemporaryDirectory() as d:
            antigo = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_DATA_HOME"] = d
            try:
                self.assertEqual(tb.Recordes().caminho, os.path.join(d, "termboy", "recordes.json"))
            finally:
                if antigo is None:
                    del os.environ["XDG_DATA_HOME"]
                else:
                    os.environ["XDG_DATA_HOME"] = antigo


class TestDemoPulo(unittest.TestCase):
    def test_quadrado_pula_com_espaco(self):
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import demo_pulo
        q = demo_pulo.Quadrado()
        ent = tb.Entrada()
        alturas = []
        for tick in range(60):
            if tick == 5:
                ent.injetar(" ", 1)
            q.atualizar(tb.PASSO, ent)
            ent.fim_do_tick()
            alturas.append(q.y)
        self.assertEqual(alturas[4], demo_pulo.CHAO)
        self.assertLess(min(alturas), demo_pulo.CHAO - 10)
        self.assertEqual(alturas[-1], demo_pulo.CHAO)


class TestCLI(unittest.TestCase):
    def test_lista(self):
        r = subprocess.run([sys.executable, os.path.join(RAIZ, "termboy"), "-l"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)
        self.assertIn("Aberturas:", r.stdout)


if __name__ == "__main__":
    unittest.main()
