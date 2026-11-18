# Experimento principal: 3 layouts x 4 estrategias x 100 pedidos de avaliacao = 1.200 execucoes,
# todas com a mesma matriz D.
#
# O dado bruto vai para resultados/resultados_por_pedido.csv (uma linha por pedido, layout e estrategia,
# com distancia, tempo e ganho). As tabelas sao calculadas a partir dele, sem refazer rotas,
# e trazem IC de 95% por bootstrap pareado:
#   tabela_distancia, tabela_reducao_layouts (H1, H2), tabela_ganho (H3),
#   tabela_ganho_faixa_secoes, tabela_ganho_faixa_corredores, tabela_tempo_turno,
#   tabela_equivalencias, verificacao_hipoteses (H1 a H4).
#
# Uso (na raiz do projeto): python src/experimento.py

from itertools import combinations

import numpy as np
import pandas as pd

from carga import carregar_pedidos_avaliacao, slots_do_pedido
from config import LAYOUTS, PASTA_RESULTADOS
from grafo_fisico import carregar_layout, grafo_padrao
from indicadores import (bootstrap_ic, ganho, ganho_medio, n_corredores, pares_equivalentes,
                         pedidos_por_turno, reducao_media, resumo, tempo_coleta)
from rotas import ESTRATEGIAS, executar, opt_e_exata

# Arquivos de saida, em resultados/.
SAIDA_POR_PEDIDO = PASTA_RESULTADOS / "resultados_por_pedido.csv"
SAIDA_TABELA_DISTANCIA = PASTA_RESULTADOS / "tabela_distancia.csv"
SAIDA_TABELA_REDUCAO = PASTA_RESULTADOS / "tabela_reducao_layouts.csv"
SAIDA_TABELA_GANHO = PASTA_RESULTADOS / "tabela_ganho.csv"
SAIDA_TABELA_GANHO_FAIXA = PASTA_RESULTADOS / "tabela_ganho_faixa_secoes.csv"
SAIDA_TABELA_GANHO_CORREDORES = PASTA_RESULTADOS / "tabela_ganho_faixa_corredores.csv"
SAIDA_TABELA_TEMPO = PASTA_RESULTADOS / "tabela_tempo_turno.csv"
SAIDA_TABELA_EQUIVALENCIAS = PASTA_RESULTADOS / "tabela_equivalencias.csv"
SAIDA_VERIFICACAO = PASTA_RESULTADOS / "verificacao_hipoteses.csv"

# Abaixo disso (em metros), duas distancias contam como iguais.
TOLERANCIA_DISTANCIA = 1e-9

COLUNAS_VERIFICACAO = ["hipotese", "parte", "estrategia", "layout", "n_pedidos", "medida", "valor",
                       "ic_inf", "ic_sup", "resultado"]

# So estas tem ganho contra a ref (o da propria ref e sempre 0).
ESTRATEGIAS_COM_CRITERIO = tuple(e for e in ESTRATEGIAS if e != "ref")

# Faixas de |S(o)| (secoes distintas), como na amostra de avaliacao do documento de modelagem:
# (nome, minimo, maximo), extremos incluidos.
FAIXAS_SECOES = (("1-2", 1, 2), ("3-4", 3, 4), ("5-6", 5, 6), ("7-8", 7, 8),
                 ("9-11", 9, 11), ("12-15", 12, 15), ("16+", 16, np.inf))

# Faixas de corredores distintos: escolha do grupo (o documento nao define); formam grupos de tamanho parecido.
FAIXAS_CORREDORES = (("1-2", 1, 2), ("3-4", 3, 4), ("5-6", 5, 6), ("7-8", 7, 8), ("9+", 9, np.inf))

# Comparacoes (base, novo): a reducao mede quanto 'novo' anda a menos que 'base'.
# L2 contra L1 serve a H2.
COMPARACOES_LAYOUTS = (("L0", "L1"), ("L0", "L2"), ("L2", "L1"))


