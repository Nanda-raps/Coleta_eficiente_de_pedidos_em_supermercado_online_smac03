"""Analise de sensibilidade dos parametros de tempo (v, t_item, t_fixo).

Os valores de tempo sao premissas do grupo (modelagem 3.5), nao medidas. A pergunta aqui e: se esses valores
estivessem diferentes, as conclusoes mudariam? Como T(o) = D/v + t_item * |o| + t_fixo, e os dois ultimos
termos dependem so do pedido (nao da rota nem do layout), a ORDEM dos casos nao deveria mudar; o que muda e
o tamanho das diferencas, os minutos e os pedidos por turno. Este script confere isso.

Nao refaz nenhuma rota: le resultados/resultados_por_pedido.csv (distancia e itens de cada pedido) e so
recalcula o tempo. Cenarios (config.SENSIBILIDADE; o caso base e config.TEMPO):
    base           os valores de config.TEMPO
    um por vez     um parametro assume cada um de seus outros valores, os demais ficam no base (7 cenarios)
    pessimista     tudo no pior: v minima, t_item e t_fixo maximos
    otimista       tudo no melhor: v maxima, t_item e t_fixo minimos
Sao 10 cenarios x 12 casos (3 layouts x 4 estrategias) = 120 linhas.

Saidas (em resultados/):
    tabela_sensibilidade.csv
    figuras/fig4_sensibilidade_pedidos_turno.png e .pdf   (pedidos por turno: faixa pessimista a otimista)

Uso (na raiz do repositorio, depois de rodar python src/experimento.py):
    python src/sensibilidade.py
"""
import pandas as pd

from config import LAYOUTS, PASTA_RESULTADOS, SENSIBILIDADE, TEMPO
from graficos import PASTA_FIGURAS, figura_sensibilidade, ler_resultado
from indicadores import pedidos_por_turno, tempo_coleta
from rotas import ESTRATEGIAS

SAIDA_TABELA = PASTA_RESULTADOS / "tabela_sensibilidade.csv"


def cenarios():
    """Lista dos cenarios, cada um um dicionario: cenario, tipo, parametro, velocidade, t_item, t_fixo.

    A ordem e: base, um por vez (velocidade, t_item e t_fixo, pulando o valor igual ao do base),
    pessimista e otimista.
    """
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
    """Tempo medio e pedidos por turno de cada caso (layout x estrategia) em UM cenario.

    resultados: o DataFrame de resultados_por_pedido.csv (precisa de layout, estrategia, distancia_m, n_itens).
    O tempo de cada pedido usa indicadores.tempo_coleta, e os pedidos por turno, indicadores.pedidos_por_turno
    (H dividido pela MEDIA dos tempos). Devolve uma lista de dicionarios, um por caso.
    """
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
    """Os casos (layout, estrategia) do menor para o maior tempo medio; empate desfeito pelo nome."""
    ordenadas = sorted(linhas, key=lambda l: (l["tempo_medio_s"], l["layout"], l["estrategia"]))
    return [(l["layout"], l["estrategia"]) for l in ordenadas]


def tabela_sensibilidade(resultados):
    """Tabela com todos os cenarios (120 linhas).

    ranking_igual_ao_base: True se, neste cenario, a ordem dos 12 casos por tempo medio e a mesma do caso base.
    E uma propriedade do cenario inteiro, repetida nas linhas dele.
    """
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

    # resumo: pedidos por turno em dois casos de referencia, e se o ranking se manteve
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
