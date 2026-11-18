"""Testes da analise de sensibilidade dos parametros de tempo.

Rodar na raiz do repositorio:  python tests/test_sensibilidade.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from carga import carregar_pedidos_avaliacao                                         # noqa: E402
from config import LAYOUTS, SENSIBILIDADE, TEMPO                                     # noqa: E402
from experimento import rodar_experimento                                            # noqa: E402
from grafo_fisico import grafo_padrao                                                # noqa: E402
from rotas import ESTRATEGIAS                                                        # noqa: E402
from sensibilidade import (calcular_cenario, cenarios, ordem_dos_casos,              # noqa: E402
                           tabela_sensibilidade)

CASOS = [(layout, e) for layout in LAYOUTS for e in ESTRATEGIAS]


def perto(a, b, tol=1e-9):
    return abs(a - b) <= tol


def sintetico(distancias=None, itens=None):
    """Resultados de mentira (layout, estrategia, distancia_m, n_itens) com 2 pedidos em cada um dos 12 casos.

    distancias, itens: dicionarios (layout, estrategia) -> lista de 2 valores; o padrao e distancia distinta
    por caso (para a ordem dos casos ficar bem definida) e 4 e 6 itens.
    """
    linhas = []
    for i, caso in enumerate(CASOS):
        d = (distancias or {}).get(caso, [100.0 + 10 * i, 200.0 + 10 * i])
        n = (itens or {}).get(caso, [4, 6])
        for pedido in range(2):
            linhas.append({"layout": caso[0], "estrategia": caso[1], "distancia_m": d[pedido],
                           "n_itens": n[pedido]})
    return pd.DataFrame(linhas)


def test_cenarios():
    lista = cenarios()
    assert len(lista) == 10
    assert len({c["cenario"] for c in lista}) == 10                                  # nomes distintos
    base = {"velocidade": TEMPO["velocidade"], "t_item": TEMPO["t_item"], "t_fixo": TEMPO["t_fixo"]}
    assert lista[0]["cenario"] == "base" and all(lista[0][k] == v for k, v in base.items())
    assert [c["tipo"] for c in lista].count("um por vez") == 7                       # 3 + 2 + 2 outros valores
    for c in lista:
        if c["tipo"] == "um por vez":                                                # muda exatamente um parametro
            diferentes = [k for k in base if c[k] != base[k]]
            assert diferentes == [c["parametro"]]
    v, ti, tf = SENSIBILIDADE["velocidade"], SENSIBILIDADE["t_item"], SENSIBILIDADE["t_fixo"]
    pessimista = next(c for c in lista if c["cenario"] == "pessimista")
    otimista = next(c for c in lista if c["cenario"] == "otimista")
    assert (pessimista["velocidade"], pessimista["t_item"], pessimista["t_fixo"]) == (min(v), max(ti), max(tf))
    assert (otimista["velocidade"], otimista["t_item"], otimista["t_fixo"]) == (max(v), min(ti), min(tf))


def test_calcular_cenario_a_mao():
    # pedidos: distancias 100 e 200 m, com 4 e 6 itens, em todos os casos
    todos = sintetico({c: [100.0, 200.0] for c in CASOS})
    por_nome = {c["cenario"]: c for c in cenarios()}
    base = {(l["layout"], l["estrategia"]): l for l in calcular_cenario(todos, por_nome["base"])}
    # base (1 m/s, 15 s, 120 s): T1 = 100 + 60 + 120 = 280 e T2 = 200 + 90 + 120 = 410, media 345
    assert perto(base[("L0", "ref")]["tempo_medio_s"], 345.0)
    assert perto(base[("L0", "ref")]["pedidos_turno"], TEMPO["turno"] / 345.0)
    pess = {(l["layout"], l["estrategia"]): l for l in calcular_cenario(todos, por_nome["pessimista"])}
    # pessimista (0,8 m/s, 20 s, 180 s): T1 = 125 + 80 + 180 = 385 e T2 = 250 + 120 + 180 = 550, media 467,5
    assert perto(pess[("L2", "opt")]["tempo_medio_s"], 467.5)
    assert perto(pess[("L2", "opt")]["pedidos_turno"], TEMPO["turno"] / 467.5)
    assert len(base) == 12 and pess[("L0", "ref")]["cenario"] == "pessimista"


def test_ordem_dos_casos():
    linhas = [{"layout": "L1", "estrategia": "nn", "tempo_medio_s": 300.0},
              {"layout": "L0", "estrategia": "ref", "tempo_medio_s": 500.0},
              {"layout": "L2", "estrategia": "opt", "tempo_medio_s": 200.0},
              {"layout": "L0", "estrategia": "opt", "tempo_medio_s": 300.0}]
    assert ordem_dos_casos(linhas) == [("L2", "opt"), ("L0", "opt"), ("L1", "nn"), ("L0", "ref")]   # empate: pelo nome


def test_tabela_sintetica_forma_e_ranking():
    tabela = tabela_sensibilidade(sintetico())
    assert len(tabela) == 10 * 12 and not tabela.isna().any().any()
    assert set(tabela["cenario"]) == {c["cenario"] for c in cenarios()}
    assert tabela["ranking_igual_ao_base"].all()          # mesmos itens em todos os casos: so D/v diferencia


def test_ranking_muda_se_os_itens_forem_diferentes():
    # Caso A = (L0, ref): 100 m e 2 itens. Caso B = (L0, corr): 20 m e 8 itens. Os demais: longe e com 2 itens.
    # Base:     A = 100 + 30 + 120 = 250  <  B = 20 + 120 + 120 = 260
    # Otimista (1,1 m/s, 10 s, 60 s): A = 90,9 + 20 + 60 = 170,9  >  B = 18,2 + 80 + 60 = 158,2 (inverte)
    distancias = {c: [900.0 + 10 * i] * 2 for i, c in enumerate(CASOS)}
    distancias[("L0", "ref")] = [100.0, 100.0]
    distancias[("L0", "corr")] = [20.0, 20.0]
    itens = {c: [2, 2] for c in CASOS}
    itens[("L0", "corr")] = [8, 8]
    tabela = tabela_sensibilidade(sintetico(distancias, itens))
    por_cenario = tabela.drop_duplicates("cenario").set_index("cenario")["ranking_igual_ao_base"]
    assert por_cenario["base"] and not por_cenario["otimista"]


def test_tabela_com_pedidos_reais():
    g = grafo_padrao()
    D = g.matriz_D()
    resultados = rodar_experimento(carregar_pedidos_avaliacao().head(8), g, D)
    tabela = tabela_sensibilidade(resultados)
    assert len(tabela) == 120 and tabela["ranking_igual_ao_base"].all()
    # o cenario base reproduz o tempo medio que o experimento ja calculou com config.TEMPO
    base = tabela[tabela["cenario"] == "base"].set_index(["layout", "estrategia"])
    medias = resultados.groupby(["layout", "estrategia"])["tempo_s"].mean()
    for caso, media in medias.items():
        assert perto(base.loc[caso, "tempo_medio_s"], media, 1e-9)
    # piorar as premissas diminui os pedidos por turno; melhorar aumenta
    pedidos = tabela.pivot(index=["layout", "estrategia"], columns="cenario", values="pedidos_turno")
    assert (pedidos["pessimista"] < pedidos["base"]).all() and (pedidos["base"] < pedidos["otimista"]).all()
    assert (pedidos["velocidade = 0.8"] < pedidos["base"]).all() and (pedidos["base"] < pedidos["velocidade = 1.1"]).all()


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("OK", nome)