def rodar_experimento(pedidos, g, D):
    # Roda todas as estrategias, em todos os layouts, para todos os pedidos.
    # Devolve um DataFrame em formato longo (uma linha por pedido, layout e estrategia).
    linhas = []
    for layout in LAYOUTS:
        _, mapa = carregar_layout(layout)
        for p in pedidos.itertuples():
            # Slots do pedido neste layout, na ordem do carrinho.
            slots = list(dict.fromkeys(slots_do_pedido(p.secoes, mapa, g)))
            # estrategia -> metros.
            custos = {e: executar(e, slots, D, g)[1] for e in ESTRATEGIAS}
            for e in ESTRATEGIAS:
                linhas.append({
                    "id_teste": p.id_teste,
                    "order_id": p.order_id,
                    "layout": layout,
                    "estrategia": e,
                    "n_itens": p.n_itens,
                    "n_secoes": len(slots),
                    "n_corredores": n_corredores(slots, g),
                    "pedido_heuristico": not opt_e_exata(slots),
                    "distancia_m": custos[e],
                    "tempo_s": tempo_coleta(custos[e], p.n_itens),
                    "ganho_vs_ref": ganho(custos["ref"], custos[e]),
                })
    return pd.DataFrame(linhas)


def distancias_pareadas(resultados):
    # Distancia de cada pedido em cada caso: uma linha por pedido, uma coluna por (layout, estrategia),
    # todas na mesma ordem de pedidos. E o que o bootstrap pareado exige.
    return resultados.pivot(index="id_teste", columns=["layout", "estrategia"], values="distancia_m")


def tabela_distancia(resultados):
    # Media, mediana e IC de 95% da distancia, por layout e estrategia.
    dist = distancias_pareadas(resultados)
    linhas = []
    for layout in LAYOUTS:
        for e in ESTRATEGIAS:
            d = dist[(layout, e)].to_numpy()
            _, inferior, superior = bootstrap_ic(np.mean, d)
            linhas.append({"layout": layout, "estrategia": e,
                           "media_m": resumo(d)["media"], "mediana_m": resumo(d)["mediana"],
                           "ic_inf_m": inferior, "ic_sup_m": superior})
    return pd.DataFrame(linhas)


def tabela_reducao_layouts(resultados):
    # Reducao de distancia entre layouts (H1 e H2), por estrategia: 100 * (1 - media(novo) / media(base)).
    # Positiva = o layout novo anda menos. Se o IC inteiro esta acima de 0, a reducao se distingue de zero.
    dist = distancias_pareadas(resultados)
    linhas = []
    for e in ESTRATEGIAS:
        for base, novo in COMPARACOES_LAYOUTS:
            d_base, d_novo = dist[(base, e)].to_numpy(), dist[(novo, e)].to_numpy()
            reducao, inferior, superior = bootstrap_ic(reducao_media, d_base, d_novo)
            linhas.append({"estrategia": e, "comparacao": f"{novo} vs {base}",
                           "media_base_m": float(d_base.mean()), "media_novo_m": float(d_novo.mean()),
                           "reducao_pct": 100 * reducao,
                           "ic_inf_pct": 100 * inferior, "ic_sup_pct": 100 * superior})
    return pd.DataFrame(linhas)


def dados_do_pedido(resultados, indice):
    # n_secoes e pedido_heuristico de cada pedido (iguais em todos os layouts e estrategias),
    # na ordem de 'indice'.
    return resultados.drop_duplicates("id_teste").set_index("id_teste")[["n_secoes", "pedido_heuristico"]].loc[indice]


