# Todos os parametros do prototipo ficam aqui; os outros arquivos importam deste.

from pathlib import Path


# Pasta raiz do projeto (src/config.py -> sobe duas pastas).
RAIZ = Path(__file__).resolve().parent.parent

# CSV de cada layout: diz em que corredor e posicao fica cada secao.
LAYOUTS = {
    "L0": RAIZ / "dados" / "layouts" / "layout_L0.csv",
    "L1": RAIZ / "dados" / "layouts" / "layout_L1_final.csv",
    "L2": RAIZ / "dados" / "layouts" / "layout_L2_final.csv",
}

# Pasta onde os scripts gravam tabelas, figuras e a matriz D.
PASTA_RESULTADOS = RAIZ / "resultados"


# Geometria da loja, em metros.
# Cada corredor tem 20 m e 8 slots (2 dos 17 corredores tem 7: 134 slots no total).
COMPRIMENTO_CORREDOR = 20.0

SLOTS_POR_CORREDOR = 8

# Medidas usadas em grafo_fisico.py para calcular as coordenadas (x, y) dos pontos.
GEOMETRIA = {
    # x entre o eixo de um corredor e o do corredor vizinho.
    "espaco_eixos": 4.0,
    # Fatia de cada slot ao longo do corredor: 20 m / 8 = 2,5 m.
    "espaco_slots": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR,
    # y do slot 1: o centro da primeira fatia (2,5 m / 2 = 1,25 m).
    "y_primeiro_slot": COMPRIMENTO_CORREDOR / SLOTS_POR_CORREDOR / 2,
    # Profundidade h_i entre o eixo do corredor e a prateleira.
    # Com 0, o slot fica no eixo e a aresta slot-acesso pesa 0 m (valor que reproduz calibracao_n_min.csv).
    "h_lateral": 0.0,
    # y da passagem da frente, onde ficam ENTRADA e CAIXA.
    "y_transversal_frente": 0.0,
    # y da passagem do fundo (fim do corredor).
    "y_transversal_fundo": COMPRIMENTO_CORREDOR,
}


# Ate 15 secoes distintas no pedido, a rota otima e exata (Held-Karp); acima disso, heuristica.
LIMITE_HELD_KARP = 15


# Tempo de coleta (indicadores.py): T = D/v + t_item * itens + t_fixo.
# velocidade em m/s; t_item e t_fixo em segundos; turno = duracao H (8 h) em segundos.
TEMPO = {
    "velocidade": 1.0,
    "t_item": 15.0,
    "t_fixo": 120.0,
    "turno": 28800.0,
}


# Semente fixa de todos os sorteios: rodar de novo da exatamente o mesmo resultado.
SEMENTE = 42

# Bootstrap pareado (indicadores.py): 10.000 re-sorteios e intervalo de confianca de 95%.
BOOTSTRAP = {
    "repeticoes": 10000,
    "nivel": 0.95,
}

# Diferenca maxima aceita, em metros, entre a distancia recalculada em validacao_geometria.py
# e a de calibracao_n_min.csv.
TOLERANCIA_VALIDACAO_M = 0.05

# Valores de tempo testados em sensibilidade.py. As faixas vem do documento de modelagem (3.5);
# o caso base e o dicionario TEMPO.
SENSIBILIDADE = {
    "velocidade": (0.8, 0.9, 1.0, 1.1),
    "t_item": (10.0, 15.0, 20.0),
    "t_fixo": (60.0, 120.0, 180.0),
}
