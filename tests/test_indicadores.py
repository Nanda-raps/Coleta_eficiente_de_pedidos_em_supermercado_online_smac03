"""Testes dos indicadores. Rodar na raiz do repositorio: python tests/test_indicadores.py

Usa so arquivos do repositorio (dados/amostras e dados/curados).
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from carga import carregar_pedidos_avaliacao, slots_do_pedido                                   # noqa: E402
from grafo_fisico import grafo_padrao, carregar_layout                                          # noqa: E402
from indicadores import (bootstrap_ic, contar_equivalentes, ganho, ganho_medio, n_corredores,   # noqa: E402
                         pares_equivalentes, pedidos_por_turno, reducao_media, resumo, tempo_coleta)
from rotas import ESTRATEGIAS, executar                                                        # noqa: E402

g = grafo_padrao()
D = g.matriz_D()
pedidos = carregar_pedidos_avaliacao()
perto = lambda a, b: abs(a - b) < 1e-9


def custos_do_pedido(secoes, mapa):
    """Distancia de cada estrategia para um pedido (secoes na ordem do carrinho) em um layout."""
    slots = slots_do_pedido(secoes, mapa, g)
    return {e: executar(e, slots, D, g)[1] for e in ESTRATEGIAS}


# ---- contas feitas a mao ------------------------------------------------------------
def test_tempo_a_mao():
    assert perto(tempo_coleta(100, 10), 370)                     # 100/1 + 15*10 + 120
    assert perto(tempo_coleta(154.5, 8), 394.5)                  # 154,5 + 120 + 120
    assert perto(tempo_coleta(64, 1), 64 + 15 + 120)             # menor rota possivel, 1 item


def test_tempo_com_outros_parametros():
    outro = {"velocidade": 0.5, "t_item": 10.0, "t_fixo": 60.0, "turno": 3600.0}
    assert perto(tempo_coleta(100, 10, outro), 200 + 100 + 60)   # 100/0,5 + 10*10 + 60


def test_pedidos_por_turno_a_mao():
    assert perto(pedidos_por_turno([370, 370]), 28800 / 370)
    assert perto(pedidos_por_turno([300, 900]), 48.0)            # media 600 s: 28800 / 600
    # NAO e a media de H/T de cada pedido: (96 + 32) / 2 = 64
    assert not perto(pedidos_por_turno([300, 900]), 64.0)


def test_ganho_a_mao():
    assert perto(ganho(100, 80), 0.20)
    assert perto(ganho(100, 100), 0.0)
    assert abs(ganho(365.5, 154.5) - 211 / 365.5) < 1e-12       # 0,5773


def test_n_corredores_a_mao():
    assert n_corredores([g.indice_slot(1, 1)], g) == 1
    assert n_corredores([g.indice_slot(1, 1), g.indice_slot(1, 5)], g) == 1             # mesmo corredor
    assert n_corredores([g.indice_slot(1, 1), g.indice_slot(1, 5), g.indice_slot(3, 2)], g) == 2


def test_equivalentes_a_mao():
    assert pares_equivalentes({"ref": 365.5, "corr": 171.5, "nn": 154.5, "opt": 154.5}) == [("nn", "opt")]
    assert pares_equivalentes({"ref": 100.0, "corr": 90.0, "nn": 80.0, "opt": 70.0}) == []
    assert len(pares_equivalentes({"ref": 5.0, "corr": 5.0, "nn": 5.0, "opt": 5.0})) == 6     # C(4,2) pares
    assert pares_equivalentes({"ref": 5.0, "nn": 5.0 + 1e-12}) == [("ref", "nn")]             # dentro da tolerancia
    casos = [{"a": 1.0, "b": 1.0}, {"a": 1.0, "b": 2.0}, {"a": 3.0, "b": 3.0}]
    assert contar_equivalentes(casos) == 2


# ---- pedidos reais ---------------------------------------------------------------------
def test_pedido_40098_no_L0():
    # Valores obtidos com o codigo na Etapa 2 (teste de regressao; sigma_corr fica de fora porque
    # a definicao dele ainda esta em aberto com os modeladores).
    _, mapa = carregar_layout("L0")
    r = pedidos.set_index("order_id").loc[40098]
    c = custos_do_pedido(r.secoes, mapa)
    assert perto(c["ref"], 365.5) and perto(c["nn"], 154.5) and perto(c["opt"], 154.5)
    assert n_corredores(slots_do_pedido(r.secoes, mapa, g), g) == 5
    assert perto(tempo_coleta(c["opt"], r.n_itens), 394.5)
    assert abs(ganho(c["ref"], c["opt"]) - 0.5773) < 1e-4


def test_ganhos_reais_entre_0_e_1():
    for nome in ("L0", "L1", "L2"):
        _, mapa = carregar_layout(nome)
        for r in pedidos.itertuples():
            c = custos_do_pedido(r.secoes, mapa)
            assert c["opt"] >= D[g.ENTRADA, g.CAIXA] - 1e-9               # toda rota custa >= 64 m
            assert perto(ganho(c["ref"], c["ref"]), 0.0)                  # ref contra ela mesma
            ganho_opt = ganho(c["ref"], c["opt"])
            assert 0.0 <= ganho_opt < 1.0, (nome, r.order_id, ganho_opt)
            if len(r.secoes) <= 15:                                       # Held-Karp exato: opt nunca perde
                assert all(ganho_opt >= ganho(c["ref"], c[e]) - 1e-12 for e in ESTRATEGIAS)


def test_pedido_de_uma_secao_todas_equivalentes():                        # hipotese H4
    _, mapa = carregar_layout("L1")
    unicos = [r for r in pedidos.itertuples() if len(r.secoes) == 1]
    assert len(unicos) == 9                                               # 9 pedidos de uma secao so
    for r in unicos:
        c = custos_do_pedido(r.secoes, mapa)
        assert len(pares_equivalentes(c)) == 6, (r.order_id, c)           # os 6 pares empatam
        assert all(perto(ganho(c["ref"], c[e]), 0.0) for e in ESTRATEGIAS)


def test_contagem_de_equivalentes_nos_cem_pedidos():
    _, mapa = carregar_layout("L1")
    custos = [custos_do_pedido(r.secoes, mapa) for r in pedidos.itertuples()]
    n = contar_equivalentes(custos)
    assert 9 <= n <= 100                                                  # ao menos os 9 de uma secao


def test_tempo_nao_muda_a_ordem_das_estrategias():
    # t_item*|o| e t_fixo sao iguais para o mesmo pedido, entao so a distancia decide o ranking.
    _, mapa = carregar_layout("L2")
    for r in pedidos.itertuples():
        c = custos_do_pedido(r.secoes, mapa)
        por_distancia = sorted(ESTRATEGIAS, key=lambda e: c[e])
        por_tempo = sorted(ESTRATEGIAS, key=lambda e: tempo_coleta(c[e], r.n_itens))
        assert [c[e] for e in por_distancia] == [c[e] for e in por_tempo]


# ---- resumo, reducao e ganho medio (a mao) ---------------------------------------------
def test_resumo_a_mao():
    r = resumo([1, 2, 3, 10])
    assert perto(r["media"], 4.0) and perto(r["mediana"], 2.5)


def test_reducao_media_a_mao():
    assert perto(reducao_media([100, 200], [90, 180]), 0.10)             # medias 150 e 135
    # razao das medias (1 - 125/150 = 0,1667), e NAO a media das reducoes por pedido ((0,5 + 0)/2 = 0,25)
    assert perto(reducao_media([100, 200], [50, 200]), 1 - 125 / 150)
    assert perto(reducao_media([100, 200], [100, 200]), 0.0)


def test_reducao_media_reproduz_a_calibracao():
    assert abs(100 * reducao_media([157.234], [144.783]) - 7.92) < 0.005   # calibracao_n_min.csv, n_min = 300


def test_ganho_medio_a_mao():
    assert perto(ganho_medio([100, 200], [80, 100]), 0.35)               # ganhos 0,2 e 0,5


# ---- bootstrap pareado ---------------------------------------------------------------------
def test_bootstrap_reproduzivel():
    v = np.arange(100.0)
    assert bootstrap_ic(np.mean, v) == bootstrap_ic(np.mean, v)          # mesma semente, mesmo resultado
    assert bootstrap_ic(np.mean, v, semente=1) != bootstrap_ic(np.mean, v, semente=2)


def test_bootstrap_intervalo_contem_a_estimativa():
    est, inf, sup = bootstrap_ic(np.mean, np.arange(100.0))
    assert perto(est, 49.5) and inf < est < sup
    # largura esperada, pela aproximacao normal: 2 * 1,96 * desvio / raiz(n) = 2 * 1,96 * 28,87 / 10 = 11,3
    assert 9.0 < sup - inf < 13.5, sup - inf


def test_bootstrap_dados_constantes():
    assert bootstrap_ic(np.mean, [5.0] * 50) == (5.0, 5.0, 5.0)          # sem variacao, intervalo de largura zero
    assert bootstrap_ic(np.mean, [7.0]) == (7.0, 7.0, 7.0)               # um unico pedido


def test_bootstrap_mantem_o_pareamento():
    # b = 2 * a em todo pedido. Se o sorteio fosse independente por serie, b - 2a deixaria de ser 0.
    a = np.arange(100.0)
    est, inf, sup = bootstrap_ic(lambda x, y: float(np.mean(y - 2 * x)), a, 2 * a)
    assert (est, inf, sup) == (0.0, 0.0, 0.0)


def test_bootstrap_pareado_estreita_a_diferenca():
    d0 = np.random.default_rng(0).uniform(100, 200, 100)                 # distancias por pedido
    d1 = d0 - 10                                                         # sempre 10 m a menos, pedido a pedido
    est, inf, sup = bootstrap_ic(lambda a, b: float(np.mean(a - b)), d0, d1)
    assert perto(est, 10.0) and sup - inf < 1e-9                         # pareado: diferenca exata, sem incerteza
    _, inf0, sup0 = bootstrap_ic(np.mean, d0)                            # mas cada media sozinha e incerta
    assert sup0 - inf0 > 5.0


def test_bootstrap_erros():
    for chamada in (lambda: bootstrap_ic(np.mean),                       # sem series
                    lambda: bootstrap_ic(np.mean, []),                   # serie vazia
                    lambda: bootstrap_ic(reducao_media, [1, 2], [1]),    # tamanhos diferentes
                    lambda: bootstrap_ic(np.mean, [1, 2], nivel=1.5)):   # nivel invalido
        try:
            chamada()
        except ValueError:
            continue
        raise AssertionError("era esperado ValueError")


def test_bootstrap_nos_pedidos_reais():
    # Distancias de sigma_opt nos 100 pedidos, em L0 e L1, e a reducao de L1 contra L0.
    # Valores de referencia obtidos com o codigo na Etapa 3 (teste de regressao).
    d = {}
    for nome in ("L0", "L1"):
        _, mapa = carregar_layout(nome)
        d[nome] = [custos_do_pedido(r.secoes, mapa)["opt"] for r in pedidos.itertuples()]
    est, inf, sup = bootstrap_ic(reducao_media, d["L0"], d["L1"])
    assert perto(est, 1 - np.mean(d["L1"]) / np.mean(d["L0"]))           # estimativa = conta direta
    assert inf < est < sup
    assert 0.070 < est < 0.077, est                                      # cerca de 7,3%
    media_l0, _, _ = bootstrap_ic(np.mean, d["L0"])
    assert perto(media_l0, resumo(d["L0"])["media"])


for nome, f in list(globals().items()):
    if nome.startswith("test_"):
        f()
        print("OK", nome)