def _ganho_por_faixa(dist, heuristico, valores, faixas, coluna_faixa):
    # Ganho contra ref por faixa de um valor do pedido (secoes ou corredores), por layout e estrategia.
    # valores = {layout: array com o valor de cada pedido}; faixas = (nome, minimo, maximo).
    # Faixas sem pedidos sao puladas.
    linhas = []
    for layout in LAYOUTS:
        d_ref = dist[(layout, "ref")].to_numpy()
        for nome, minimo, maximo in faixas:
            na_faixa = (valores[layout] >= minimo) & (valores[layout] <= maximo)
            if not na_faixa.any():
                continue
            for e in ESTRATEGIAS_COM_CRITERIO:
                d_sigma = dist[(layout, e)].to_numpy()
                media, inferior, superior = bootstrap_ic(ganho_medio, d_ref[na_faixa], d_sigma[na_faixa])
                linhas.append({"layout": layout, coluna_faixa: nome, "n_pedidos": int(na_faixa.sum()),
                               "estrategia": e,
                               "ganho_medio_pct": 100 * media,
                               "ic_inf_pct": 100 * inferior, "ic_sup_pct": 100 * superior,
                               "n_pedidos_opt_heuristico": int(heuristico[na_faixa].sum())})
    return pd.DataFrame(linhas)


def tabela_ganho(resultados):
    # Ganho de corr, nn e opt contra ref, por layout: G(o) = (D_ref - D_sigma) / D_ref em cada pedido.
    # Media com IC de 95% e mediana, em pontos percentuais.
    # n_pedidos_opt_heuristico: pedidos em que opt nao e exata (mais de 15 secoes).
    dist = distancias_pareadas(resultados)
    heuristicos = int(dados_do_pedido(resultados, dist.index)["pedido_heuristico"].sum())
    linhas = []
    for layout in LAYOUTS:
        d_ref = dist[(layout, "ref")].to_numpy()
        for e in ESTRATEGIAS_COM_CRITERIO:
            d_sigma = dist[(layout, e)].to_numpy()
            media, inferior, superior = bootstrap_ic(ganho_medio, d_ref, d_sigma)
            linhas.append({"layout": layout, "estrategia": e,
                           "ganho_medio_pct": 100 * media,
                           "ic_inf_pct": 100 * inferior, "ic_sup_pct": 100 * superior,
                           "ganho_mediano_pct": 100 * float(np.median(ganho(d_ref, d_sigma))),
                           "n_pedidos_opt_heuristico": heuristicos})
    return pd.DataFrame(linhas)


def tabela_ganho_faixa_secoes(resultados):
    # Ganho por faixa de |S(o)| (H3: o ganho cresce com |S(o)|?).
    # Cada faixa tem 8 a 18 pedidos, entao o IC e largo: leia a tendencia, nao cada linha.
    dist = distancias_pareadas(resultados)
    pedido = dados_do_pedido(resultados, dist.index)
    n_secoes = pedido["n_secoes"].to_numpy()
    return _ganho_por_faixa(dist, pedido["pedido_heuristico"].to_numpy(),
                            {layout: n_secoes for layout in LAYOUTS}, FAIXAS_SECOES, "faixa_secoes")


def corredores_por_layout(resultados, indice):
    # Corredores distintos de cada pedido em cada layout
    # (muda com o layout, nao com a estrategia; usa as linhas da ref).
    ref = resultados[resultados["estrategia"] == "ref"]
    return ref.pivot(index="id_teste", columns="layout", values="n_corredores").loc[indice]


def tabela_ganho_faixa_corredores(resultados):
    # Como a tabela por secoes, mas agrupando pelo numero de corredores visitados.
    # O mesmo pedido pode cair em faixas diferentes em cada layout.
    dist = distancias_pareadas(resultados)
    corredores = corredores_por_layout(resultados, dist.index)
    heuristico = dados_do_pedido(resultados, dist.index)["pedido_heuristico"].to_numpy()
    return _ganho_por_faixa(dist, heuristico, {layout: corredores[layout].to_numpy() for layout in LAYOUTS},
                            FAIXAS_CORREDORES, "faixa_corredores")


def tempos_pareados(resultados):
    # Como distancias_pareadas, mas com o tempo T(o) em segundos.
    return resultados.pivot(index="id_teste", columns=["layout", "estrategia"], values="tempo_s")


