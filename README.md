# Coleta Eficiente de Pedidos de Supermercado Online (SMAC03 - Grafos, UNIFEI)

Cenário 5: reduzir o percurso do funcionário na coleta de pedidos de supermercado online, modelando a loja como grafo e comparando layouts (L0, L1, L2) e estratégias de coleta (referência, por corredores, vizinho mais próximo, ótima).

Dataset: Instacart Market Basket Analysis (Kaggle).

## Estrutura

- `dados/`: dados curados, layouts e amostras (ver `dados/README.md`)
- `notebooks/`: curadoria dos dados
- `modelagem/`: documento de modelagem e diagramas
- `src/`: protótipo (grafo físico, rotas, indicadores, experimento)
- `tests/`: testes
- `resultados/`: tabelas e figuras geradas
- `relatorio/`: relatório (LaTeX e PDF)
- `slides/`: apresentação

## Como executar

Python 3 com as bibliotecas de `requirements.txt` (`pip install -r requirements.txt`). Todos os comandos rodam na raiz do repositório.

```
python src/grafo_fisico.py        # constroi o grafo fisico e salva a matriz D em resultados/D.npy
python tests/test_grafo_fisico.py # testes do grafo e da matriz D
python tests/test_rotas.py        # testes das estrategias de rota
python tests/test_carga.py        # testes da carga dos 100 pedidos
python tests/test_indicadores.py  # testes dos indicadores e do bootstrap
```

Os testes usam só arquivos que estão no repositório (`dados/amostras/` e `dados/curados/`). O arquivo `dados/amostras/pedidos_avaliacao_carrinho.csv` guarda a ordem do carrinho dos 100 pedidos de avaliação. Os arquivos grandes do Instacart não são versionados (ver `dados/README.md`).

## Papéis

- **Dev A (Júlia):** grafo físico, matriz D, estratégias de rota (`src/grafo_fisico.py`, `src/rotas.py`).
- **Dev B:** carga dos pedidos, indicadores, bootstrap e experimento (`src/carga.py`, `src/indicadores.py`, `src/experimento.py`).
