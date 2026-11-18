# Gera as figuras do experimento a partir dos CSVs de resultados/ (nao recalcula nada).
# Cada figura sai em PNG (200 dpi) e em PDF (vetorial, para o LaTeX), em resultados/figuras/:
#   fig1_distancia_boxplot         distancia por layout, um painel por estrategia
#   fig2_reducao_layouts           reducao de L1 e L2 contra L0 e de L1 contra L2, com IC de 95% (H1, H2)
#   fig3_ganho_faixa_secoes        ganho contra ref por faixa de |S(o)|, um painel por layout (H3)
#   fig4_sensibilidade_pedidos_turno   pedidos por turno por cenario (gerada por sensibilidade.py)
#
# As funcoes dados_*, pontos_* e serie_* preparam os dados; as figura_* desenham.
# Cores: uma por layout (azul, laranja, aqua) e outras tres por estrategia (violeta, verde, magenta),
# para a mesma cor nunca valer duas coisas. Nenhuma figura depende so da cor:
# ha nome no eixo, marcadores e legenda.
#
# Uso (depois de python src/experimento.py): python src/graficos.py

import matplotlib
# Backend sem janela: so grava arquivos. Precisa vir antes de importar pyplot.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Patch

from config import LAYOUTS, PASTA_RESULTADOS
from experimento import COMPARACOES_LAYOUTS, ESTRATEGIAS_COM_CRITERIO, FAIXAS_SECOES
from rotas import ESTRATEGIAS

PASTA_FIGURAS = PASTA_RESULTADOS / "figuras"

# Cores neutras (fundo branco).
FUNDO = "#ffffff"
TINTA = "#0b0b0b"
TINTA_2 = "#52514e"
TINTA_3 = "#898781"
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"

# Uma cor por layout (igual em todas as figuras) e uma por estrategia; nomes mostrados nas legendas.
COR_LAYOUT = {"L0": "#2a78d6", "L1": "#eb6834", "L2": "#1baf7a"}
NOME_LAYOUT = {"L0": "aleatório", "L1": "afinidade (Lift)", "L2": "demanda"}

COR_ESTRATEGIA = {"corr": "#6250d6", "nn": "#008300", "opt": "#e87ba4"}
MARCADOR_ESTRATEGIA = {"corr": "o", "nn": "s", "opt": "^"}
NOME_ESTRATEGIA = {"ref": "ordem do carrinho", "corr": "por corredores",
                   "nn": "vizinho mais próximo", "opt": "rota de custo mínimo"}

# Estilo comum a todas as figuras: fontes, eixos, legenda sem moldura, fontes embutidas no PDF.
ESTILO = {
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "text.color": TINTA, "axes.titlecolor": TINTA, "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.edgecolor": EIXO,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.facecolor": FUNDO, "figure.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "legend.frameon": False, "pdf.fonttype": 42,
}


def formatar_pct(valor):
    # Percentual com sinal e virgula decimal: -6.7 vira -6,7%.
    return f"{valor:+.1f}%".replace(".", ",").replace("-", "−")


def salvar(fig, base):
    # Grava base.png (200 dpi) e base.pdf, fecha a figura e devolve os caminhos.
    # O PDF sai sem data de criacao, para ser identico a cada execucao.
    base.parent.mkdir(parents=True, exist_ok=True)
    png, pdf = base.with_suffix(".png"), base.with_suffix(".pdf")
    fig.savefig(png, dpi=200)
    fig.savefig(pdf, metadata={"CreationDate": None})
    plt.close(fig)
    return [png, pdf]


def dados_boxplot(resultados):
    # Distancias por estrategia e layout: {estrategia: {layout: array}}, na ordem de id_teste.
    ordenado = resultados.sort_values("id_teste")
    return {e: {layout: ordenado[(ordenado["estrategia"] == e) & (ordenado["layout"] == layout)]
                ["distancia_m"].to_numpy() for layout in LAYOUTS} for e in ESTRATEGIAS}


def pontos_floresta(reducao):
    # Pontos da figura 2: {comparacao: DataFrame por estrategia} com reducao_pct, ic_inf_pct, ic_sup_pct
    # e exclui_zero (IC inteiro de um lado do 0).
    pontos = {}
    for base, novo in COMPARACOES_LAYOUTS:
        comparacao = f"{novo} vs {base}"
        t = reducao[reducao["comparacao"] == comparacao].set_index("estrategia").loc[list(ESTRATEGIAS)]
        t = t[["reducao_pct", "ic_inf_pct", "ic_sup_pct"]].copy()
        t["exclui_zero"] = (t["ic_inf_pct"] > 0) | (t["ic_sup_pct"] < 0)
        pontos[comparacao] = t
    return pontos


