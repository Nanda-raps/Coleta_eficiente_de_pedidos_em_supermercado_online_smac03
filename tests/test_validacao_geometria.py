"""Testes da validacao da geometria (so as pecas; a validacao completa roda em src/validacao_geometria.py).

Rodar na raiz do repositorio:  python tests/test_validacao_geometria.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from grafo_fisico import grafo_padrao, carregar_layout                               # noqa: E402
from rotas import executar                                                           # noqa: E402
from validacao_geometria import (carregar_validacao, custo_validacao,                # noqa: E402
                                 esperado_calibracao, media_opt, montar_tabela)

g = grafo_padrao()
D = g.matriz_D()


def perto(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_pedidos_de_validacao():
    pedidos = carregar_validacao()
    assert len(pedidos) == 1000
    _, mapa = carregar_layout("L0")
    for secoes in pedidos:
        assert len(secoes) >= 1
        assert len(set(secoes)) == len(secoes)                           # sem secao repetida
        assert all(a in mapa for a in secoes)                            # toda secao existe no layout


def test_esperado_vem_do_csv_de_calibracao():
    esperado = esperado_calibracao()
    assert perto(esperado["L0"], 157.234)
    assert perto(esperado["L1"], 144.783)


def test_media_opt_a_mao():
    """Secoes na frente do corredor 1 (x = 0, ENTRADA em (0, 0), CAIXA em (64, 0)).

    Posicao 1 fica em y = 1,25 e posicao 2 em y = 3,75 (h_i = 0). Calculo a mao:
      so a posicao 1:        sobe 1,25 + volta 1,25 + 64 ate o CAIXA = 66,5
      so a posicao 2:        3,75 + 3,75 + 64                          = 71,5
      posicoes 1 e 2 juntas: passa pela 1 na subida e pela 2 no fundo da subida, e volta = 71,5
    """
    _, mapa = carregar_layout("L0")
    aisle_na = {pos: a for a, pos in mapa.items()}
    a1, a2 = aisle_na[(1, 1)], aisle_na[(1, 2)]
    media, heuristicos = media_opt([[a1]], mapa, D, g)
    assert perto(media, 66.5) and heuristicos == 0
    media, _ = media_opt([[a2]], mapa, D, g)
    assert perto(media, 71.5)
    media, heuristicos = media_opt([[a1], [a2], [a1, a2]], mapa, D, g)
    assert perto(media, (66.5 + 71.5 + 71.5) / 3) and heuristicos == 0


def test_media_opt_conta_pedidos_heuristicos():
    _, mapa = carregar_layout("L0")
    todas = list(mapa)
    media, heuristicos = media_opt([todas[:16], todas[:3]], mapa, D, g)   # 16 secoes > limite de 15
    assert heuristicos == 1 and media > 0


def test_custo_validacao_igual_ao_opt_ate_15_e_nunca_menor_acima():
    _, mapa = carregar_layout("L0")
    todas = list(mapa)
    for k in (3, 8, 15):                                                  # exato: igual ao sigma_opt
        slots = [g.indice_slot(*mapa[a]) for a in todas[:k]]
        assert perto(custo_validacao(slots, D, g), executar("opt", slots, D, g)[1])
    for k in (16, 20, 30):                                                # heuristica: sigma_opt tem mais partidas
        slots = [g.indice_slot(*mapa[a]) for a in todas[:k]]
        assert custo_validacao(slots, D, g) >= executar("opt", slots, D, g)[1] - 1e-9


def test_tabela_dentro_e_fora_da_tolerancia():
    obtidas = {"L0": 157.244, "L1": 144.900}
    esperadas = {"L0": 157.234, "L1": 144.783}
    tabela = montar_tabela(obtidas, esperadas, {"L0": 0, "L1": 2}, tolerancia=0.05)
    l0, l1 = tabela.iloc[0], tabela.iloc[1]
    assert l0["layout"] == "L0" and l0["dentro_da_tolerancia"]            # diferenca de 0,010
    assert perto(l0["diferenca_m"], 0.010, 1e-9)
    assert l1["layout"] == "L1" and not l1["dentro_da_tolerancia"]        # diferenca de 0,117
    assert l1["pedidos_heuristicos"] == 2


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("OK", nome)
