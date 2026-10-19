# termboy

**Aberturas animadas de jogos retrô no seu terminal**, no estilo Game Boy e Game Boy Advance. Rode `termboy` e assista, como um asciiquarium dos portáteis.

![Trailer](docs/trailer.gif)

Tudo é desenhado em tempo real com caracteres coloridos, sem vídeo e sem imagens: um arquivo Python, zero dependências.

## Instalação

Com uma linha:

```bash
mkdir -p ~/.local/bin && curl -fsSL https://raw.githubusercontent.com/Nicolas-Queiroz/termboy/main/termboy -o ~/.local/bin/termboy && chmod +x ~/.local/bin/termboy
```

Ou clonando o repositório:

```bash
git clone https://github.com/Nicolas-Queiroz/termboy.git
cd termboy
bash install.sh
```

Precisa de Python 3 e de um terminal com suporte a *true color* (a maioria dos terminais modernos no Linux e no macOS; no Windows, use o Windows Terminal com WSL).

## Uso

```bash
termboy                # todas as aberturas em sequência aleatória
termboy turbo          # só uma, em loop
termboy -e gb          # no estilo do Game Boy original
termboy -e aleatorio   # estilo sorteado a cada abertura
termboy -u             # toca uma vez e sai
termboy -l             # lista as opções
```

| Tecla | Ação |
|---|---|
| `q` ou `Esc` | sair |
| `espaço` ou `→` | pular para a próxima |
| `e` | trocar o estilo (GB → GBC → GBA) |

Dica: quanto menor a fonte do terminal, mais "pixels" e mais detalhe. Experimente `Ctrl -` algumas vezes antes de rodar.

## As aberturas

| | |
|---|---|
| ![Elementra](docs/elementra.gif) **Elementra** (`elementra`): duas criaturas se enfrentam numa batalha, com estrela cadente, ataque de energia e título no pôr do sol | ![Turbo Asfalto](docs/turbo.gif) **Turbo Asfalto** (`turbo`): largada com semáforo, pista em pseudo-3D, ultrapassagem, nitro e horizonte neon |
| ![Astro Vértice](docs/astro.gif) **Astro Vértice** (`astro`): nave contra drones numa nebulosa, asteroide e um chefe gigante chegando | ![Reino de Cinza](docs/reino.gif) **Reino de Cinza** (`reino`): tempestade sobre o castelo, cavaleiro, dragão cruzando a lua e título em chamas |

![Telas de título](docs/titulos.gif)

## O elenco

Todos os personagens são desenhados por código, com sombreamento no estilo dos sprites de GBA.

![Elenco](docs/elenco.gif)

## Três estilos de cor

![Estilos](docs/estilos.gif)

- `gb`: os quatro tons de verde da tela do Game Boy original
- `gbc`: a paleta limitada do Game Boy Color
- `gba`: cores de 15 bits, como no Game Boy Advance

## Usar num painel

O termboy funciona bem num canto da tela, dentro do tmux ou do zellij. No zellij:

```kdl
pane command="termboy" {
    args "-e" "aleatorio"
}
```

## Criar uma abertura nova

Cada abertura é uma função `minha_abertura(tela, t)` que desenha o quadro do instante `t` (em segundos). O motor oferece:

- `tela.ceu()`, `tela.retangulo()`, `tela.circulo()`, `tela.poligono()`, `tela.brilho()`, `tela.flash()`
- `Spr`: sprites com sombreamento automático (`elipse`, `poligono`, `contorno`)
- `titulo()` e `rodape()`: título em pixel art com contorno e brilho, mais o "PRESS START"

Registre a função no dicionário `ABERTURAS` e gere os GIFs de demonstração:

```bash
pip install pillow
python3 tools/gerar_gifs.py
```

PRs com aberturas novas são bem-vindos!

## Desinstalar

```bash
rm ~/.local/bin/termboy
```

## Licença

[MIT](LICENSE). As aberturas, personagens, nomes e cenários são originais deste projeto.
