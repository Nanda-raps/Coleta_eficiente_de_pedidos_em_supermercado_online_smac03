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

Os parâmetros do modelo ficam em `src/config.py`, cada um com seu papel e sua unidade comentados.

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
  validacao_geometria.py  confere se o grafo reproduz a calibração dos modeladores
  experimento.py  3 layouts x 4 estratégias x 100 pedidos, com tabelas e verificação das hipóteses
  graficos.py     figuras do experimento (PNG e PDF), a partir das tabelas de resultados/
  sensibilidade.py  análise de sensibilidade dos parâmetros de tempo (tabela e figura)
tests/        testes automatizados de cada módulo
resultados/   gerada pelos scripts (matriz D, validação da geometria, tabelas do experimento e figuras/)
relatorio/    relatório em LaTeX
slides/       apresentação
```

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

### Validação da geometria

```
python src/validacao_geometria.py   # salva resultados/validacao_geometria.csv (~30 s)
```

O documento de modelagem não define o espaço entre slots, o hᵢ nem a posição das transversais; esses valores são premissas do grupo (`src/config.py`). O script recalcula, nos 1.000 pedidos da amostra de validação, a distância média em L0 e em L1 (n_min = 300) e compara com `dados/amostras/calibracao_n_min.csv` (L0 = 157,234 m; L1 = 144,783 m). Termina com erro se a diferença passar de `TOLERANCIA_VALIDACAO_M` (0,05 m).

Nos pedidos com mais de 15 seções, a validação usa só vizinho mais próximo + 2-opt (e não o `opt` completo), que é o método que reproduz a calibração dos modeladores. Isso mede a geometria sem misturar com a heurística.

### Experimento

```
python src/experimento.py           # grava as tabelas em resultados/ (~12 s)
```

Executa os 100 pedidos de avaliação em cada layout (L0, L1, L2) com cada estratégia (`ref`, `corr`, `nn`, `opt`), com a mesma matriz D. Os intervalos de confiança (95%) são por bootstrap pareado, com semente fixa (42). Arquivos gerados em `resultados/`:

| Arquivo | Conteúdo |
|---|---|
| `resultados_por_pedido.csv` | uma linha por pedido, layout e estratégia (1.200 linhas): distância, tempo, ganho, nº de seções e de corredores |
| `tabela_distancia.csv` | média, mediana e IC da distância, por layout e estratégia |
| `tabela_reducao_layouts.csv` | redução de L1 e L2 contra L0, e de L1 contra L2, por estratégia |
| `tabela_ganho.csv` | ganho de `corr`, `nn` e `opt` contra `ref`, por layout |
| `tabela_ganho_faixa_secoes.csv` | ganho por faixa de seções distintas do pedido |
| `tabela_ganho_faixa_corredores.csv` | ganho por faixa de corredores distintos visitados |
| `tabela_tempo_turno.csv` | tempo médio de coleta e pedidos por turno |
| `tabela_equivalencias.csv` | em quantos pedidos estratégias distintas dão a mesma distância |
| `verificacao_hipoteses.csv` | H1 a H4, cada critério com o resultado (confirmada, contrariada, inconclusiva ou mista) |

Em 8 dos 100 pedidos (mais de 15 seções) o `opt` é heurística, não exato; a coluna `pedido_heuristico` os marca. O ganho contra `ref` é relativo à `ref` do próprio layout, então não serve para comparar o desempenho absoluto entre layouts.

### Figuras

```
python src/graficos.py              # grava resultados/figuras/ (PNG e PDF, ~2 s)
```

Só lê os CSVs de `resultados/`, então rode antes `python src/experimento.py`. Gera três figuras, cada uma em PNG (200 dpi) e em PDF (vetorial, para o LaTeX):

| Figura | Conteúdo |
|---|---|
| `fig1_distancia_boxplot` | distância por pedido em cada layout, um painel por estratégia (boxplots, com a média marcada) |
| `fig2_reducao_layouts` | redução de L1 e L2 contra L0 e de L1 contra L2, com IC de 95% (H1 e H2) |
| `fig3_ganho_faixa_secoes` | ganho contra `ref` por faixa de seções do pedido, um painel por layout (H3) |

As cores foram validadas para daltonismo, e nenhuma figura depende só da cor: os layouts têm o nome no eixo e as estratégias têm marcadores diferentes. Os testes conferem as contas e a geração dos arquivos, mas não a aparência: abra as imagens para conferir.

### Sensibilidade

```
python src/sensibilidade.py         # grava a tabela e a figura 4 (~2 s)
```

Os valores de tempo (velocidade, tempo por item e tempo fixo) são premissas do grupo, não medidas. O script recalcula o tempo e os pedidos por turno em 10 cenários e confere se a ordem dos 12 casos (layout × estratégia) muda:

- o **caso base** (`TEMPO`, em `src/config.py`);
- **um parâmetro de cada vez**: velocidade de 0,8 a 1,1 m/s, tempo por item de 10 a 20 s e tempo fixo de 60 a 180 s (valores em `SENSIBILIDADE`, em `src/config.py`);
- um cenário **pessimista** (tudo no pior) e um **otimista** (tudo no melhor).

Não refaz rotas: lê `resultados/resultados_por_pedido.csv` (rode antes o experimento). Saídas:

- `resultados/tabela_sensibilidade.csv`: 120 linhas (10 cenários × 12 casos). A coluna `ranking_igual_ao_base` diz se a ordem dos casos se manteve naquele cenário.
- `resultados/figuras/fig4_sensibilidade_pedidos_turno` (PNG e PDF): para cada caso, uma barra do cenário pessimista ao otimista e um ponto no caso base.

O ranking é comparado **dentro de cada cenário**: as barras de casos diferentes podem se sobrepor sem que isso signifique que a ordem mudou. Como o tempo é D/v mais termos que dependem só do pedido, a ordem não muda; o que muda é o número de pedidos por turno. A sensibilidade do `n_min` é a tabela `dados/amostras/calibracao_n_min.csv`, feita pelos modeladores.

### Testes

```
python tests/test_grafo_fisico.py   # distâncias conferidas à mão, simetria, desigualdade triangular
python tests/test_rotas.py          # Held-Karp contra força bruta, 2-opt, varredura por corredores
python tests/test_carga.py          # carga dos 100 pedidos
python tests/test_indicadores.py    # tempo, ganho e bootstrap
python tests/test_validacao_geometria.py  # validação da geometria (peças e contas à mão)
python tests/test_experimento.py    # experimento e tabelas, com dados sintéticos e reais (~20 s)
python tests/test_graficos.py       # dados das figuras e geração de PNG e PDF
python tests/test_sensibilidade.py  # cenários, contas à mão e detecção de mudança no ranking
```

Cada teste imprime `OK` ao passar. Eles usam só arquivos que estão no repositório (`dados/amostras/` e `dados/curados/`).

## Dados

Os arquivos grandes do Instacart não são versionados: cada integrante baixa os CSVs e os coloca em `dados/instacart/`, e o notebook `notebooks/curadoria_dados_cenario5.ipynb` recria as tabelas curadas. Detalhes e cuidados (por exemplo, qual tabela de coocorrência não usar para gerar L1 e L2) estão em `dados/README.md`.