def faixas_presentes(tabela):
    # Faixas de secoes que aparecem na tabela, na ordem de FAIXAS_SECOES.
    return [nome for nome, _, _ in FAIXAS_SECOES if nome in set(tabela["faixa_secoes"])]


def serie_ganho_faixa(tabela, layout, estrategia):
    # Linhas da tabela de ganho por faixa de um layout e uma estrategia, na ordem das faixas.
    t = tabela[(tabela["layout"] == layout) & (tabela["estrategia"] == estrategia)].set_index("faixa_secoes")
    return t.loc[[f for f in faixas_presentes(tabela) if f in t.index]].reset_index()


def figura_distancia(resultados, base):
    # Figura 1: distancia por layout, um painel por estrategia.
    # Caixa = quartis; linha branca = mediana; losango = media;
    # pontos soltos = pedidos fora de 1,5 x a distancia entre quartis.
    dados = dados_boxplot(resultados)
    with plt.rc_context(ESTILO):
        fig, eixos = plt.subplots(1, len(ESTRATEGIAS), sharey=True, figsize=(7.2, 3.6))
        for eixo, e in zip(eixos, ESTRATEGIAS):
            caixas = eixo.boxplot(
                [dados[e][layout] for layout in LAYOUTS], positions=range(len(LAYOUTS)), widths=0.55,
                patch_artist=True, showmeans=True,
                boxprops={"linewidth": 0}, medianprops={"color": FUNDO, "linewidth": 2},
                whiskerprops={"color": TINTA_2, "linewidth": 1}, capprops={"color": TINTA_2, "linewidth": 1},
                flierprops={"marker": "o", "markersize": 3, "markerfacecolor": "none",
                            "markeredgecolor": TINTA_3, "markeredgewidth": 0.8},
                meanprops={"marker": "D", "markersize": 5.5, "markerfacecolor": FUNDO,
                           "markeredgecolor": TINTA, "markeredgewidth": 1})
            for caixa, layout in zip(caixas["boxes"], LAYOUTS):
                caixa.set_facecolor(COR_LAYOUT[layout])
            eixo.set_xticks(range(len(LAYOUTS)), list(LAYOUTS))
            eixo.set_title(f"{e}\n{NOME_ESTRATEGIA[e]}")
            eixo.set_ylim(bottom=0)
            eixo.yaxis.grid(True, color=GRADE, linewidth=0.8)
            eixo.set_axisbelow(True)
            eixo.tick_params(axis="x", length=0)
        eixos[0].set_ylabel("Distância percorrida por pedido (m)")
        legenda = [Patch(facecolor=COR_LAYOUT[l], label=f"{l} · {NOME_LAYOUT[l]}") for l in LAYOUTS]
        legenda.append(Line2D([], [], marker="D", linestyle="", markersize=5.5, markerfacecolor=FUNDO,
                              markeredgecolor=TINTA, label="média"))
        fig.legend(handles=legenda, loc="lower center", ncol=len(legenda))
        fig.tight_layout(rect=(0, 0.08, 1, 1))
        return salvar(fig, base)


def figura_reducao(reducao, base):
    # Figura 2: reducao da distancia media entre layouts, com IC de 95%, um painel por comparacao.
    # Positivo = o layout novo anda menos. Circulo cheio = IC sem o 0; vazado = IC com o 0.
    # O valor so e escrito na linha do opt.
    pontos = pontos_floresta(reducao)
    todas = pd.concat(pontos.values())
    minimo, maximo = todas["ic_inf_pct"].min(), todas["ic_sup_pct"].max()
    folga = 0.08 * (maximo - minimo)
    # Posicao vertical de cada estrategia (ref no topo).
    y = {e: len(ESTRATEGIAS) - 1 - i for i, e in enumerate(ESTRATEGIAS)}
    with plt.rc_context(ESTILO):
        fig, eixos = plt.subplots(1, len(pontos), sharex=True, sharey=True, figsize=(7.2, 3.0))
        for eixo, (comparacao, tabela) in zip(eixos, pontos.items()):
            novo, base_ = comparacao.split(" vs ")
            eixo.axvline(0, color=TINTA_2, linewidth=1, zorder=1)
            for e, linha in tabela.iterrows():
                eixo.hlines(y[e], linha["ic_inf_pct"], linha["ic_sup_pct"], color=TINTA, linewidth=2, zorder=2)
                eixo.plot([linha["reducao_pct"]], [y[e]], linestyle="", marker="o", markersize=7,
                          markerfacecolor=TINTA if linha["exclui_zero"] else FUNDO,
                          markeredgecolor=TINTA, markeredgewidth=1.5, zorder=3)
                if e == "opt":
                    eixo.annotate(formatar_pct(linha["reducao_pct"]), (linha["reducao_pct"], y[e]),
                                  xytext=(0, 8), textcoords="offset points", ha="center",
                                  fontsize=8, color=TINTA_2)
            eixo.set_title(f"{novo} em relação a {base_}")
            eixo.set_yticks([y[e] for e in ESTRATEGIAS], list(ESTRATEGIAS))
            eixo.set_ylim(-0.7, len(ESTRATEGIAS) - 0.3)
            eixo.set_xlim(minimo - folga, maximo + folga)
            eixo.xaxis.grid(True, color=GRADE, linewidth=0.8)
            eixo.set_axisbelow(True)
            eixo.tick_params(axis="y", length=0)
            eixo.spines["left"].set_visible(False)
        fig.supxlabel("Redução da distância média (%): à direita do 0 o layout novo anda menos; à esquerda, anda mais",
                      fontsize=8.5, color=TINTA_2, y=0.01)
        legenda = [Line2D([], [], linestyle="", marker="o", markersize=7, markerfacecolor=TINTA,
                          markeredgecolor=TINTA, label="IC de 95% não contém 0"),
                   Line2D([], [], linestyle="", marker="o", markersize=7, markerfacecolor=FUNDO,
                          markeredgecolor=TINTA, markeredgewidth=1.5, label="IC de 95% contém 0")]
        fig.legend(handles=legenda, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.08))
        fig.tight_layout(rect=(0, 0.17, 1, 1))
        return salvar(fig, base)


