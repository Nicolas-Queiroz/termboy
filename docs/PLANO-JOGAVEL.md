# Plano: versão jogável do termboy

> **Aviso:** este plano foi escrito **sem ver o código**. Onde ele diverge da
> implementação real, vale o que está na seção
> [Revisão contra o código](#revisão-contra-o-código), e o que foi de fato
> construído está em [Como ficou](#como-ficou).

Dividido em fases que entregam algo usável no fim de cada uma. Primeiro se mexe
no motor, o que também beneficia as aberturas, e só depois nos jogos. **Uma fase
por sessão**: termine, verifique e pare.

## Andamento

- [x] Fase 0: preparação
- [x] Fase 1: motor de jogo
- [x] Fase 2: estrutura dos jogos
- [x] Fase 3: Pulo do Gato (corredor)
- [x] Fase 4: Tocha Eterna (roguelike)
- [x] Fase 5: mais jogos e polimento
- [ ] Testar o modo kitty dentro do zellij num terminal de verdade (`termboy --teclado`)
- [ ] Jogar cada jogo de verdade e ajustar dificuldade (os bots só provam que é possível)

---

## Fase 0: preparação

Branch `jogavel` e pasta `tests/` fora do arquivo principal. Ela é só de
desenvolvimento, como `tools/`, então a regra de "um arquivo" continua valendo
para o que o usuário baixa.

O primeiro teste é de não-regressão: renderizar quadros fixos de cada abertura
numa `Tela` de tamanho fixo e comparar um hash da saída. Assim, quando a Fase 1
mexer no render, dá para saber se alguma abertura quebrou.

```bash
git switch -c jogavel
mkdir -p tests
python3 -m unittest discover -s tests -v
```

## Fase 1: motor de jogo

Seis peças, todas dentro do `termboy`.

1. **Render por diferença.** O render guarda o último quadro e, a cada quadro,
   emite só as células que mudaram, agrupando sequências contíguas na mesma
   linha (um posicionamento de cursor por sequência) e só reemitindo
   `38;2`/`48;2` quando a cor muda em relação à célula anterior emitida.
   `forcar=True` redesenha tudo, usado na primeira vez e após resize.

2. **Resize.** Tratar `SIGWINCH` com um handler que só marca uma flag. O laço
   principal recria a `Tela` e força o redesenho completo. Nada de redesenhar
   dentro do handler.

3. **Classe `Entrada`.** Substitui o `Teclado` e expõe três consultas:
   `apertou(tecla)` (borda de descida neste tick), `segurando(tecla)` e
   `soltou(tecla)`. Dois modos por dentro:
   - **Modo kitty:** na inicialização envia `\x1b[?u` e espera ~100 ms por uma
     resposta `\x1b[?<n>u`. Se vier, ativa o protocolo e o desativa com
     `\x1b[<u` na saída, inclusive no `finally` e no handler de `SIGTERM`. Os
     eventos chegam como `CSI código;mods:tipo u` (tipo 1 = apertou,
     2 = repetição, 3 = soltou). As setas chegam como `CSI 1;mods:tipo A/B/C/D`.
   - **Modo fallback:** sem resposta, a tecla conta como segurada até 150 ms
     depois do último byte recebido. É impreciso, por isso os jogos da primeira
     leva não dependem de segurar.

   Um mapa de ações (`"pular": {" ", "w", "↑"}`) separa teclas de intenção, e
   os jogos só perguntam por ações.

4. **Laço com passo fixo.** A lógica roda a 30 Hz com acumulador e o render na
   taxa que der:

   ```python
   PASSO = 1 / 30
   acum, antes = 0.0, time.monotonic()
   while rodando:
       agora = time.monotonic()
       acum += min(agora - antes, 0.25)   # evita espiral após travada
       antes = agora
       entrada.ler()
       while acum >= PASSO:
           jogo.atualizar(PASSO, entrada)
           entrada.fim_do_tick()          # limpa apertou/soltou
           acum -= PASSO
       jogo.desenhar(tela); tela.render()
       time.sleep(max(0, 1/30 - (time.monotonic() - agora)))
   ```

5. **Mundo e câmera.** A física fica em unidades de mundo com altura fixa (por
   exemplo, o chão sempre a 80% de uma tela lógica de 48 px de altura,
   escalada). Um objeto `Camera(x, y, tremor)` converte mundo→tela. O tamanho
   do terminal muda quanto se vê à frente, não a dificuldade. Abaixo de 80×24,
   mostrar uma tela "aumente o terminal" em vez de quebrar.

6. **Utilitários.**
   - `colide(a, b)`: AABB com caixas um pouco menores que o sprite ("passou
     raspando, que bom").
   - `Particulas`: pool reaproveitável com vida, gravidade e cor.
   - `Recordes`: json em `$XDG_DATA_HOME/termboy/recordes.json` (padrão
     `~/.local/share`), gravando num `.tmp` e renomeando com `os.replace` para
     não corromper.
   - Cada jogo usa um `random.Random(semente)` próprio, nunca o global, o que
     permite replays determinísticos (usados na Fase 5).

**Teste da fase:** as aberturas continuam com o mesmo hash da Fase 0 usando o
render novo, mais uma demo mínima: um quadrado que pula com espaço.

## Fase 2: estrutura dos jogos

Classe base com o ciclo de vida:

```python
class Jogo:
    nome = ""; abertura = ""          # abertura vira tela de título
    def iniciar(self, semente): ...
    def atualizar(self, dt, ent): ... # retorna None ou "fim"
    def desenhar(self, tela): ...
    def pontos(self): ...
```

O registro `JOGOS` fica paralelo a `ABERTURAS`. O controlador geral é uma
máquina de estados:

```
ABERTURA ──start──▶ JOGANDO ──p──▶ PAUSA
    ▲                  │
    └── RECORDE ◀── FIM (game over, 2 s de "CONTINUE?")
```

Na abertura, o `rodape()` já desenha PRESS START, e agora ele passa a valer de
verdade. Se a abertura terminar sem ninguém apertar, ela recomeça (modo
atração). O HUD usa a fonte 5×5 para a pontuação e o `texto()` para dicas de
teclas.

Na CLI, `termboy jogar [nome]` entra no modo jogo e `termboy -l` lista
aberturas e jogos. O comportamento padrão (só aberturas) não muda, então quem
usa o termboy num painel não percebe diferença.

## Fase 3: primeiro jogo, Pulo do Gato (corredor)

Usa um botão só, por isso vem primeiro.

**Física do pulo.**
- *Coyote time*: dá para pular até ~0,1 s depois de sair da beirada.
- *Buffer de pulo*: um aperto ~0,1 s antes de tocar o chão conta.
- *Pulo variável*: no modo kitty, soltar cedo corta a velocidade vertical pela
  metade; no fallback, todo pulo tem altura fixa.
- Gravidade maior na descida que na subida, para o pulo não parecer flutuante.

**Geração de fase.** Pedaços pré-desenhados ("buraco curto", "caixa dupla",
"plataforma flutuante" etc.), cada um com dificuldade e largura. O gerador
escolhe pedaços pela dificuldade atual e garante uma distância mínima calculada
a partir do alcance horizontal do pulo na velocidade atual. Isso assegura que
tudo seja passável, e dá para testar: simular o gato com pulo perfeito por
10 mil metros com várias sementes e verificar que ele nunca morre.

**Progressão.** A velocidade sobe aos poucos, e a cada 500 m o céu muda de hora
(dia → pôr do sol → noite com estrelas), com `ceu()` e as paletas existentes.
Itens colecionáveis originais, como novelos de lã, dão pontos.

**Capricho.** Poeira ao pousar, *squash & stretch* no sprite (um quadro
achatado no pouso, um esticado no pulo), tremor de câmera e `flash()` ao
morrer, parallax das montanhas e nuvens existentes.

**Teste da fase:** o de alcançabilidade acima, mais um replay gravado tocando
de forma determinística.

## Fase 4: segundo jogo, Tocha Eterna (roguelike)

Por ser por turnos, funciona igual em qualquer terminal.

**Mapa.** Geração em grade com BSP (divide a área, põe uma sala em cada folha,
liga com corredores), com escada para o próximo andar. Cada célula da grade
vira um bloco de, digamos, 4×4 px desenhado com `Spr`.

**Mecânica central: a tocha.** O raio de visão depende do combustível, que cai
a cada passo. Óleo encontrado no chão recarrega. Quando a tocha apaga, as
paredes já exploradas continuam visíveis em tom escuro, mas os inimigos não. O
`brilho()` desenha a luz, e o campo de visão sai de um raycast simples ou de
shadowcasting.

**Inimigos e combate.** Uns três tipos originais com comportamentos distintos
(um que persegue, um que foge da luz, um que só se mexe a cada dois turnos).
Combate por esbarrão, como nos roguelikes clássicos. Transições entre turnos
animadas com interpolação de ~0,1 s, para não parecer teletransporte.

**Testes:** todo andar gerado é conexo (flood fill da entrada alcança a
escada), e a mesma semente gera o mesmo andar.

## Fase 5: mais jogos e polimento

- **Turbo Asfalto:** 3 faixas com troca por toque, reaproveitando a pista
  pseudo-3D.
- **Astro Vértice:** shmup vertical com movimento em grade de 5 colunas.

Os dois são menores, porque o motor já estará pronto.

O `tools/gerar_gifs.py` passa a gerar GIFs dos jogos tocando replays gravados:
uma lista de `(tick, ação)` mais a semente, que o passo fixo e o RNG próprio
tornam determinísticos. O README ganha uma seção de controles, uma tabela de
compatibilidade de terminais (com e sem eventos de soltar tecla) e os GIFs. No
painel, um atalho de layout ou um segundo alias (`painel-jogo`) abre o termboy
em modo jogo numa aba.

## Ordem e riscos

Ordem recomendada: 0 → 1 → 2 → 3, publicar como versão nova, depois 4 e 5.

- **Modo kitty dentro do zellij**, que tem seu próprio tratamento de teclado.
  Testar logo no começo da Fase 1, antes de construir em cima.
- **Tamanho do arquivo único.** Com quatro jogos ele cresce bastante. Seções
  bem marcadas com comentários (`# ═══ MOTOR`, `# ═══ JOGOS ═══ Pulo do Gato`)
  mantêm a navegação viável.

---

## Revisão contra o código

Feita na Fase 0, lendo o `termboy` (1338 linhas, commit `ae91fd0`). Cada item
diz o que o plano assume, o que o código tem e o ajuste proposto.

### Bloqueantes ou que mudam o escopo

1. **Não existem aberturas "Pulo do Gato" nem "Tocha Eterna".** `ABERTURAS` tem
   só `elementra`, `turbo`, `astro` e `reino`. Há `docs/gato.gif`,
   `docs/tocha.gif` e `docs/neon.gif` no commit "Add images", mas nenhum código
   que os gere. Na Fase 3 não há sprite de gato nem cenário de corredor para
   reaproveitar, e "abertura vira tela de título" não tem abertura de origem.
   **Ajuste:** escrever cada uma dessas aberturas como primeiro passo da sua
   fase (ou recuperar o código, se ele existir em outro lugar), ou começar a
   Fase 3 por um jogo baseado numa abertura que já existe.

2. **O render por diferença sozinho não leva a 20–30 FPS em terminal grande.**
   Medido em 200×60: o desenho do quadro custa 35–110 ms (turbo e astro
   chegam a ~100 ms), e o `render()` só 4–10 ms. Em 80×24 o desenho fica em
   10–55 ms. O gargalo é o desenho pixel a pixel em Python, não a saída.
   **Ajuste:** o diff continua valendo (menos bytes, sem cintilação no
   zellij), mas o ganho de FPS exige cortar custo de desenho: cachear camadas
   estáticas (céu, montanhas, nebulosa já é cacheada), usar `retangulo` por
   linha em vez de `ponto`, evitar `misturar` por pixel em `flash()` e
   `brilho()` grandes. Os jogos devem ter orçamento de quadro medido desde o
   início, e o laço precisa funcionar bem a 15 FPS de render.

3. **A `Tela` é recriada a cada quadro.** `quadro()` cria uma `Tela` nova e
   `render()` devolve uma string, sem estado entre quadros. O "último quadro"
   do diff não pode morar na `Tela`. **Ajuste:** criar um objeto `Saida`
   (dono do terminal: último quadro, `forcar`, tamanho atual) que recebe a
   `Tela` e escreve só a diferença. A `Tela` continua descartável, o que
   mantém `quadro()` e o `tools/gerar_gifs.py` funcionando sem mudança.

4. **A célula não é só `(cor_cima, cor_baixo)`.** O `render()` sobrepõe texto
   (`tela.texto`) e, nessas células, o caractere é uma letra com cor de frente
   = cor do texto e fundo = pixel de cima. **Ajuste:** a célula guardada para
   o diff é `(caractere, frente, fundo)`.

### Divergências de nomes e assinaturas

5. **`SourceFileLoader(...).load_module()` não existe mais** (removido no
   Python 3.12; aqui roda 3.14). Os testes usam `spec_from_loader` +
   `exec_module`, igual ao `tools/gerar_gifs.py` (em `tests/apoio.py`).

6. **`Tela(estilo, tamanho=None)`**: o estilo é obrigatório e `tamanho` é
   `(cols, linhas)` de caracteres; os pixels são `W = cols`, `H = linhas * 2`.
   80×24 dá 80×48 px, o que bate com a "tela lógica de 48 px" da Fase 1.

7. **O que existe para teclado é `Teclado`**, um context manager com `ler()` que
   devolve até 16 bytes crus. É ele que a `Entrada` substitui. `tocar()` usa
   `time.time()`; o laço novo deve usar `time.monotonic()`.

8. **`tela.texto(linha, s, cor)` só centraliza**, não tem coluna. O HUD
   (pontos à esquerda, dicas à direita) precisa de um parâmetro opcional de
   alinhamento ou coluna.

9. **A fonte 5×5 só tem A–Z maiúsculas, 0–9, `!`, `-` e espaço.** Não tem `:`,
   `/`, `x` minúsculo nem acentos (por isso o título é "VERTICE", sem acento).
   O HUD em fonte grande precisa de glifos novos ou de textos sem esses
   caracteres. Detalhe: o glifo `-` tem 23 caracteres em vez de 25 (o
   `ljust` corrige).

10. **Não há sistema de partículas para extrair.** Os efeitos (`brasas`,
    `explosao`, estrelas, faíscas) são funções puras de `t` com `_hash`, sem
    estado. `Particulas` é código novo. As aberturas devem continuar sem
    estado, para o teste de hash e o `gerar_gifs.py` seguirem funcionando.

11. **`Spr` não tem cache nem transformações.** O cache é `functools.lru_cache`
    nas funções que montam cada sprite (`fofolume(h, piscando)`, `carro(w, cor)`
    etc.). *Squash & stretch* vira um parâmetro a mais nessas funções (ou uma
    função `escalar(spr, sx, sy)` cacheada), não um recurso do `Spr`.

12. **`brilho()` só clareia** (mistura em direção a uma cor). A tocha da Fase 4
    precisa do contrário: escurecer tudo fora do raio. **Ajuste:** um método
    novo `Tela.escuridao(cx, cy, raio)` (ou máscara de luz), com o `brilho()`
    por cima para o halo.

13. **CLI:** `abertura` é um posicional com `choices` fixos, então
    `termboy jogar gato` hoje falha no argparse. **Ajuste:** tratar `jogar`
    como subcomando (`add_subparsers`) ou checar `sys.argv[1] == "jogar"`
    antes do parser atual, mantendo `termboy turbo` como está.

14. **O painel e o alias `painel-jogo` não estão neste repositório.** O README
    só tem um trecho KDL de exemplo para o zellij. A mudança do painel é nos
    dotfiles, fora daqui; aqui só cabe atualizar o exemplo no README.

### Ajustes técnicos no próprio plano

15. **Flags do protocolo kitty.** Com `>3u` (desambiguar + tipos de evento), as
    teclas de texto sem modificador ainda chegam como texto puro ao apertar,
    mas a soltura chega como `CSI ... :3u`. O parser fica misto. **Ajuste:**
    usar `>11u` (1 + 2 + 8, "todas as teclas como escape"), assim todo evento
    chega como `CSI u` e o parser fica uniforme.

16. **Fallback de 150 ms.** O atraso até a primeira repetição automática do
    teclado costuma ficar entre 250 e 600 ms, então segurar uma tecla aparece
    como "apertou, soltou, (pausa), apertou de novo...". O plano já evita
    depender de segurar no fallback; só não dá para usar `segurando()` nem
    para movimento contínuo nesse modo.

17. **tmux.** Além do zellij, o tmux não repassa eventos de soltar tecla (o
    `extended-keys` dele não inclui tipos de evento). Vale entrar na tabela de
    compatibilidade da Fase 5.

18. **Resize hoje "funciona por acidente":** como `quadro()` lê o tamanho do
    terminal a cada quadro e redesenha tudo, o resize já se ajusta. Com o
    diff, isso deixa de valer e o `SIGWINCH` passa a ser obrigatório, junto
    com um `\x1b[2J` no redesenho forçado (ao encolher, sobra lixo nas bordas).

### Sobre o teste de não-regressão (Fase 0, como ficou)

- Em vez de hashear a string do `render()`, o teste passa a saída por um
  terminal falso (`tests/apoio.py`) e hasheia a grade de células. Isso porque
  o render por diferença muda os bytes emitidos sem mudar o que aparece na
  tela; um hash da string quebraria por design na Fase 1. Na Fase 1, o teste
  aplica o quadro forçado e depois um quadro por diferença sobre o mesmo
  terminal falso, e compara as grades.
- Cobre as 4 aberturas × 3 instantes (1,5 s, 5 s e 13,5 s, ou seja, cena
  inicial, ação e título) × 3 estilos em 80×24, mais GBA em 123×37 (tamanho
  ímpar, para pegar arredondamentos). São 48 quadros, em ~1,5 s.
- As referências ficam em `tests/referencia.json`. Depois de uma mudança
  visual intencional: `TERMBOY_REGRAVAR=1 python3 -m unittest tests.test_aberturas`.
- Limitação: o resultado depende do `libm` da máquina (`sin`, `sqrt`), então
  pode divergir em outra plataforma. Se isso acontecer, regravar localmente
  antes de mexer no render.

---

## Como ficou

As cinco fases foram feitas em sequência numa sessão, no branch `jogavel`. Testes:
`python3 -m unittest discover -s tests -v` (53 testes, ~45 s).

### Fase 1: motor

- **Render por diferença:** `Tela.celulas()` monta a grade `(caractere, frente,
  fundo)`; `emitir(grade, anterior)` gera só as sequências que mudaram (buracos
  de até 3 células iguais entram na sequência, porque reposicionar o cursor custa
  mais). O objeto `Saida` guarda o quadro anterior e redesenha tudo com `\x1b[2J`
  na primeira vez, ao mudar de tamanho ou após `forcar()`. `Tela.render()`
  continua devolvendo o quadro inteiro, então `quadro()` e `gerar_gifs.py` não
  mudaram. Bytes por quadro caíram de 3 a 15 vezes.
- **Desempenho:** além do diff, `conv()` ganhou cache, `lerp_cor()` deixou de
  usar gerador, o degradê do `ceu()` é cacheado e `brilho()`, `flash()` e as
  nebulosas misturam cores sem chamadas intermediárias. Tudo com saída idêntica
  (os hashes da Fase 0 não mudaram). Aberturas subiram de 15 para 24 FPS; em
  80×24 todos os jogos desenham em menos de 10 ms, em 200×60 entre 19 e 43 ms.
- **Resize:** `SIGWINCH` só marca `estado["redimensionou"]`; o laço chama
  `Saida.forcar()`. A classe `Terminal` cuida de tela alternativa, cursor,
  teclado, `SIGWINCH` e `SIGTERM`, e desfaz tudo na saída.
- **Entrada:** `ler_teclas()` decodifica bytes comuns e eventos do kitty;
  `Entrada` expõe `apertou(acao, repetir=False)`, `segurando`, `soltou`, `algo()`
  e `injetar()` (replays e testes). A detecção manda `\x1b[?u\x1b[c`: se o DA1
  chega sem a resposta do kitty, não há suporte, sem esperar timeout. Ativa com
  `\x1b[>11u` (todas as teclas como escape, o parser fica uniforme) e desativa
  com `\x1b[<u` no `__exit__`, que roda também no `finally` e no `SIGTERM`.
  Com o kitty, Ctrl+C chega como tecla (`ctrl+c`) e também sai. O modo das
  aberturas não liga o kitty, para não mudar nada no painel.
- **`termboy --teclado`:** diagnóstico que mostra o modo detectado e os eventos.
  O teste no pty finge um terminal kitty e um sem kitty; o zellij real ainda
  precisa ser conferido à mão.
- **Mundo:** `Camera` com `escala = min(H/48, W/64)`, ou seja, terminal estreito
  não esconde o que vem pela frente. `colide()` com folga de 15%, `Particulas`
  (pool), `Recordes` (top 5 por jogo, `.tmp` + `os.replace`), `Laco` (passo fixo
  de 30 Hz com acumulador limitado a 0,25 s).
- **Demo:** `python3 tests/demo_pulo.py` (o quadrado que pula).

### Fase 2: estrutura

- `Jogo`, `JOGOS` e `Fliperama` (máquina de estados com modo atração; `tab`
  troca de jogo na tela de título; abaixo de 80×24 o jogo pausa e mostra
  "AUMENTE O TERMINAL").
- CLI: `termboy jogar [nome] [-e estilo] [--semente N] [--gravar ARQ]
  [--replay ARQ]`. `termboy` sem `jogar` continua igual.
- Replay: `{"jogo", "semente", "modo", "ticks", "pontos", "eventos":
  [[tick, tecla, tipo], ...]}`. O `modo` entra porque o pulo variável depende
  dele. `replay(dados)` devolve o jogo a cada tick.
- A fonte 5×5 ganhou `:`, `.`, `+`, `/` e `?`; `texto()` ganhou `coluna`.

### Fase 3: Pulo do Gato

- Abertura nova `gato` (amanhecer, o gato Pipoca correndo entre buracos e novelos).
- Física em `Gato` (só números, compartilhada com o bot): coyote 0,1 s, buffer
  0,1 s, pulo variável só quando a entrada não é fallback, gravidade 270/440.
- `Fase` gera 8 pedaços. Cada um devolve `(largura, sobra)`: sobra é o quanto o
  pulo forçado passa do fim do pedaço (por exemplo, pular de cima de uma caixa
  alta). Sem isso, o teste de alcançabilidade achava trechos impossíveis
  (plataforma seguida de caixa alta).
- O teste de alcançabilidade usa um bot de busca em profundidade com pulo de
  altura fixa (o pior caso) e horizonte de 3 s: 4 sementes × 10 mil metros nos
  testes, 20 sementes conferidas à mão.
- 1 m = 4 unidades do mundo; a velocidade sobe de 34 a 66 u/s ao longo de ~6 km.

### Fase 4: Tocha Eterna

- Abertura nova `tocha` (a tocha acende, o mago Nox, o baú e o cristal).
- `Andar`: BSP em 40×28, salas ligadas por corredores em L, escada na sala mais
  longe. Visão por raycast de Bresenham. Ladrilhos pré-iluminados em 9 níveis,
  cacheados e copiados por fatia (rápido); o já explorado fica azulado e escuro.
- Inimigos: gosma (persegue), vulto (foge da luz, ataca no escuro), pedrusco
  (anda a cada dois turnos). Esbarrão ataca. Movimento interpolado em 0,1 s.
- Equilíbrio inicial: 6 de vida, óleo gasta 0,5 por turno, +40 por frasco, um
  coração por andar.

### Fase 5

- **Turbo Asfalto:** 3 faixas sobre a `turbo_pista()` existente; rivais a meia
  velocidade, fileiras de 1 ou 2 carros com pelo menos 0,95 s entre elas.
- **Astro Vértice:** 5 colunas, nave girada (`girar()`), drones que atiram e
  rochas indestrutíveis (no máximo 3 objetos e 2 rochas por fileira).
- **GIFs:** `tools/gravar_replays.py` grava em `tools/replays/` uma partida de
  cada jogo jogada pelos bots de `tools/bots.py`; `gerar_gifs.py jogos` toca
  esses replays. `gerar_gifs.py` aceita escolher quais GIFs gerar.
- **README:** seção de jogos, controles, compatibilidade de terminais e uma aba
  de jogo no layout do zellij. O alias `painel-jogo` fica nos dotfiles, fora
  deste repositório.

### Pendências e riscos que continuam

- O modo kitty dentro do zellij não foi testado num terminal de verdade (aqui
  não havia zellij).
- A dificuldade foi ajustada só com bots. Vale jogar e calibrar.
- O arquivo `termboy` passou de 1338 para ~3700 linhas. As seções continuam
  marcadas com `# ====`.