def tabela_tempo_turno(resultados):
    # Tempo medio de coleta e pedidos por turno (H / T medio), por layout e estrategia, com IC de 95%.
    # O IC dos pedidos por turno vem do proprio bootstrap, nao do IC do tempo.
    tempos = tempos_pareados(resultados)
    linhas = []
    for layout in LAYOUTS:
        for e in ESTRATEGIAS:
            t = tempos[(layout, e)].to_numpy()
            media, t_inf, t_sup = bootstrap_ic(np.mean, t)
            por_turno, p_inf, p_sup = bootstrap_ic(pedidos_por_turno, t)
            linhas.append({"layout": layout, "estrategia": e,
                           "tempo_medio_s": media, "ic_inf_s": t_inf, "ic_sup_s": t_sup,
                           "pedidos_turno": por_turno, "ic_inf_turno": p_inf, "ic_sup_turno": p_sup})
    return pd.DataFrame(linhas)


def tabela_equivalencias(resultados):
    # Em quantos pedidos estrategias distintas dao a mesma distancia, por layout:
    # cada par, 'qualquer par' e 'as 4 iguais'.
    # Pedidos de 1 secao tem as 4 iguais por construcao (H4);
    # as colunas *_2mais_secoes repetem a contagem sem eles.
    dist = distancias_pareadas(resultados)
    varias = dados_do_pedido(resultados, dist.index)["n_secoes"].to_numpy() >= 2
    pares = list(combinations(ESTRATEGIAS, 2))
    linhas = []
    for layout in LAYOUTS:
        # Um conjunto de pares equivalentes por pedido.
        equivalentes = []
        for i in range(len(dist)):
            custos = {e: float(dist[(layout, e)].iloc[i]) for e in ESTRATEGIAS}
            equivalentes.append(set(pares_equivalentes(custos, TOLERANCIA_DISTANCIA)))
        casos = {f"{a} = {b}": [(a, b) in eq for eq in equivalentes] for a, b in pares}
        casos["qualquer par"] = [len(eq) > 0 for eq in equivalentes]
        casos["as 4 iguais"] = [len(eq) == len(pares) for eq in equivalentes]
        for caso, marcas in casos.items():
            marcas = np.array(marcas)
            nas_varias = marcas & varias
            linhas.append({"layout": layout, "caso": caso,
                           "n_pedidos": int(marcas.sum()), "pct_pedidos": 100 * float(marcas.mean()),
                           "n_pedidos_2mais_secoes": int(nas_varias.sum()),
                           "pct_pedidos_2mais_secoes": (100 * nas_varias.sum() / varias.sum()
                                                        if varias.any() else float("nan"))})
    return pd.DataFrame(linhas)


def classificar_ic(inferior, superior):
    # confirmada: IC inteiro acima de 0; contrariada: IC inteiro abaixo de 0; inconclusiva: o IC contem o 0.
    if inferior > 0:
        return "confirmada"
    if superior < 0:
        return "contrariada"
    return "inconclusiva"


def _linha_verificacao(hipotese, parte, estrategia, layout, n_pedidos, medida, valor, resultado,
                       inferior=np.nan, superior=np.nan):
    return {"hipotese": hipotese, "parte": parte, "estrategia": estrategia, "layout": layout,
            "n_pedidos": n_pedidos, "medida": medida, "valor": valor,
            "ic_inf": inferior, "ic_sup": superior, "resultado": resultado}


def _contagem_para_resultado(n_pedidos, n_violacoes):
    # 0 violacoes = confirmada; alguma = contrariada; sem pedidos = inconclusiva.
    if n_pedidos == 0:
        return "inconclusiva"
    return "confirmada" if n_violacoes == 0 else "contrariada"