def figura_ganho_faixa(tabela, base):
    # Figura 3: ganho contra ref por faixa de |S(o)|, um painel por layout, uma linha por estrategia.
    # Ponto = ganho medio; barra = IC de 95% (deslocada um pouco em x para nao sobrepor).
    # Faixas pequenas dao ICs largos: leia a tendencia.
    faixas = faixas_presentes(tabela)
    deslocamento = dict(zip(ESTRATEGIAS_COM_CRITERIO, np.linspace(-0.13, 0.13, len(ESTRATEGIAS_COM_CRITERIO))))
    topo = np.ceil(tabela["ic_sup_pct"].max() / 10) * 10 + 5
    # Rotulo de cada faixa: nome, '*' se o opt e heuristico nela, e numero de pedidos.
    rotulos = []
    for f in faixas:
        linhas = tabela[tabela["faixa_secoes"] == f]
        heuristica = (linhas["n_pedidos_opt_heuristico"] > 0).any()
        rotulos.append(f"{f}{'*' if heuristica else ''} (n={int(linhas['n_pedidos'].iloc[0])})")
    n_heuristicos = int(tabela["n_pedidos_opt_heuristico"].max())
    with plt.rc_context(ESTILO):
        fig, eixos = plt.subplots(1, len(LAYOUTS), sharex=True, sharey=True, figsize=(7.2, 3.9))
        for eixo, layout in zip(eixos, LAYOUTS):
            for e in ESTRATEGIAS_COM_CRITERIO:
                s = serie_ganho_faixa(tabela, layout, e)
                x = np.array([faixas.index(f) for f in s["faixa_secoes"]]) + deslocamento[e]
                y = s["ganho_medio_pct"].to_numpy()
                eixo.errorbar(x, y, yerr=[y - s["ic_inf_pct"].to_numpy(), s["ic_sup_pct"].to_numpy() - y],
                              color=COR_ESTRATEGIA[e], marker=MARCADOR_ESTRATEGIA[e], markersize=6,
                              markeredgecolor=FUNDO, markeredgewidth=0.8, linewidth=1.5, elinewidth=1,
                              capsize=0, label=e)
            eixo.set_title(f"{layout} · {NOME_LAYOUT[layout]}")
            eixo.set_xticks(range(len(faixas)), rotulos, rotation=45, ha="right", rotation_mode="anchor")
            eixo.set_ylim(0, topo)
            eixo.yaxis.grid(True, color=GRADE, linewidth=0.8)
            eixo.set_axisbelow(True)
        eixos[0].set_ylabel("Ganho contra ref (%)")
        eixos[0].legend(loc="upper left")
        fig.supxlabel("Seções distintas do pedido, |S(o)|  (n = número de pedidos na faixa)", fontsize=8.5,
                      color=TINTA_2, y=0.05)
        if n_heuristicos:
            fig.text(0.01, 0.005, f"* {n_heuristicos} pedidos com mais de 15 seções: nesses, opt é heurística (não exata).",
                     fontsize=7.5, color=TINTA_2, ha="left", va="bottom")
        fig.tight_layout(rect=(0, 0.1, 1, 1))
        return salvar(fig, base)


def dados_sensibilidade(tabela):
    # Pedidos por turno nos cenarios pessimista, base e otimista: DataFrame por (layout, estrategia).
    tres = tabela[tabela["cenario"].isin(["pessimista", "base", "otimista"])]
    larga = tres.pivot(index=["layout", "estrategia"], columns="cenario", values="pedidos_turno")
    return larga.loc[[(l, e) for l in LAYOUTS for e in ESTRATEGIAS], ["pessimista", "base", "otimista"]]


