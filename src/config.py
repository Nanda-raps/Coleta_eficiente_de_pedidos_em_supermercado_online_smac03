"""Parametros do prototipo (Cenario 5 - coleta de pedidos)."""
from pathlib import Path

# Caminhos
RAIZ = Path(__file__).resolve().parent.parent          # raiz do repositorio
LAYOUTS = {
    "L0": RAIZ / "dados" / "layouts" / "layout_L0.csv",
    "L1": RAIZ / "dados" / "layouts" / "layout_L1_final.csv",
    "L2": RAIZ / "dados" / "layouts" / "layout_L2_final.csv",
}
PASTA_RESULTADOS = RAIZ / "resultados"

# Geometria da loja (metros)
COMPRIMENTO_CORREDOR = 20.0     # 20 m por corredor
SLOTS_POR_CORREDOR = 8          # 8 secoes em 15 corredores (2 corredores tem 7)

GEOMETRIA = {
    "espaco_eixos": 4.0,                                         # 4 m entre eixos de corredores adjacentes
    "espaco_slots": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR,   # 20 m / 8 slots = 2,5 m
    "y_primeiro_slot": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR / 2,   # centro do 1o slot = 1,25 m
    "h_lateral": 0.0,                                            # h_i = 0 reproduz calibracao_n_min.csv
    "y_transversal_frente": 0.0,                                 # transversal da frente (ENTRADA e CAIXA)
    "y_transversal_fundo": COMPRIMENTO_CORREDOR,                 # transversal do fundo, no fim do corredor
}

# Rotas
LIMITE_HELD_KARP = 15   # ate 15 secoes distintas a rota otima e exata

# Tempo de coleta (usado em indicadores.py): T(o) = D/v + t_item * |o| + t_fixo
TEMPO = {
    "velocidade": 1.0,      # v, em m/s
    "t_item": 15.0,         # segundos por item
    "t_fixo": 120.0,        # segundos fixos por pedido
    "turno": 28800.0,       # H, 8 horas em segundos
}

# Bootstrap pareado (usado em indicadores.py)
SEMENTE = 42                # semente fixa de todos os sorteios (plano de divisao: "sementes fixas (42)")
BOOTSTRAP = {
    "repeticoes": 10000,    # quantas vezes os pedidos sao re-sorteados
    "nivel": 0.95,          # intervalo de confianca de 95%
}

# Validacao da geometria (usado em validacao_geometria.py)
# Diferenca maxima aceita, em metros, entre a distancia media recalculada na amostra de validacao
# e a de calibracao_n_min.csv. Premissa: o plano registra diferencas de 0,010 m (L0) e 0,019 m (L1)
# com h_i = 0; a sobra vem, provavelmente, dos pedidos com mais de 15 secoes (sigma_opt heuristica).
TOLERANCIA_VALIDACAO_M = 0.05
