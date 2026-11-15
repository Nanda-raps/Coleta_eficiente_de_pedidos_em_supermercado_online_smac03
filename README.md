# Coleta Eficiente de Pedidos de Supermercado Online

Projeto da disciplina SMAC03 (Grafos, UNIFEI), **Cenário 5**: reduzir o percurso do funcionário que coleta pedidos de supermercado online.

A loja é modelada como um grafo ponderado (corredores, entrada, caixa e prateleiras). O trabalho compara:

- **3 layouts**, que mudam apenas quem ocupa cada prateleira;
- **4 estratégias de coleta**, que mudam apenas a ordem de visita dos itens.

A comparação usa 100 pedidos reais do dataset [Instacart Market Basket Analysis](https://www.kaggle.com/datasets/psparks/instacart-market-basket-analysis) (Kaggle) e mede distância percorrida, tempo estimado de coleta e pedidos atendidos por turno.

## Modelo em resumo

**Grafo físico G₁.** Os vértices são os 134 slots de prateleira, a ENTRADA, o CAIXA e nós de acesso e passagem. Cada aresta pesa o seu comprimento em metros (distância de Manhattan), e a troca de corredor só ocorre pela frente ou pelo fundo da loja. O algoritmo de Dijkstra gera a matriz **D** (136 × 136) de distâncias mínimas, usada para avaliar qualquer rota.

**Rota de um pedido.** ENTRADA → paradas (uma por seção do pedido) → CAIXA. É um caixeiro viajante com origem e destino fixos, e o custo é a soma das distâncias de D.

| Estratégia | Regra |
|---|---|
| `ref` | Ordem do carrinho. É a referência, sem critério. |
| `corr` | Varredura por corredores em ordem crescente, alternando o sentido a cada corredor. |
| `nn` | Vizinho mais próximo, a partir da ENTRADA. |
| `opt` | Rota de custo mínimo. Exata (Held-Karp) até 15 seções; acima disso, 2-opt a partir de `nn` e de `corr`, ficando com a menor. |

| Layout | Origem |
|---|---|
| L0 | Alocação aleatória das seções (referência). |
| L1 | Seções com maior afinidade de compra (Lift) ficam próximas. |
| L2 | Seções mais pedidas ficam nos slots de menor deslocamento entre ENTRADA e CAIXA. |

Os parâmetros do modelo ficam em `src/config.py`, e cada valor indica se vem do documento de modelagem ou se é premissa do grupo.

## Estrutura

```
dados/        entrada do protótipo (ver dados/README.md)
  amostras/     100 pedidos de avaliação, amostra de validação e calibração do n_min
  curados/      tabelas geradas pelo notebook (frequências, coocorrência, catálogo de seções)
  layouts/      layouts L0, L1 e L2 (CSV e figura)
  instacart/    CSVs originais do Kaggle (não versionados)
notebooks/    curadoria dos dados
modelagem/    figura do grafo físico
src/          protótipo
  config.py       parâmetros do modelo
  grafo_fisico.py grafo G1 e matriz D (Dijkstra)
  rotas.py        estratégias ref, corr, nn e opt (Held-Karp e 2-opt)
  carga.py        leitura dos pedidos e conversão de seções em slots
  indicadores.py  tempo, ganho, pedidos por turno e bootstrap
  demo.py         demonstração de um pedido
tests/        testes automatizados de cada módulo
resultados/   gerada pelos scripts (matriz D e, depois, tabelas e figuras)
relatorio/    relatório em LaTeX
slides/       apresentação
```

## Como executar

Requer Python 3 (testado com 3.10). Todos os comandos rodam na **raiz do repositório**.

```
pip install -r requirements.txt
```

### Demonstração de um pedido

```
python src/demo.py                  # pedido 40098 no layout L0
python src/demo.py 40098 L1         # outro layout (L0, L1 ou L2)
python src/demo.py --lista          # lista os 100 pedidos de avaliação
```

Para o pedido escolhido, mostra as paradas, a distância, o tempo estimado e o ganho de cada estratégia, e a ordem de visita:

```
Estrategia                         distancia   tempo    ganho vs ref
ref  (ordem do carrinho)            365.5 m   10.1 min       0%
corr (varredura por corredores)     171.5 m    6.9 min      53%
nn   (vizinho mais proximo)         154.5 m    6.6 min      58%
opt  (rota de custo minimo)         154.5 m    6.6 min      58%  [exata]
```

### Matriz de distâncias

```
python src/grafo_fisico.py          # salva a matriz D em resultados/D.npy
```

### Testes

```
python tests/test_grafo_fisico.py   # distâncias conferidas à mão, simetria, desigualdade triangular
python tests/test_rotas.py          # Held-Karp contra força bruta, 2-opt, varredura por corredores
python tests/test_carga.py          # carga dos 100 pedidos
python tests/test_indicadores.py    # tempo, ganho e bootstrap
```

Cada teste imprime `OK` ao passar. Eles usam só arquivos que estão no repositório (`dados/amostras/` e `dados/curados/`).

## Dados

Os arquivos grandes do Instacart não são versionados: cada integrante baixa os CSVs e os coloca em `dados/instacart/`, e o notebook `notebooks/curadoria_dados_cenario5.ipynb` recria as tabelas curadas. Detalhes e cuidados (por exemplo, qual tabela de coocorrência não usar para gerar L1 e L2) estão em `dados/README.md`.

## Papéis

- **Dev A (Júlia):** grafo físico, matriz D, estratégias de rota e demonstração (`grafo_fisico.py`, `rotas.py`, `demo.py`).
- **Dev B:** carga dos pedidos, indicadores, bootstrap e experimento (`carga.py`, `indicadores.py`, `experimento.py`).

## Pendente

- `src/experimento.py`: executar 3 layouts × 4 estratégias × 100 pedidos e gerar as tabelas e figuras em `resultados/`.
