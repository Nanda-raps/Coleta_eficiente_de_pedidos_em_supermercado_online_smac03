# config.py
# Guarda todos os numeros (parametros) do prototipo em um unico lugar.
# Os outros arquivos importam daqui; para mudar algo (ex.: tamanho do corredor),
# basta alterar o valor neste arquivo.
from pathlib import Path

# ---------- Caminhos dos arquivos ----------

# RAIZ e a pasta principal do projeto.
# __file__ e este arquivo (src/config.py); o 1o .parent sobe para src/ e o 2o sobe para a raiz.
RAIZ = Path(__file__).resolve().parent.parent

# CSV de cada layout (L0, L1, L2). Cada CSV diz qual secao fica em qual slot da loja.
LAYOUTS = {
    "L0": RAIZ / "dados" / "layouts" / "layout_L0.csv",
    "L1": RAIZ / "dados" / "layouts" / "layout_L1_final.csv",
    "L2": RAIZ / "dados" / "layouts" / "layout_L2_final.csv",
}

# Pasta onde os resultados gerados (ex.: a matriz D.npy) sao salvos.
PASTA_RESULTADOS = RAIZ / "resultados"

# ---------- Geometria da loja (em metros) ----------

# Cada corredor tem 20 m de comprimento.
COMPRIMENTO_CORREDOR = 20.0

# Cada corredor tem 8 slots (prateleiras); 2 dos 17 corredores tem 7 (os 134 slots no total).
SLOTS_POR_CORREDOR = 8

# Medidas usadas em grafo_fisico.py para calcular as coordenadas (x, y) de cada ponto.
GEOMETRIA = {
    # Distancia em x entre o eixo de um corredor e o do corredor vizinho.
    "espaco_eixos": 4.0,
    # Tamanho da "fatia" de cada slot ao longo do corredor: 20 m / 8 slots = 2,5 m.
    "espaco_slots": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR,
    # Posicao y do slot 1: o ponto fica no CENTRO da primeira fatia (2,5 m / 2 = 1,25 m).
    "y_primeiro_slot": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR / 2,
    # Profundidade lateral h_i: distancia entre o eixo do corredor e a prateleira.
    # Com 0, o slot fica exatamente no eixo e a aresta slot -> acesso pesa 0 m.
    # Mantido em 0 porque assim o resultado reproduz o calibracao_n_min.csv.
    "h_lateral": 0.0,
    # Posicao y da passagem da frente da loja (onde ficam a ENTRADA e a CAIXA).
    "y_transversal_frente": 0.0,
    # Posicao y da passagem do fundo, no fim do corredor (y = 20 m).
    "y_transversal_fundo": COMPRIMENTO_CORREDOR,
}

# ---------- Rotas ----------

# Ate este numero de secoes distintas no pedido, a rota otima e calculada de forma exata
# (Held-Karp). Acima disso, usa-se uma heuristica (vizinho mais proximo + 2-opt).
LIMITE_HELD_KARP = 15

# ---------- Tempo de coleta ----------

# Usado em indicadores.py na formula: T(o) = D/v + t_item * |o| + t_fixo
TEMPO = {
    "velocidade": 1.0,      # v: velocidade do funcionario, em m/s
    "t_item": 15.0,         # tempo para separar cada item, em segundos
    "t_fixo": 120.0,        # tempo fixo por pedido, em segundos
    "turno": 28800.0,       # H: duracao do turno (8 horas), em segundos
}

# ---------- Estatistica ----------

# Semente fixa de todos os sorteios: com ela, rodar de novo da exatamente o mesmo resultado.
SEMENTE = 42

# Bootstrap pareado (usado em indicadores.py).
BOOTSTRAP = {
    "repeticoes": 10000,    # quantas vezes os pedidos sao re-sorteados
    "nivel": 0.95,          # intervalo de confianca de 95%
}

# Validacao da geometria (usado em validacao_geometria.py)
# Diferenca maxima aceita, em metros, entre a distancia media recalculada na amostra de validacao
# e a de calibracao_n_min.csv. Premissa: o plano registra diferencas de 0,010 m (L0) e 0,019 m (L1)
# com h_i = 0; a sobra vem, provavelmente, dos pedidos com mais de 15 secoes (sigma_opt heuristica).
TOLERANCIA_VALIDACAO_M = 0.05

# Analise de sensibilidade (usado em sensibilidade.py): valores testados de cada parametro de tempo.
# As faixas (v de 0,8 a 1,1; t_item de 10 a 20; t_fixo de 60 a 180) vem do documento de modelagem (3.5);
# os passos intermediarios (0,9 m/s; 15 s; 120 s) sao escolha nossa. O caso base e o dicionario TEMPO.
SENSIBILIDADE = {
    "velocidade": (0.8, 0.9, 1.0, 1.1),     # m/s
    "t_item": (10.0, 15.0, 20.0),           # segundos por item
    "t_fixo": (60.0, 120.0, 180.0),         # segundos por pedido
}
