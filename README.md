# Coleta Eficiente de Pedidos de Supermercado Online

Projeto da disciplina SMAC03 – Grafos (UNIFEI, 2026.2), **Cenário 5**: reduzir o percurso do funcionário que coleta pedidos de supermercado online. A loja é modelada como um grafo ponderado e o percurso de coleta é comparado em **3 layouts × 4 estratégias × 100 pedidos reais** do [Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis), num total de 1.200 rotas.

- Relatório: 
- Slides: 

## Modelagem

- **Grafo físico G₁:** 134 slots de prateleira em 17 corredores, ENTRADA, CAIXA e pontos de passagem, com arestas pesadas pela distância em metros (Manhattan); a troca de corredor só ocorre pela frente ou pelo fundo da loja. O Dijkstra gera a matriz D (136 × 136) usada para medir qualquer rota.
- **Rota de um pedido:** ENTRADA → uma parada por seção do pedido → CAIXA. É um caixeiro viajante com origem e destino fixos, e o custo é a soma das distâncias de D.
- **L0:** seções em posições aleatórias (referência).
- **L1 (grafo multicamadas):** a camada lógica G₂ liga seções compradas juntas (peso = lift) e uma busca local aproxima as seções afins.
- **L2 (grafo único):** as seções mais pedidas ficam nos slots de menor deslocamento entre ENTRADA e CAIXA.

## Estratégias de coleta

| Estratégia | Ordem de visita |
|---|---|
| `ordem_carrinho` | ordem em que o cliente colocou as seções no carrinho (referência) |
| `corredores` | varredura em S: corredores em ordem crescente, alternando o sentido |
| `vizinho` | sempre a seção mais próxima ainda não visitada |
| `custoMin` | rota de custo mínimo: Held-Karp até 15 seções e 2-opt acima disso |

Indicadores: distância (m), tempo T = D/v + 15 s por item + 120 s por pedido (v = 1 m/s), pedidos por turno de 8 h e ganho sobre a ordem do carrinho, com IC de 95% por bootstrap pareado.

## Estrutura

```
src/
  grafo.ipynb         grafo G1, Dijkstra, matriz D, layouts, pedidos e camada G2
  rotas.ipynb         estratégias de coleta (Held-Karp e 2-opt)
  layouts.ipynb       gera L1 (busca local) e L2 (popularidade) e refaz a calibração de n_min
  testes.ipynb        testes do grafo e das rotas e validação da geometria
  experimento.ipynb   1.200 rotas, tabelas, hipóteses e sensibilidade
  demo.ipynb          rota de um pedido em um layout
figuras/
  figuras.ipynb       figuras dos resultados e das rotas (relatório e slides)
  fig1_*, fig2_*, fig3_*, fig4_*  distância, redução entre layouts, ganho por nº de seções e sensibilidade (PNG e PDF)
  rotas_*.png         rotas de um pedido por estratégia e por layout
modelagem/
  gerar_imagens_layouts.py   imagens dos layouts L0, L1 e L2 (salvas em dados/layouts/)
  gerar_grafos_modelagem.py  figuras do grafo multicamadas e do grafo único (salvas em modelagem/)
  *.png                      grafo multicamadas, grafo único e grafo físico
notebooks/
  curadoria_dados_cenario5_final.ipynb   curadoria do Instacart usada pelos notebooks
dados/                ver dados/README.md
  instacart/          CSVs originais do Kaggle (não versionados)
  curados/            catálogo, frequências e coocorrências das seções e dos departamentos, produtos mais pedidos e pedidos do train
  amostras/           100 pedidos de avaliação, 1.000 de validação e calibração de n_min
  layouts/            L0, L1 e L2 (CSV e imagem)
resultados/           tabelas do experimento (CSV)
relatorio/            relatório 
slides/               apresentação 
```


## Como executar

Todos os comandos rodam na **raiz do repositório**.

```
pip install -r requirements.txt
jupyter notebook
```

`grafo.ipynb` e `rotas.ipynb` são carregados pelos demais notebooks com `%run`. Ordem sugerida:

1. `src/layouts.ipynb`: regera L1 e L2 a partir dos dados curados e refaz a calibração de n_min (cerca de 3 min). L0 e as amostras de pedidos vêm da modelagem e são lidos de `dados/`.
2. `src/testes.ipynb`: confere o grafo, as estratégias e a geometria.
3. `src/experimento.ipynb`: roda as 1.200 rotas e salva as tabelas em `resultados/`.
4. `src/demo.ipynb`: mostra a rota de um pedido (troque `PEDIDO` e `LAYOUT`).
5. `figuras/figuras.ipynb`: gera as figuras a partir das tabelas do passo 3.

A curadoria só precisa ser executada para refazer `dados/curados/`. Ela lê os CSVs de `dados/instacart/` e, se não os encontrar, baixa o dataset com o `mlcroissant` (`pip install mlcroissant`).

### Figuras da modelagem

As imagens dos layouts estão em `dados/layouts/`, e as do grafo multicamadas e do grafo único em `relatorio/latex/figs/` (`cenario1_grafo_multicamadas.png` e `cenario2_grafo_unico.png`). Os notebooks não geram essas imagens: elas vêm dos scripts das modeladoras, `gerar_imagens_layouts.py` e `gerar_grafos_modelagem.py`, que estão na pasta `modelagem/`.

## Equipe

| Papel | Integrante |
|---|---|
| Coordenadora | Fernanda Raponi Silva |
| Modeladora A | Jennifer Lopes |
| Modeladora B | Yasmin Araujo Da Silva |
| Desenvolvedora A | Júlia Garcia da Silva |
| Desenvolvedor B | Fábio Lourenço Machado Rodrigues |

O código original foi escrito em módulos `.py` pelos desenvolvedores (branch `develop`) e pelas modeladoras (scripts de figuras e layouts); a coordenadora revisou e reorganizou o protótipo nos notebooks atuais, que reproduzem os mesmos resultados. As imagens dos layouts e dos grafos da modelagem continuam vindo dos scripts de `modelagem/`.
