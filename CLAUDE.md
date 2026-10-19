# termboy

- Tudo original: nada de personagens, nomes, músicas ou elementos
  reconhecíveis de jogos existentes. Gêneros e estética retrô podem.
- Python puro, um único arquivo (`termboy`), sem dependências.
  `tests/` e `tools/` são só de desenvolvimento.
- Visual caprichado estilo GBA: sombreamento, contorno, parallax,
  partículas, brilhos.
- Comandos de shell: compatíveis com noclobber (`>|` em vez de `>`
  em arquivo existente), sem sudo no meio de blocos.
- Plano da versão jogável: docs/PLANO-JOGAVEL.md
- Testes: `python3 -m unittest discover -s tests -v`
- Replays e GIFs: `python3 tools/gravar_replays.py` (depois de mudar a lógica
  de um jogo) e `python3 tools/gerar_gifs.py [aberturas|titulos|jogos|...]`.
- Mudança visual intencional numa abertura: regrave as referências com
  `TERMBOY_REGRAVAR=1 python3 -m unittest discover -s tests -p test_aberturas.py`
  e confira que só as chaves esperadas mudaram.
