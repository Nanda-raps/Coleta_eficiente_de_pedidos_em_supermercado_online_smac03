"""Parametros do prototipo (Cenario 5 - coleta de pedidos).

Valores marcados como DOCUMENTO vem do documento de modelagem (secao 3.5).
Valores marcados como PREMISSA nao estao no documento e precisam ser confirmados
pelos modeladores; se mudarem, basta ajustar aqui, o resto do codigo le deste arquivo.
"""
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
COMPRIMENTO_CORREDOR = 20.0     # DOCUMENTO: 20 m por corredor
SLOTS_POR_CORREDOR = 8          # DOCUMENTO: 8 secoes em 15 corredores (2 corredores tem 7)

GEOMETRIA = {
    "espaco_eixos": 4.0,                                         # DOCUMENTO: 4 m entre eixos de corredores adjacentes
    "espaco_slots": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR,   # PREMISSA: 20 m / 8 slots = 2,5 m
    "y_primeiro_slot": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR / 2,  # PREMISSA: centro do 1o slot = 1,25 m
    "h_lateral": 0.0,                                            # PREMISSA calibrada: h_i = 0 reproduz calibracao_n_min.csv
    "y_transversal_frente": 0.0,                                 # PREMISSA: transversal da frente (ENTRADA e CAIXA)
    "y_transversal_fundo": COMPRIMENTO_CORREDOR,                 # PREMISSA: transversal do fundo, no fim do corredor
}

# Rotas
LIMITE_HELD_KARP = 15   # DOCUMENTO (3.2.2): ate 15 secoes distintas a rota otima e exata

# Tempo de coleta (usado em indicadores.py): T(o) = D/v + t_item * |o| + t_fixo
TEMPO = {
    "velocidade": 1.0,      # DOCUMENTO (3.5): v, em m/s
    "t_item": 15.0,         # DOCUMENTO (3.5): segundos por item
    "t_fixo": 120.0,        # DOCUMENTO (3.5): segundos fixos por pedido
    "turno": 28800.0,       # DOCUMENTO (3.5): H, 8 horas em segundos
}

# Bootstrap pareado (usado em indicadores.py)
SEMENTE = 42                # semente fixa de todos os sorteios (plano de divisao: "sementes fixas (42)")
BOOTSTRAP = {
    "repeticoes": 10000,    # PREMISSA: quantas vezes os pedidos sao re-sorteados
    "nivel": 0.95,          # PREMISSA: intervalo de confianca de 95%
}
