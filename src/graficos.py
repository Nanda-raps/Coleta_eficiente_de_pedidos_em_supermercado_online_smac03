"""Figuras do experimento (so le resultados/, nao recalcula nada).

Gera tres figuras, cada uma em PNG (200 dpi) e em PDF (vetorial, para o LaTeX), em resultados/figuras/:

    fig1_distancia_boxplot       distancia por layout, um painel por estrategia (boxplots)
    fig2_reducao_layouts         reducao de L1 e L2 contra L0 e de L1 contra L2, com IC de 95% (H1 e H2)
    fig3_ganho_faixa_secoes      ganho contra ref por faixa de |S(o)|, um painel por layout (H3)

Uso (na raiz do repositorio, depois de rodar python src/experimento.py):
    python src/graficos.py

Estrutura (igual a do experimento.py): funcoes que PREPARAM os dados (dados_*, pontos_*, serie_*), faceis
de testar, e funcoes que DESENHAM (figura_*), que recebem os dados e o caminho de saida.

Cores (validadas com o script da skill de visualizacao, sobre fundo branco):
    layouts     azul, laranja, aqua      -> a mesma cor em toda figura que mostra layouts
    estrategias violeta, verde, magenta  -> outras tres cores, para a mesma cor nunca valer duas coisas
Nenhuma figura depende so da cor: os layouts tem o nome no eixo, e as estrategias tem marcadores e legenda.
"""
import matplotlib
matplotlib.use("Agg")                       # grava arquivos, sem abrir janela
import matplotlib.pyplot as plt             # noqa: E402
import numpy as np                          # noqa: E402
import pandas as pd                         # noqa: E402
from matplotlib.lines import Line2D         # noqa: E402
from matplotlib.patches import Patch        # noqa: E402

from config import LAYOUTS, PASTA_RESULTADOS                                           # noqa: E402
from experimento import COMPARACOES_LAYOUTS, ESTRATEGIAS_COM_CRITERIO, FAIXAS_SECOES  # noqa: E402
from rotas import ESTRATEGIAS                                                          # noqa: E402

PASTA_FIGURAS = PASTA_RESULTADOS / "figuras"

# Tintas e superficies (paleta de referencia da skill de visualizacao, modo claro, fundo branco)
FUNDO = "#ffffff"
TINTA = "#0b0b0b"           # texto principal e marcas neutras
TINTA_2 = "#52514e"         # texto secundario
TINTA_3 = "#898781"         # eixos e rotulos discretos
GRADE = "#e1e0d9"
EIXO = "#c3c2b7"

COR_LAYOUT = {"L0": "#2a78d6", "L1": "#eb6834", "L2": "#1baf7a"}
NOME_LAYOUT = {"L0": "aleatório", "L1": "afinidade (Lift)", "L2": "demanda"}

COR_ESTRATEGIA = {"corr": "#6250d6", "nn": "#008300", "opt": "#e87ba4"}
MARCADOR_ESTRATEGIA = {"corr": "o", "nn": "s", "opt": "^"}
NOME_ESTRATEGIA = {"ref": "ordem do carrinho", "corr": "por corredores",
                   "nn": "vizinho mais próximo", "opt": "rota de custo mínimo"}

ESTILO = {
    "font.size": 9, "axes.titlesize": 9, "axes.labelsize": 9,
    "xtick.labelsize": 8, "ytick.labelsize": 8, "legend.fontsize": 8,
    "text.color": TINTA, "axes.titlecolor": TINTA, "axes.labelcolor": TINTA_2,
    "xtick.color": TINTA_2, "ytick.color": TINTA_2, "axes.edgecolor": EIXO,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.facecolor": FUNDO, "figure.facecolor": FUNDO, "savefig.facecolor": FUNDO,
    "legend.frameon": False, "pdf.fonttype": 42,        # fontes embutidas no PDF
}


def formatar_pct(valor):
    """Percentual no padrao brasileiro, com sinal: -6.7 vira '−6,7%'."""
    return f"{valor:+.1f}%".replace(".", ",").replace("-", "−")


