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

## Visualizações dos Layouts

As figuras dos layouts (L<sub>0</sub>, L<sub>1</sub> e L<sub>2</sub>) já estão pré-geradas em `dados/layouts/`. Caso deseje reproduzi-las a partir dos arquivos CSV:

1. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```

2. Reproduza o comando:
   ```bash
   python3 modelagem/gerar_imagens_layouts.py  
   ```

## Papéis
