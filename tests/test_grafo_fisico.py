"""Testes do grafo fisico e da matriz D. Rodar na raiz do repositorio: python tests/test_grafo_fisico.py"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import GEOMETRIA                      # noqa: E402
from grafo_fisico import grafo_padrao             # noqa: E402

g = grafo_padrao()
D = g.matriz_D()
h, y1, dy, eixos = (GEOMETRIA[k] for k in ("h_lateral", "y_primeiro_slot", "espaco_slots", "espaco_eixos"))
perto = lambda a, b: abs(a - b) < 1e-9


def test_forma_e_propriedades():
    assert g.n_slots == 134 and D.shape == (136, 136)
    assert np.isfinite(D).all()                                   # grafo conexo
    assert np.allclose(D, D.T)                                    # simetrica
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


def test_corredores_de_7_slots():
    assert g.n_slots == 15 * 8 + 2 * 7                            # 134
    assert sum(1 for c in g.slot_corredor if c == 16) == 7 and sum(1 for c in g.slot_corredor if c == 17) == 7


for nome, f in list(globals().items()):
    if nome.startswith("test_"):
        f()
        print("OK", nome)
