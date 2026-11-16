"""Testes do experimento (parte 1: rodar_experimento), com poucos pedidos para ficar rapido.

Rodar na raiz do repositorio:  python tests/test_experimento.py
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from carga import carregar_pedidos_avaliacao                                         # noqa: E402
from config import LAYOUTS, LIMITE_HELD_KARP, TEMPO                                  # noqa: E402
from experimento import (COLUNAS_VERIFICACAO, classificar_ic, distancias_pareadas,  # noqa: E402
                         rodar_experimento, tabela_distancia, tabela_equivalencias, tabela_ganho,
                         tabela_ganho_faixa_corredores, tabela_ganho_faixa_secoes,
                         tabela_reducao_layouts, tabela_tempo_turno, verificacao_hipoteses)
from indicadores import contar_equivalentes                                          # noqa: E402
from grafo_fisico import grafo_padrao                                                # noqa: E402
from rotas import ESTRATEGIAS                                                        # noqa: E402

g = grafo_padrao()
D = g.matriz_D()

todos = carregar_pedidos_avaliacao()
n_secoes = todos["secoes"].apply(len)
# amostra pequena: os 5 primeiros, 2 pedidos de 1 secao, 1 pedido com mais de 15 secoes e o pedido 40098
amostra = pd.concat([
    todos.head(5),
    todos[n_secoes == 1].head(2),
    todos[n_secoes > LIMITE_HELD_KARP].head(1),
    todos[todos["order_id"] == 40098],
]).drop_duplicates("order_id").reset_index(drop=True)
resultados = rodar_experimento(amostra, g, D)


def perto(a, b, tol=1e-9):
    return abs(a - b) <= tol


def test_tamanho_e_colunas():
    assert len(resultados) == len(LAYOUTS) * len(ESTRATEGIAS) * len(amostra)
    assert not resultados.isna().any().any()
    esperadas = {"id_teste", "order_id", "layout", "estrategia", "n_itens", "n_secoes", "n_corredores",
                 "pedido_heuristico", "distancia_m", "tempo_s", "ganho_vs_ref"}
    assert set(resultados.columns) == esperadas


def test_mesmos_pedidos_em_todos_os_casos():
    ids = set(amostra["order_id"])
    for (layout, estrategia), grupo in resultados.groupby(["layout", "estrategia"]):
        assert set(grupo["order_id"]) == ids and len(grupo) == len(amostra), (layout, estrategia)
    assert set(resultados["layout"]) == set(LAYOUTS) and set(resultados["estrategia"]) == set(ESTRATEGIAS)


def test_ref_tem_ganho_zero_e_distancia_minima():
    ref = resultados[resultados["estrategia"] == "ref"]
    assert (ref["ganho_vs_ref"] == 0).all()
    assert (resultados["distancia_m"] >= D[g.ENTRADA, g.CAIXA] - 1e-9).all()       # nunca menos que ENTRADA -> CAIXA


def test_opt_nao_perde_para_as_outras():
    for (layout, order_id), grupo in resultados.groupby(["layout", "order_id"]):
        d = grupo.set_index("estrategia")["distancia_m"]
        assert d["opt"] <= d[["corr", "nn"]].min() + 1e-9, (layout, order_id)       # vale tambem nos heuristicos
        if not grupo["pedido_heuristico"].iloc[0]:
            assert d["opt"] <= d["ref"] + 1e-9, (layout, order_id)                  # exato: nao perde nem para ref


def test_pedido_de_uma_secao_todas_iguais():                                        # hipotese H4
    um = resultados[resultados["n_secoes"] == 1]
    assert len(um) > 0
    for (layout, order_id), grupo in um.groupby(["layout", "order_id"]):
        assert grupo["distancia_m"].nunique() == 1, (layout, order_id)


def test_pedido_40098_no_L0_conferido():
    # valores do demo.py / README: ref 365,5; corr 171,5; nn 154,5; opt 154,5
    linhas = resultados[(resultados["order_id"] == 40098) & (resultados["layout"] == "L0")]
    d = linhas.set_index("estrategia")["distancia_m"]
    assert perto(d["ref"], 365.5) and perto(d["corr"], 171.5)
    assert perto(d["nn"], 154.5) and perto(d["opt"], 154.5)
    assert perto(linhas.set_index("estrategia").loc["nn", "ganho_vs_ref"], (365.5 - 154.5) / 365.5)


def test_tempo_confere_com_a_formula():
    for r in resultados.itertuples():
        esperado = r.distancia_m / TEMPO["velocidade"] + TEMPO["t_item"] * r.n_itens + TEMPO["t_fixo"]
        assert perto(r.tempo_s, esperado, 1e-9)


def test_pedido_heuristico_so_acima_de_15_secoes():
    assert (resultados["pedido_heuristico"] == (resultados["n_secoes"] > LIMITE_HELD_KARP)).all()
    assert resultados["pedido_heuristico"].any()                                    # a amostra tem um pedido grande


def test_reprodutivel():
    de_novo = rodar_experimento(amostra, g, D)
    assert de_novo.equals(resultados)


def sintetico(distancia_l0, fator_l1, fator_l2):
    """Resultados de mentira em formato longo, 4 pedidos, as 4 estrategias com a mesma distancia.

    L1 = fator_l1 * L0 e L2 = fator_l2 * L0 em CADA pedido, entao as reducoes sao conhecidas.
    """
    linhas = []
    fatores = {"L0": 1.0, "L1": fator_l1, "L2": fator_l2}
    for layout, fator in fatores.items():
        for estrategia in ESTRATEGIAS:
            for i, d in enumerate(distancia_l0, start=1):
                linhas.append({"id_teste": i, "layout": layout, "estrategia": estrategia,
                               "distancia_m": fator * d})
    return pd.DataFrame(linhas)


def test_distancias_pareadas_alinhadas_por_pedido():
    dist = distancias_pareadas(resultados)
    assert dist.shape == (len(amostra), len(LAYOUTS) * len(ESTRATEGIAS))
    assert list(dist.index) == sorted(amostra["id_teste"])
    um = resultados[(resultados["layout"] == "L1") & (resultados["estrategia"] == "nn")]
    for r in um.itertuples():                                                        # a mesma linha, o mesmo pedido
        assert perto(dist.loc[r.id_teste, ("L1", "nn")], r.distancia_m)


def test_tabela_distancia_a_mao():
    tabela = tabela_distancia(sintetico([100, 200, 300, 400], 1.0, 1.0))
    assert len(tabela) == len(LAYOUTS) * len(ESTRATEGIAS)
    linha = tabela.iloc[0]
    assert linha["layout"] == "L0" and linha["estrategia"] == "ref"
    assert perto(linha["media_m"], 250) and perto(linha["mediana_m"], 250)
    assert linha["ic_inf_m"] <= 250 <= linha["ic_sup_m"]
    assert 100 <= linha["ic_inf_m"] and linha["ic_sup_m"] <= 400                      # IC fica dentro dos dados
    constante = tabela_distancia(sintetico([50, 50, 50, 50], 1.0, 1.0))
    assert (constante["ic_inf_m"] == 50).all() and (constante["ic_sup_m"] == 50).all()   # sem variacao, IC colapsa


def test_tabela_distancia_bate_com_os_dados_reais():
    tabela = tabela_distancia(resultados).set_index(["layout", "estrategia"])
    medias = resultados.groupby(["layout", "estrategia"])["distancia_m"].mean()
    for caso, media in medias.items():
        assert perto(tabela.loc[caso, "media_m"], media, 1e-9)
        assert tabela.loc[caso, "ic_inf_m"] <= media <= tabela.loc[caso, "ic_sup_m"]


def test_tabela_reducao_a_mao():
    # L1 = 75% de L0 e L2 = 50% de L0 em todo pedido: reducoes de 25%, 50% e, de L1 contra L2, -50%
    tabela = tabela_reducao_layouts(sintetico([100, 200, 300, 400], 0.75, 0.5))
    assert len(tabela) == len(ESTRATEGIAS) * 3
    esperado = {"L1 vs L0": 25.0, "L2 vs L0": 50.0, "L1 vs L2": -50.0}
    for r in tabela.itertuples():
        assert perto(r.reducao_pct, esperado[r.comparacao], 1e-9), r
        assert perto(r.ic_inf_pct, esperado[r.comparacao], 1e-6)                    # razao constante: IC colapsa
        assert perto(r.ic_sup_pct, esperado[r.comparacao], 1e-6)
    linha = tabela[(tabela["estrategia"] == "ref") & (tabela["comparacao"] == "L1 vs L0")].iloc[0]
    assert perto(linha["media_base_m"], 250) and perto(linha["media_novo_m"], 187.5)


def test_tabela_reducao_nos_dados_reais():
    tabela = tabela_reducao_layouts(resultados)
    assert len(tabela) == len(ESTRATEGIAS) * 3 and not tabela.isna().any().any()
    assert ((tabela["ic_inf_pct"] <= tabela["reducao_pct"]) & (tabela["reducao_pct"] <= tabela["ic_sup_pct"])).all()
    for r in tabela.itertuples():                                                    # reducao = razao das medias
        assert perto(r.reducao_pct, 100 * (1 - r.media_novo_m / r.media_base_m), 1e-9)


def test_tabelas_reprodutiveis():
    assert tabela_distancia(resultados).equals(tabela_distancia(resultados))
    assert tabela_reducao_layouts(resultados).equals(tabela_reducao_layouts(resultados))


def sintetico_ganho():
    """4 pedidos de mentira, iguais nos 3 layouts, com ganhos conhecidos contra a ref:
    corr = 50% da ref (ganho 50%), nn = 80% (ganho 20%), opt = 40% (ganho 60%) em TODO pedido.
    Secoes dos pedidos: 1, 3, 8 e 16 (faixas 1-2, 3-4, 7-8 e 16+); so o ultimo e heuristico.
    """
    ref = [100, 200, 300, 400]
    n_secoes = [1, 3, 8, 16]
    fatores = {"ref": 1.0, "corr": 0.5, "nn": 0.8, "opt": 0.4}
    linhas = []
    for layout in LAYOUTS:
        for estrategia, fator in fatores.items():
            for i, (d, n) in enumerate(zip(ref, n_secoes), start=1):
                linhas.append({"id_teste": i, "layout": layout, "estrategia": estrategia,
                               "distancia_m": fator * d, "n_secoes": n, "pedido_heuristico": n > 15})
    return pd.DataFrame(linhas)


def test_tabela_ganho_a_mao():
    tabela = tabela_ganho(sintetico_ganho())
    assert len(tabela) == len(LAYOUTS) * 3 and "ref" not in set(tabela["estrategia"])
    esperado = {"corr": 50.0, "nn": 20.0, "opt": 60.0}
    for r in tabela.itertuples():
        assert perto(r.ganho_medio_pct, esperado[r.estrategia], 1e-9)
        assert perto(r.ganho_mediano_pct, esperado[r.estrategia], 1e-9)
        assert perto(r.ic_inf_pct, esperado[r.estrategia], 1e-6)                    # ganho constante: IC colapsa
        assert perto(r.ic_sup_pct, esperado[r.estrategia], 1e-6)
        assert r.n_pedidos_opt_heuristico == 1


def test_tabela_ganho_faixa_a_mao():
    tabela = tabela_ganho_faixa_secoes(sintetico_ganho())
    assert set(tabela["faixa_secoes"]) == {"1-2", "3-4", "7-8", "16+"}               # faixas vazias sao puladas
    assert len(tabela) == len(LAYOUTS) * 4 * 3
    assert (tabela["n_pedidos"] == 1).all()
    esperado = {"corr": 50.0, "nn": 20.0, "opt": 60.0}
    for r in tabela.itertuples():
        assert perto(r.ganho_medio_pct, esperado[r.estrategia], 1e-9)
        assert r.n_pedidos_opt_heuristico == (1 if r.faixa_secoes == "16+" else 0)


def test_tabela_ganho_nos_dados_reais():
    tabela = tabela_ganho(resultados).set_index(["layout", "estrategia"])
    medias = resultados[resultados["estrategia"] != "ref"].groupby(["layout", "estrategia"])["ganho_vs_ref"].mean()
    for caso, media in medias.items():                                               # bate com o ganho_vs_ref do CSV
        assert perto(tabela.loc[caso, "ganho_medio_pct"], 100 * media, 1e-9)
        assert tabela.loc[caso, "ic_inf_pct"] <= 100 * media <= tabela.loc[caso, "ic_sup_pct"]
    assert (tabela["n_pedidos_opt_heuristico"] == 1).all()                           # a amostra tem 1 pedido > 15 secoes


def test_tabela_ganho_faixa_nos_dados_reais():
    tabela = tabela_ganho_faixa_secoes(resultados)
    for _, grupo in tabela.groupby(["layout", "estrategia"]):
        assert grupo["n_pedidos"].sum() == len(amostra)                              # cada pedido cai em uma faixa so
    por_faixa = resultados.assign(faixa=pd.cut(resultados["n_secoes"], [0, 2, 4, 6, 8, 11, 15, 10**6],
                                               labels=["1-2", "3-4", "5-6", "7-8", "9-11", "12-15", "16+"]))
    medias = por_faixa[por_faixa["estrategia"] == "opt"].groupby(["layout", "faixa"], observed=True)["ganho_vs_ref"].mean()
    opt = tabela[tabela["estrategia"] == "opt"].set_index(["layout", "faixa_secoes"])
    for (layout, faixa), media in medias.items():
        assert perto(opt.loc[(layout, faixa), "ganho_medio_pct"], 100 * media, 1e-9)


def sintetico_corredores():
    """4 pedidos de mentira com ganhos conhecidos (corr 50%, nn 20%, opt 60%) e corredores DIFERENTES por layout.

    Corredores distintos: em L0 sao 1, 3, 8 e 10; em L1 sao 2, 4, 5 e 9; em L2 sao 1, 1, 12 e 12.
    So o pedido 4 e heuristico.
    """
    ref = [100, 200, 300, 400]
    corredores = {"L0": [1, 3, 8, 10], "L1": [2, 4, 5, 9], "L2": [1, 1, 12, 12]}
    fatores = {"ref": 1.0, "corr": 0.5, "nn": 0.8, "opt": 0.4}
    linhas = []
    for layout in LAYOUTS:
        for estrategia, fator in fatores.items():
            for i, d in enumerate(ref, start=1):
                linhas.append({"id_teste": i, "layout": layout, "estrategia": estrategia,
                               "distancia_m": fator * d, "n_corredores": corredores[layout][i - 1],
                               "n_secoes": 1, "pedido_heuristico": i == 4})
    return pd.DataFrame(linhas)


def test_tabela_ganho_corredores_a_mao():
    tabela = tabela_ganho_faixa_corredores(sintetico_corredores())
    faixas = {layout: set(g["faixa_corredores"]) for layout, g in tabela.groupby("layout")}
    assert faixas["L0"] == {"1-2", "3-4", "7-8", "9+"}                               # a faixa depende do layout
    assert faixas["L1"] == {"1-2", "3-4", "5-6", "9+"}
    assert faixas["L2"] == {"1-2", "9+"}
    for r in tabela.itertuples():                                                    # em L2, 2 pedidos em cada faixa
        assert r.n_pedidos == (2 if r.layout == "L2" else 1), r
    esperado = {"corr": 50.0, "nn": 20.0, "opt": 60.0}
    for r in tabela.itertuples():
        assert perto(r.ganho_medio_pct, esperado[r.estrategia], 1e-9)
        assert perto(r.ic_inf_pct, esperado[r.estrategia], 1e-6)
        assert r.n_pedidos_opt_heuristico == (1 if r.faixa_corredores == "9+" else 0)


def test_tabela_ganho_corredores_nos_dados_reais():
    tabela = tabela_ganho_faixa_corredores(resultados)
    for _, grupo in tabela.groupby(["layout", "estrategia"]):
        assert grupo["n_pedidos"].sum() == len(amostra)
    ref_cor = resultados[resultados["estrategia"] == "opt"].assign(
        faixa=lambda d: pd.cut(d["n_corredores"], [0, 2, 4, 6, 8, float("inf")],
                               labels=["1-2", "3-4", "5-6", "7-8", "9+"]))
    medias = ref_cor.groupby(["layout", "faixa"], observed=True)["ganho_vs_ref"].mean()
    opt = tabela[tabela["estrategia"] == "opt"].set_index(["layout", "faixa_corredores"])
    for (layout, faixa), media in medias.items():
        assert perto(opt.loc[(layout, faixa), "ganho_medio_pct"], 100 * media, 1e-9)


def sintetico_tempo(tempos):
    """Resultados de mentira so com o tempo de cada pedido, igual em todos os casos."""
    linhas = [{"id_teste": i, "layout": layout, "estrategia": e, "tempo_s": t}
              for layout in LAYOUTS for e in ESTRATEGIAS for i, t in enumerate(tempos, start=1)]
    return pd.DataFrame(linhas)


def test_tabela_tempo_turno_a_mao():
    tabela = tabela_tempo_turno(sintetico_tempo([400, 500, 600, 700]))
    assert len(tabela) == len(LAYOUTS) * len(ESTRATEGIAS)
    for r in tabela.itertuples():
        assert perto(r.tempo_medio_s, 550) and perto(r.pedidos_turno, TEMPO["turno"] / 550)   # 28.800 / 550
        assert r.ic_inf_s <= 550 <= r.ic_sup_s
        assert r.ic_inf_turno <= r.pedidos_turno <= r.ic_sup_turno
    constante = tabela_tempo_turno(sintetico_tempo([600, 600, 600, 600]))
    assert all(perto(r.pedidos_turno, 48.0) and perto(r.ic_inf_turno, 48.0) and perto(r.ic_sup_turno, 48.0)
               for r in constante.itertuples())                                           # 28.800 / 600 = 48


def test_tabela_tempo_turno_nos_dados_reais():
    tempo = tabela_tempo_turno(resultados).set_index(["layout", "estrategia"])
    distancia = tabela_distancia(resultados).set_index(["layout", "estrategia"])
    itens_medios = amostra["n_itens"].mean()
    for caso in tempo.index:
        # T medio = D medio / v + t_item * itens medios + t_fixo (os itens sao os mesmos em todos os casos)
        esperado = (distancia.loc[caso, "media_m"] / TEMPO["velocidade"]
                    + TEMPO["t_item"] * itens_medios + TEMPO["t_fixo"])
        assert perto(tempo.loc[caso, "tempo_medio_s"], esperado, 1e-9)
        assert perto(tempo.loc[caso, "pedidos_turno"], TEMPO["turno"] / tempo.loc[caso, "tempo_medio_s"], 1e-9)
    for layout in LAYOUTS:                                                                # menos distancia, menos tempo
        assert tempo.loc[(layout, "opt"), "tempo_medio_s"] <= tempo.loc[(layout, "ref"), "tempo_medio_s"]


def sintetico_equivalencias():
    """4 pedidos de mentira (1, 3, 5 e 7 secoes) com equivalencias conhecidas, iguais nos 3 layouts:
        pedido 1: as 4 iguais (100)          pedido 2: so nn = opt (180)
        pedido 3: corr = nn = opt (250)      pedido 4: todas diferentes
    """
    distancias = {"ref": [100, 200, 300, 400], "corr": [100, 190, 250, 350],
                  "nn": [100, 180, 250, 300], "opt": [100, 180, 250, 250]}
    n_secoes = [1, 3, 5, 7]
    linhas = [{"id_teste": i, "layout": layout, "estrategia": e, "distancia_m": distancias[e][i - 1],
               "n_secoes": n_secoes[i - 1], "pedido_heuristico": False}
              for layout in LAYOUTS for e in ESTRATEGIAS for i in range(1, 5)]
    return pd.DataFrame(linhas)


def test_tabela_equivalencias_a_mao():
    tabela = tabela_equivalencias(sintetico_equivalencias())
    assert len(tabela) == len(LAYOUTS) * 8                                           # 6 pares + qualquer par + as 4
    # caso: (pedidos no total, pedidos com 2 ou mais secoes)
    esperado = {"ref = corr": (1, 0), "ref = nn": (1, 0), "ref = opt": (1, 0),
                "corr = nn": (2, 1), "corr = opt": (2, 1), "nn = opt": (3, 2),
                "qualquer par": (3, 2), "as 4 iguais": (1, 0)}
    for r in tabela.itertuples():
        total, varias = esperado[r.caso]
        assert (r.n_pedidos, r.n_pedidos_2mais_secoes) == (total, varias), r
        assert perto(r.pct_pedidos, 100 * total / 4) and perto(r.pct_pedidos_2mais_secoes, 100 * varias / 3)


def test_tabela_equivalencias_nos_dados_reais():
    tabela = tabela_equivalencias(resultados).set_index(["layout", "caso"])
    dist = distancias_pareadas(resultados)
    n_secoes = resultados.drop_duplicates("id_teste").set_index("id_teste")["n_secoes"].loc[dist.index]
    for layout in LAYOUTS:
        por_pedido = [{e: dist[(layout, e)].iloc[i] for e in ESTRATEGIAS} for i in range(len(dist))]
        assert tabela.loc[(layout, "qualquer par"), "n_pedidos"] == contar_equivalentes(por_pedido)
        assert tabela.loc[(layout, "as 4 iguais"), "n_pedidos"] >= (n_secoes == 1).sum()   # 1 secao: todas iguais
        assert tabela.loc[(layout, "qualquer par"), "n_pedidos"] >= tabela.loc[(layout, "as 4 iguais"), "n_pedidos"]


def test_classificar_ic():
    assert classificar_ic(1.0, 2.0) == "confirmada"
    assert classificar_ic(-2.0, -1.0) == "contrariada"
    assert classificar_ic(-1.0, 2.0) == "inconclusiva"
    assert classificar_ic(0.0, 2.0) == "inconclusiva"                                # encostar no 0 nao basta


def reducao_ficticia():
    """tabela_reducao_layouts de mentira, com um resultado de cada tipo escolhido a mao."""
    ics = {  # (comparacao, estrategia): (reducao, ic_inf, ic_sup)
        ("L1 vs L0", "ref"): (-6.7, -12.2, -1.4), ("L1 vs L0", "corr"): (7.9, 5.2, 10.6),
        ("L1 vs L0", "nn"): (8.4, -1.0, 12.1), ("L1 vs L0", "opt"): (7.4, 4.8, 9.9),
        **{("L2 vs L0", e): (20.0, 15.0, 25.0) for e in ESTRATEGIAS},
        **{("L1 vs L2", e): (-20.0, -25.0, -15.0) for e in ESTRATEGIAS},
    }
    return pd.DataFrame([{"estrategia": e, "comparacao": c, "reducao_pct": v[0], "ic_inf_pct": v[1],
                          "ic_sup_pct": v[2]} for (c, e), v in ics.items()])


def test_verificacao_hipoteses_a_mao():
    base = sintetico_ganho()           # 4 pedidos (1, 3, 8 e 16 secoes), ganhos constantes de 50%, 20% e 60%
    ganhos, faixas = tabela_ganho(base), tabela_ganho_faixa_secoes(base)
    v = verificacao_hipoteses(base, reducao_ficticia(), ganhos, faixas)
    assert list(v.columns) == COLUNAS_VERIFICACAO
    assert len(v) == 42 and v["resultado"].isin(["confirmada", "contrariada", "inconclusiva", "mista"]).all()

    def resultado(**filtro):
        linhas = v
        for coluna, valor in filtro.items():
            linhas = linhas[linhas[coluna] == valor]
        assert len(linhas) == 1, filtro
        return linhas.iloc[0]["resultado"]

    assert resultado(hipotese="H1", parte="L1 vs L0", estrategia="ref") == "contrariada"
    assert resultado(hipotese="H1", parte="L1 vs L0", estrategia="corr") == "confirmada"
    assert resultado(hipotese="H1", parte="L1 vs L0", estrategia="nn") == "inconclusiva"
    assert resultado(hipotese="H1", parte="L1 vs L0", estrategia="as 4") == "mista"
    assert resultado(hipotese="H1", parte="L2 vs L0", estrategia="as 4") == "confirmada"
    assert resultado(hipotese="H2", parte="L1 vs L2", estrategia="as 4") == "contrariada"
    assert resultado(hipotese="H3", parte="ganho contra ref > 0", estrategia="opt", layout="L1") == "confirmada"
    # opt (40% da ref) nunca perde para as outras; a amostra tem 3 pedidos exatos e 1 heuristico
    exatos = v[v["parte"] == "opt <= demais (pedidos exatos)"]
    assert (exatos["n_pedidos"] == 3).all() and (exatos["valor"] == 0).all() and (exatos["resultado"] == "confirmada").all()
    heur = v[v["parte"] == "opt <= demais (pedidos heuristicos)"]
    assert (heur["n_pedidos"] == 1).all() and (heur["resultado"] == "confirmada").all()
    assert (v[v["parte"] == "ganho cresce com |S(o)| (faixas)"]["resultado"] == "confirmada").all()
    # o pedido de 1 secao tem distancias diferentes entre as estrategias (100, 50, 80, 40): H4 contrariada
    h4 = v[v["hipotese"] == "H4"]
    assert (h4["n_pedidos"] == 1).all() and (h4["valor"] == 1).all() and (h4["resultado"] == "contrariada").all()


def test_verificacao_ganho_com_queda_entre_faixas():
    base = sintetico_ganho()
    ganhos, faixas = tabela_ganho(base), tabela_ganho_faixa_secoes(base)
    caso = (faixas["layout"] == "L0") & (faixas["estrategia"] == "opt") & (faixas["faixa_secoes"] == "3-4")
    faixas.loc[caso, "ganho_medio_pct"] = 10.0                                       # 60 -> 10 -> 60: uma queda
    v = verificacao_hipoteses(base, reducao_ficticia(), ganhos, faixas)
    crescimento = v[v["parte"] == "ganho cresce com |S(o)| (faixas)"].set_index(["layout", "estrategia"])
    assert crescimento.loc[("L0", "opt"), "valor"] == 1
    assert crescimento.loc[("L0", "opt"), "resultado"] == "inconclusiva"
    assert crescimento.loc[("L1", "opt"), "resultado"] == "confirmada"


def test_verificacao_hipoteses_nos_dados_reais():
    reducao, ganhos = tabela_reducao_layouts(resultados), tabela_ganho(resultados)
    faixas = tabela_ganho_faixa_secoes(resultados)
    v = verificacao_hipoteses(resultados, reducao, ganhos, faixas)
    assert len(v) == 42 and not v["resultado"].isna().any()
    uma_secao = int((resultados.drop_duplicates("id_teste")["n_secoes"] == 1).sum())
    h4 = v[v["hipotese"] == "H4"]
    assert (h4["n_pedidos"] == uma_secao).all() and (h4["resultado"] == "confirmada").all()   # H4 vale de verdade
    exatos = v[v["parte"] == "opt <= demais (pedidos exatos)"]
    assert (exatos["resultado"] == "confirmada").all()


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("OK", nome)