def verificacao_hipoteses(resultados, reducao, ganhos, ganhos_faixa):
    # Confere H1 a H4 com os numeros do experimento, uma linha por criterio.
    # Recebe as tabelas ja calculadas, para nao refazer os bootstraps.
    #
    # resultado:
    #   - com IC (H1, H2 e o ganho de H3): confirmada, contrariada ou inconclusiva;
    #   - com contagem (opt <= demais, H4): confirmada se nenhum pedido viola o criterio;
    #   - 'ganho cresce com |S(o)|': so descritivo; conta as quedas do ganho medio entre faixas
    #     (0 quedas = confirmada, senao inconclusiva).
    # H1 e H2 tem tambem uma linha-resumo 'as 4': confirmada ou contrariada se as 4 estrategias
    # concordam, mista nos demais casos.
    dist = distancias_pareadas(resultados)
    pedido = dados_do_pedido(resultados, dist.index)
    n_pedidos = len(dist)
    linhas = []

    # H1 (L1 e L2 contra L0) e H2 (L1 contra L2): o lado positivo da reducao e o favoravel.
    for hipotese, comparacao in (("H1", "L1 vs L0"), ("H1", "L2 vs L0"), ("H2", "L1 vs L2")):
        da_parte = []
        for e in ESTRATEGIAS:
            r = reducao[(reducao["estrategia"] == e) & (reducao["comparacao"] == comparacao)].iloc[0]
            res = classificar_ic(r["ic_inf_pct"], r["ic_sup_pct"])
            da_parte.append(res)
            linhas.append(_linha_verificacao(hipotese, comparacao, e, "-", n_pedidos, "reducao_pct",
                                             r["reducao_pct"], res, r["ic_inf_pct"], r["ic_sup_pct"]))
        resumo_da_parte = da_parte[0] if len(set(da_parte)) == 1 else "mista"
        linhas.append(_linha_verificacao(hipotese, comparacao, "as 4", "-", n_pedidos, "resumo", np.nan,
                                         resumo_da_parte))

    # H3 (a): corr, nn e opt reduzem a distancia contra a ref.
    for layout in LAYOUTS:
        for e in ESTRATEGIAS_COM_CRITERIO:
            r = ganhos[(ganhos["layout"] == layout) & (ganhos["estrategia"] == e)].iloc[0]
            linhas.append(_linha_verificacao("H3", "ganho contra ref > 0", e, layout, n_pedidos, "ganho_pct",
                                             r["ganho_medio_pct"],
                                             classificar_ic(r["ic_inf_pct"], r["ic_sup_pct"]),
                                             r["ic_inf_pct"], r["ic_sup_pct"]))

    # H3 (b): opt nunca anda mais que as outras, pedido a pedido (exatos e heuristicos separados).
    heuristico = pedido["pedido_heuristico"].to_numpy()
    for layout in LAYOUTS:
        opt = dist[(layout, "opt")].to_numpy()
        outras = np.min([dist[(layout, e)].to_numpy() for e in ESTRATEGIAS if e != "opt"], axis=0)
        viola = opt > outras + TOLERANCIA_DISTANCIA
        for nome, grupo in (("pedidos exatos", ~heuristico), ("pedidos heuristicos", heuristico)):
            n, v = int(grupo.sum()), int((viola & grupo).sum())
            linhas.append(_linha_verificacao("H3", f"opt <= demais ({nome})", "opt", layout, n,
                                             "pedidos_violando", v, _contagem_para_resultado(n, v)))

    # H3 (c): o ganho cresce com |S(o)|? Descritivo: quedas do ganho medio entre faixas consecutivas.
    ordem = [nome for nome, _, _ in FAIXAS_SECOES]
    for layout in LAYOUTS:
        for e in ESTRATEGIAS_COM_CRITERIO:
            t = ganhos_faixa[(ganhos_faixa["layout"] == layout) & (ganhos_faixa["estrategia"] == e)]
            t = t.set_index("faixa_secoes")
            serie = t.loc[[f for f in ordem if f in t.index], "ganho_medio_pct"]
            quedas = int((serie.diff().dropna() < 0).sum())
            linhas.append(_linha_verificacao("H3", "ganho cresce com |S(o)| (faixas)", e, layout,
                                             int(t["n_pedidos"].sum()), "quedas_entre_faixas", quedas,
                                             "confirmada" if quedas == 0 else "inconclusiva"))

    # H4: em pedidos de 1 secao, as 4 estrategias dao a mesma distancia.
    uma_secao = pedido["n_secoes"].to_numpy() == 1
    for layout in LAYOUTS:
        todas = np.array([dist[(layout, e)].to_numpy() for e in ESTRATEGIAS])
        diferem = (todas.max(axis=0) - todas.min(axis=0)) > TOLERANCIA_DISTANCIA
        n, v = int(uma_secao.sum()), int((diferem & uma_secao).sum())
        linhas.append(_linha_verificacao("H4", "1 secao: as 4 estrategias iguais", "as 4", layout, n,
                                         "pedidos_diferentes", v, _contagem_para_resultado(n, v)))

    return pd.DataFrame(linhas, columns=COLUNAS_VERIFICACAO)


