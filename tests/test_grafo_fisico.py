"""Testes do grafo fisico e da matriz D.

Rodar na raiz do repositorio:  python tests/test_grafo_fisico.py
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import GEOMETRIA                      # noqa: E402
from grafo_fisico import grafo_padrao             # noqa: E402

g = grafo_padrao()
D = g.matriz_D()
h, y1, dy, eixos = (GEOMETRIA[k] for k in ("h_lateral", "y_primeiro_slot", "espaco_slots", "espaco_eixos"))
y_fundo = GEOMETRIA["y_transversal_fundo"]
perto = lambda a, b: abs(a - b) < 1e-9
y_slot = lambda posicao: y1 + (posicao - 1) * dy


def test_forma_e_propriedades():
    assert g.n_slots == 134 and D.shape == (136, 136)
    assert np.isfinite(D).all()                                   # grafo conexo
    assert np.allclose(D, D.T)
    assert np.allclose(np.diag(D), 0)
    rng = np.random.default_rng(0)
    for _ in range(2000):                                         # desigualdade triangular
        a, b, c = rng.integers(0, 136, 3)
        assert D[a, c] <= D[a, b] + D[b, c] + 1e-9


def test_distancias_conferidas_a_mao():
    s11, s12, s18, s21 = (g.indice_slot(1, 1), g.indice_slot(1, 2), g.indice_slot(1, 8), g.indice_slot(2, 1))
    assert perto(D[g.ENTRADA, g.CAIXA], 16 * eixos)               # 64 m pela transversal da frente
    assert perto(D[g.ENTRADA, s11], y1 + h)                       # 1,25 m com h = 0
    assert perto(D[s11, s12], 2 * h + dy)                         # mesmo corredor: 2,5 m
    assert perto(D[s11, s18], 2 * h + 7 * dy)                     # 17,5 m
    assert perto(D[s11, s21], 2 * h + 2 * y1 + eixos)             # corredor vizinho pela frente: 6,5 m


def test_entrada_e_caixa_nos_extremos():
    # ENTRADA no corredor 1 e CAIXA no corredor 17: cada um alcanca o corredor do outro pela transversal da frente
    s11, s171 = g.indice_slot(1, 1), g.indice_slot(17, 1)
    assert perto(D[g.ENTRADA, s171], 16 * eixos + y1 + h)         # 64 + 1,25 m
    assert perto(D[g.CAIXA, s11], 16 * eixos + y1 + h)


def test_nao_atravessa_prateleira():
    # slots lado a lado (corredores 1 e 2, posicao 4): em linha reta seriam 4 m, mas a troca de
    # corredor so ocorre pela frente (ou pelo fundo): sobe ate a frente, cruza e desce.
    s14, s24 = g.indice_slot(1, 4), g.indice_slot(2, 4)
    pela_frente = 2 * h + 2 * y_slot(4) + eixos                   # 8,75 + 4 + 8,75 = 21,5 m
    pelo_fundo = 2 * h + 2 * (y_fundo - y_slot(4)) + eixos        # 11,25 + 4 + 11,25 = 26,5 m
    assert perto(D[s14, s24], min(pela_frente, pelo_fundo))
    assert D[s14, s24] > eixos + 2 * h                            # nao existe atalho em linha reta


def test_troca_de_corredor_pelo_fundo():
    # no fim do corredor (posicao 8), o caminho mais curto para o corredor vizinho e pelo fundo
    s18, s28 = g.indice_slot(1, 8), g.indice_slot(2, 8)
    pelo_fundo = 2 * h + 2 * (y_fundo - y_slot(8)) + eixos        # 1,25 + 4 + 1,25 = 6,5 m
    assert perto(D[s18, s28], pelo_fundo)


def test_corredores_de_7_slots():
    assert g.n_slots == 15 * 8 + 2 * 7
    assert sum(1 for c in g.slot_corredor if c == 16) == 7 and sum(1 for c in g.slot_corredor if c == 17) == 7


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("OK", nome)