def salvar(fig, base):
    """Grava base.png (200 dpi) e base.pdf e fecha a figura. Devolve os dois caminhos.

    O PDF sai sem data de criacao, para o arquivo ser identico a cada execucao.
    """
    base.parent.mkdir(parents=True, exist_ok=True)
    png, pdf = base.with_suffix(".png"), base.with_suffix(".pdf")
    fig.savefig(png, dpi=200)
    fig.savefig(pdf, metadata={"CreationDate": None})
    plt.close(fig)
    return [png, pdf]


# ---- preparacao dos dados ---------------------------------------------------------------
def dados_boxplot(resultados):
    """Distancias de cada pedido: dicionario estrategia -> layout -> array (na ordem de id_teste)."""
    ordenado = resultados.sort_values("id_teste")
    return {e: {layout: ordenado[(ordenado["estrategia"] == e) & (ordenado["layout"] == layout)]
                ["distancia_m"].to_numpy() for layout in LAYOUTS} for e in ESTRATEGIAS}


def pontos_floresta(reducao):
    """Pontos da Figura 2: dicionario comparacao ("L1 vs L0", ...) -> DataFrame indexado por estrategia.

    Colunas: reducao_pct, ic_inf_pct, ic_sup_pct e exclui_zero (True se o IC inteiro esta de um lado do 0).
    """
    pontos = {}
    for base, novo in COMPARACOES_LAYOUTS:
        comparacao = f"{novo} vs {base}"
        t = reducao[reducao["comparacao"] == comparacao].set_index("estrategia").loc[list(ESTRATEGIAS)]
        t = t[["reducao_pct", "ic_inf_pct", "ic_sup_pct"]].copy()
        t["exclui_zero"] = (t["ic_inf_pct"] > 0) | (t["ic_sup_pct"] < 0)
        pontos[comparacao] = t
    return pontos


def faixas_presentes(tabela):
    """Nomes das faixas de secoes que aparecem na tabela, na ordem de FAIXAS_SECOES."""
    return [nome for nome, _, _ in FAIXAS_SECOES if nome in set(tabela["faixa_secoes"])]


def serie_ganho_faixa(tabela, layout, estrategia):
    """Linhas de tabela_ganho_faixa_secoes de um layout e uma estrategia, na ordem das faixas."""
    t = tabela[(tabela["layout"] == layout) & (tabela["estrategia"] == estrategia)].set_index("faixa_secoes")
    return t.loc[[f for f in faixas_presentes(tabela) if f in t.index]].reset_index()


# ---- figuras ----------------------------------------------------------------------------
def figura_distancia(resultados, base):
    """Figura 1: distancia percorrida por layout, um painel por estrategia. Caixa = quartis; linha branca =
    mediana; losango = media; pontos soltos = pedidos fora de 1,5 x a distancia entre quartis."""
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
    """Figura 2: reducao da distancia media entre layouts, com IC de 95%, um painel por comparacao.

    Positivo = o layout "novo" anda menos que o "base". Circulo cheio: o IC nao contem 0;
    vazado: contem. O valor so e escrito na linha de opt (as demais se leem no eixo e na tabela).
    """
    pontos = pontos_floresta(reducao)
    todas = pd.concat(pontos.values())
    minimo, maximo = todas["ic_inf_pct"].min(), todas["ic_sup_pct"].max()
    folga = 0.08 * (maximo - minimo)
    y = {e: len(ESTRATEGIAS) - 1 - i for i, e in enumerate(ESTRATEGIAS)}        # ref no topo
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
            eixo.spines["left"].set_visible(False)              # as linhas de grade ja marcam a escala
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
    """Figura 3: ganho contra ref por faixa de |S(o)|, um painel por layout, uma linha por estrategia.

    Pontos = ganho medio; barras = IC de 95% (deslocadas um pouco no eixo x para nao se sobrepor).
    Cada faixa tem poucos pedidos (n no eixo), entao os ICs sao largos: leia a tendencia.
    """
    faixas = faixas_presentes(tabela)
    deslocamento = dict(zip(ESTRATEGIAS_COM_CRITERIO, np.linspace(-0.13, 0.13, len(ESTRATEGIAS_COM_CRITERIO))))
    topo = np.ceil(tabela["ic_sup_pct"].max() / 10) * 10 + 5
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


# ---- execucao ---------------------------------------------------------------------------
def ler_resultado(nome):
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