def main():
    g = grafo_padrao()
    # Dijkstra a partir de cada no, uma vez so.
    D = g.matriz_D()
    pedidos = carregar_pedidos_avaliacao()
    resultados = rodar_experimento(pedidos, g, D)

    PASTA_RESULTADOS.mkdir(exist_ok=True)
    resultados.to_csv(SAIDA_POR_PEDIDO, index=False)
    print(f"{len(resultados)} linhas ({len(pedidos)} pedidos x {len(LAYOUTS)} layouts x "
          f"{len(ESTRATEGIAS)} estrategias) salvas em {SAIDA_POR_PEDIDO}")

    distancia = tabela_distancia(resultados)
    distancia.to_csv(SAIDA_TABELA_DISTANCIA, index=False, float_format="%.3f")
    reducao = tabela_reducao_layouts(resultados)
    reducao.to_csv(SAIDA_TABELA_REDUCAO, index=False, float_format="%.3f")

    ganhos = tabela_ganho(resultados)
    ganhos.to_csv(SAIDA_TABELA_GANHO, index=False, float_format="%.3f")
    ganhos_faixa = tabela_ganho_faixa_secoes(resultados)
    ganhos_faixa.to_csv(SAIDA_TABELA_GANHO_FAIXA, index=False, float_format="%.3f")

    ganhos_corredores = tabela_ganho_faixa_corredores(resultados)
    ganhos_corredores.to_csv(SAIDA_TABELA_GANHO_CORREDORES, index=False, float_format="%.3f")
    tempo_turno = tabela_tempo_turno(resultados)
    tempo_turno.to_csv(SAIDA_TABELA_TEMPO, index=False, float_format="%.3f")

    equivalencias = tabela_equivalencias(resultados)
    equivalencias.to_csv(SAIDA_TABELA_EQUIVALENCIAS, index=False, float_format="%.3f")
    verificacao = verificacao_hipoteses(resultados, reducao, ganhos, ganhos_faixa)
    verificacao.to_csv(SAIDA_VERIFICACAO, index=False, float_format="%.3f")

    # Imprime os resultados no terminal.
    formato = lambda x: f"{x:.1f}"
    print("\nDistancia (m), media e IC de 95%:")
    print(distancia.to_string(index=False, float_format=formato))
    print("\nReducao entre layouts (%), com IC de 95%:")
    print(reducao.to_string(index=False, float_format=formato))
    print("\nGanho contra ref (%), com IC de 95%:")
    print(ganhos.to_string(index=False, float_format=formato))
    print("\nGanho de opt por faixa de |S(o)| (%) (o CSV traz as 3 estrategias):")
    print(ganhos_faixa[ganhos_faixa["estrategia"] == "opt"].to_string(index=False, float_format=formato))
    print("\nGanho de opt por faixa de corredores (%) (o CSV traz as 3 estrategias):")
    print(ganhos_corredores[ganhos_corredores["estrategia"] == "opt"].to_string(index=False, float_format=formato))
    print("\nTempo medio (s) e pedidos por turno, com IC de 95%:")
    print(tempo_turno.to_string(index=False, float_format=formato))
    print("\nPedidos com estrategias equivalentes (distancias iguais):")
    print(equivalencias.to_string(index=False, float_format=formato))
    print("\nVerificacao das hipoteses:")
    print(verificacao.drop(columns=["n_pedidos"]).to_string(index=False, float_format=formato))
    print("\nTabelas salvas em", PASTA_RESULTADOS)


if __name__ == "__main__":
    main()
