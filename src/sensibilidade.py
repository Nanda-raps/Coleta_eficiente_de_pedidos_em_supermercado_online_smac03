# Pergunta: se v, t_item e t_fixo fossem outros, as conclusoes mudariam?
# Como T = D/v + t_item * itens + t_fixo, e os dois ultimos termos dependem so do pedido,
# a ORDEM dos casos nao deve mudar; mudam o tamanho das diferencas e os pedidos por turno.
# Este script confere isso.
#
# Nao refaz rotas: le resultados/resultados_por_pedido.csv e so recalcula o tempo, em 10 cenarios
# (config.SENSIBILIDADE; o base e config.TEMPO): base, um parametro por vez (7),
# pessimista (tudo no pior) e otimista (tudo no melhor).
# Saidas: resultados/tabela_sensibilidade.csv e figuras/fig4_sensibilidade_pedidos_turno (PNG e PDF).
#
# Uso (depois de python src/experimento.py): python src/sensibilidade.py

import pandas as pd

from config import LAYOUTS, PASTA_RESULTADOS, SENSIBILIDADE, TEMPO
from graficos import PASTA_FIGURAS, figura_sensibilidade, ler_resultado
from indicadores import pedidos_por_turno, tempo_coleta
from rotas import ESTRATEGIAS

SAIDA_TABELA = PASTA_RESULTADOS / "tabela_sensibilidade.csv"


def cenarios():
    # Lista de cenarios (dicionarios): base, um parametro por vez (pulando o valor igual ao base),
    # pessimista e otimista.
    base = {"velocidade": TEMPO["velocidade"], "t_item": TEMPO["t_item"], "t_fixo": TEMPO["t_fixo"]}
    lista = [{"cenario": "base", "tipo": "base", "parametro": "-", **base}]
    for parametro, valores in SENSIBILIDADE.items():
        for valor in valores:
            if valor != base[parametro]:
                lista.append({"cenario": f"{parametro} = {valor}", "tipo": "um por vez",
                              "parametro": parametro, **{**base, parametro: valor}})
    v, t_item, t_fixo = SENSIBILIDADE["velocidade"], SENSIBILIDADE["t_item"], SENSIBILIDADE["t_fixo"]
    lista.append({"cenario": "pessimista", "tipo": "extremo", "parametro": "todos",
                  "velocidade": min(v), "t_item": max(t_item), "t_fixo": max(t_fixo)})
    lista.append({"cenario": "otimista", "tipo": "extremo", "parametro": "todos",
                  "velocidade": max(v), "t_item": min(t_item), "t_fixo": min(t_fixo)})
    return lista


def calcular_cenario(resultados, cenario):
    # Tempo medio e pedidos por turno de cada caso (layout x estrategia) em UM cenario.
    tempo = {**TEMPO, "velocidade": cenario["velocidade"], "t_item": cenario["t_item"],
             "t_fixo": cenario["t_fixo"]}
    linhas = []
    for layout in LAYOUTS:
        for e in ESTRATEGIAS:
            casos = resultados[(resultados["layout"] == layout) & (resultados["estrategia"] == e)]
            tempos = tempo_coleta(casos["distancia_m"].to_numpy(), casos["n_itens"].to_numpy(), tempo)
            linhas.append({"cenario": cenario["cenario"], "tipo": cenario["tipo"],
                           "parametro_variado": cenario["parametro"],
                           "velocidade_m_s": cenario["velocidade"], "t_item_s": cenario["t_item"],
                           "t_fixo_s": cenario["t_fixo"], "layout": layout, "estrategia": e,
                           "tempo_medio_s": float(tempos.mean()),
                           "pedidos_turno": pedidos_por_turno(tempos, tempo)})
    return linhas


def ordem_dos_casos(linhas):
    # Casos (layout, estrategia) do menor ao maior tempo medio; empate desfeito pelo nome.
    ordenadas = sorted(linhas, key=lambda l: (l["tempo_medio_s"], l["layout"], l["estrategia"]))
    return [(l["layout"], l["estrategia"]) for l in ordenadas]


def tabela_sensibilidade(resultados):
    # Tabela com todos os cenarios (120 linhas).
    # ranking_igual_ao_base = True se a ordem dos 12 casos neste cenario e a mesma do caso base.
    por_cenario = {c["cenario"]: calcular_cenario(resultados, c) for c in cenarios()}
    ordem_base = ordem_dos_casos(por_cenario["base"])
    linhas = []
    for nome, calculadas in por_cenario.items():
        igual = ordem_dos_casos(calculadas) == ordem_base
        linhas += [{**l, "ranking_igual_ao_base": igual} for l in calculadas]
    return pd.DataFrame(linhas)


def main():
    resultados = ler_resultado("resultados_por_pedido.csv")
    tabela = tabela_sensibilidade(resultados)
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    tabela.to_csv(SAIDA_TABELA, index=False, float_format="%.3f")
    figuras = figura_sensibilidade(tabela, PASTA_FIGURAS / "fig4_sensibilidade_pedidos_turno")

    # Resumo no terminal: pedidos por turno em L0 com ref e em L2 com opt, e se o ranking se manteve.
    pior = tabela[(tabela["layout"] == "L0") & (tabela["estrategia"] == "ref")].set_index("cenario")
    melhor = tabela[(tabela["layout"] == "L2") & (tabela["estrategia"] == "opt")].set_index("cenario")
    resumo = pd.DataFrame({"L0+ref": pior["pedidos_turno"], "L2+opt": melhor["pedidos_turno"],
                           "ranking igual ao base": pior["ranking_igual_ao_base"]})
    resumo["vantagem de L2+opt (%)"] = 100 * (resumo["L2+opt"] / resumo["L0+ref"] - 1)
    print("Pedidos por turno por cenario (L0 com ref contra L2 com opt):")
    print(resumo.to_string(float_format=lambda x: f"{x:.1f}"))
    print("\nSalvo em", SAIDA_TABELA, "e", ", ".join(c.name for c in figuras))


if __name__ == "__main__":
    main()
