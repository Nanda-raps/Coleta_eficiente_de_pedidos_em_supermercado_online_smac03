"""Parametros do prototipo (Cenario 5 - coleta de pedidos).

Valores marcados como DOCUMENTO vem do documento de modelagem (secao 3.5).
Valores marcados como PREMISSA nao estao no documento e precisam ser confirmados
pelos modeladores; se mudarem, basta ajustar aqui, o resto do codigo le deste arquivo.
"""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent          # raiz do repositorio
LAYOUTS = {
    "L0": RAIZ / "dados" / "layouts" / "layout_L0.csv",
    "L1": RAIZ / "dados" / "layouts" / "layout_L1_final.csv",
    "L2": RAIZ / "dados" / "layouts" / "layout_L2_final.csv",
}
PASTA_RESULTADOS = RAIZ / "resultados"

GEOMETRIA = {
    "comprimento_corredor": 20.0,   # DOCUMENTO: 20 m por corredor
    "espaco_eixos": 4.0,            # DOCUMENTO: 4 m entre eixos de corredores adjacentes
    "espaco_slots": 2.5,            # PREMISSA: 20 m / 8 slots
    "y_primeiro_slot": 1.25,        # PREMISSA: centro do 1o slot (2,5 m / 2)
    "h_lateral": 0.0,               # PREMISSA calibrada: h_i = 0 reproduz calibracao_n_min.csv
    "y_transversal_frente": 0.0,    # PREMISSA: transversal da frente (ENTRADA e CAIXA)
    "y_transversal_fundo": 20.0,    # PREMISSA: transversal do fundo
}