def _legenda_cenario(tabela, cenario, nome):
    # Texto com os parametros de um cenario, para a nota da figura 4.
    c = tabela[tabela["cenario"] == cenario].iloc[0]
    v = f"{c['velocidade_m_s']:g}".replace(".", ",")
    return f"{nome}: v = {v} m/s, {c['t_item_s']:g} s por item, {c['t_fixo_s']:g} s fixos"


def figura_sensibilidade(tabela, base):
    # Figura 4: pedidos por turno em cada caso, um painel por layout.
    # Barra cinza = do cenario pessimista ao otimista; ponto = caso base.
    # Numeros so nos dois casos que a analise compara (L0 com ref e L2 com opt).
    # Mostra que a ordem dos casos nao muda, mas os pedidos por turno dependem das premissas de tempo.
    dados = dados_sensibilidade(tabela)
    destaques = {("L0", "ref"), ("L2", "opt")}
    topo = np.ceil(dados["otimista"].max() / 20) * 20
    with plt.rc_context(ESTILO):
        fig, eixos = plt.subplots(1, len(LAYOUTS), sharey=True, figsize=(7.2, 3.7))
        for eixo, layout in zip(eixos, LAYOUTS):
            for x, e in enumerate(ESTRATEGIAS):
                pessimista, valor_base, otimista = dados.loc[(layout, e), ["pessimista", "base", "otimista"]]
                eixo.plot([x, x], [pessimista, otimista], color=EIXO, linewidth=8, solid_capstyle="round", zorder=2)
                eixo.plot([x], [valor_base], linestyle="", marker="o", markersize=7, markerfacecolor=TINTA,
                          markeredgecolor=FUNDO, markeredgewidth=1.2, zorder=3)
                if (layout, e) in destaques:
                    eixo.annotate(f"{otimista:.0f}", (x, otimista), xytext=(0, 6), textcoords="offset points",
                                  ha="center", va="bottom", fontsize=8, color=TINTA_2)
                    eixo.annotate(f"{pessimista:.0f}", (x, pessimista), xytext=(0, -7), textcoords="offset points",
                                  ha="center", va="top", fontsize=8, color=TINTA_2)
            eixo.set_title(f"{layout} · {NOME_LAYOUT[layout]}")
            eixo.set_xticks(range(len(ESTRATEGIAS)), list(ESTRATEGIAS))
            eixo.set_xlim(-0.6, len(ESTRATEGIAS) - 0.4)
            eixo.set_ylim(0, topo)
            eixo.yaxis.grid(True, color=GRADE, linewidth=0.8)
            eixo.set_axisbelow(True)
            eixo.tick_params(axis="x", length=0)
        eixos[0].set_ylabel("Pedidos por turno (8 h)")
        legenda = [Line2D([], [], color=EIXO, linewidth=8, solid_capstyle="round",
                          label="faixa: do cenário pessimista ao otimista"),
                   Line2D([], [], linestyle="", marker="o", markersize=7, markerfacecolor=TINTA,
                          markeredgecolor=FUNDO, label="caso base")]
        fig.legend(handles=legenda, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 0.075))
        nota = " | ".join([_legenda_cenario(tabela, "base", "Base"),
                           _legenda_cenario(tabela, "pessimista", "Pessimista"),
                           _legenda_cenario(tabela, "otimista", "Otimista")])
        fig.text(0.5, 0.005, nota, fontsize=7, color=TINTA_2, ha="center", va="bottom")
        fig.tight_layout(rect=(0, 0.16, 1, 1))
        return salvar(fig, base)


def ler_resultado(nome):
    # Le um CSV de resultados/; erro se nao existir (rode antes experimento.py).
    caminho = PASTA_RESULTADOS / nome
    if not caminho.exists():
        raise FileNotFoundError(f"Nao encontrei {caminho}. Rode antes: python src/experimento.py")
    return pd.read_csv(caminho)


def main():
    resultados = ler_resultado("resultados_por_pedido.csv")
    reducao = ler_resultado("tabela_reducao_layouts.csv")
    faixas = ler_resultado("tabela_ganho_faixa_secoes.csv")
    gravados = (figura_distancia(resultados, PASTA_FIGURAS / "fig1_distancia_boxplot")
                + figura_reducao(reducao, PASTA_FIGURAS / "fig2_reducao_layouts")
                + figura_ganho_faixa(faixas, PASTA_FIGURAS / "fig3_ganho_faixa_secoes"))
    print(f"{len(gravados)} arquivos gravados em {PASTA_FIGURAS}:")
    for caminho in gravados:
        print("  ", caminho.name)


if __name__ == "__main__":
    main()
