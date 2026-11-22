"""
Gera as figuras dos grafos da modelagem (Cenário 1 e Cenário 2).

    Cenário 1: grafo multicamadas M = (G, C)  -> camada lógica G2 + camada física G1
    Cenário 2: grafo único G (= G1)           -> planta física colorida por rho(p)

Uso:
    python modelagem/gerar_grafos_modelagem.py                # Cenário 1 com L1 e Cenário 2 com L2
    python modelagem/gerar_grafos_modelagem.py --layout L0    # força outro layout (arquivo ganha sufixo _L0)
    python modelagem/gerar_grafos_modelagem.py --cenario 1
    python modelagem/gerar_grafos_modelagem.py --cenario 2
    

Dependências: pandas, numpy, matplotlib, networkx
"""
from __future__ import annotations

import argparse
import warnings
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from matplotlib.collections import LineCollection
from matplotlib.colors import Normalize
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


N_CORREDORES = 17
COMPRIMENTO = 20.0
DX = 4.0
X_MAX = (N_CORREDORES - 1) * DX
H_LATERAL = 0.0
X_ENTRADA = 0.0
X_CAIXA = X_MAX
N_POS_MAX = 8


COR_FUNDO_LOJA = "#F8FAFC"
COR_EIXO = "#94A3B8"
COR_TRANSVERSAL = "#334155"
COR_VP = "#0F172A"
COR_SLOT = "#38BDF8"
COR_SLOT_BORDA = "#0369A1"
COR_ENTRADA = "#16A34A"
COR_CAIXA = "#DC2626"
COR_ARESTA_G2 = "#D97706"
COR_NO_G2 = "#FDE68A"
COR_NO_G2_BORDA = "#B45309"
_ORDEM_TAB20 = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18, 1, 3, 5, 7, 9, 11, 13]
COR_CORREDOR = {c: plt.cm.tab20(_ORDEM_TAB20[c - 1]) for c in range(1, 18)}

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "axes.titleweight": "bold",
    }
)


@dataclass
class Loja:

    slots: pd.DataFrame
    grafo: nx.Graph
    rho: np.ndarray

    @property
    def n_slots(self) -> int:
        return len(self.slots)


def localizar_layout(raiz: Path, layout: str) -> Path | None:
    pasta = raiz / "dados" / "layouts"
    cands = sorted(pasta.glob(f"layout_{layout}*.csv")) if pasta.exists() else []
    cands.sort(key=lambda p_: (0 if "final" in p_.stem else 1, p_.name))
    return cands[0] if cands else None


def carregar_layout(raiz: Path, layout: str = "L0") -> pd.DataFrame:
    csv = localizar_layout(raiz, layout)
    if csv is not None:
        df = pd.read_csv(csv)
        df = df.sort_values(["corredor", "posicao_na_frente"]).reset_index(drop=True)
        if "aisle_id" not in df.columns:
            warnings.warn(f"{csv.name} não tem a coluna 'aisle_id': usando a ordem das linhas como id da seção.")
            df["aisle_id"] = np.arange(1, len(df) + 1)
        print(f"Layout {layout} lido de: {csv}")
        return df

    warnings.warn(f"layout_{layout}*.csv não encontrado em dados/layouts/: usando layout sintético de 134 slots.")
    linhas = []
    for c in range(1, N_CORREDORES + 1):
        n = 7 if c in (16, 17) else 8
        linhas += [(c, p) for p in range(1, n + 1)]
    df = pd.DataFrame(linhas, columns=["corredor", "posicao_na_frente"])
    df["aisle_id"] = np.arange(1, len(df) + 1)
    return df


def construir_loja(df_layout: pd.DataFrame) -> Loja:
    passo = COMPRIMENTO / N_POS_MAX
    reg = []
    for i, r in df_layout.iterrows():
        c, p = int(r["corredor"]), int(r["posicao_na_frente"])
        x = (c - 1) * DX
        reg.append(dict(idx=i, aisle_id=int(r["aisle_id"]), corredor=c, pos=p, x_eixo=x,
                        y=passo * (p - 0.5), x_slot=x + H_LATERAL))
    slots = pd.DataFrame(reg)


    g = nx.Graph()
    manh = lambda a_, b_: abs(a_[0] - b_[0]) + abs(a_[1] - b_[1])
    pos = {"ENTRADA": (X_ENTRADA, 0.0), "CAIXA": (X_CAIXA, 0.0)}
    for c in range(1, N_CORREDORES + 1):
        x = (c - 1) * DX
        pos[f"VPf{c}"], pos[f"VPt{c}"] = (x, 0.0), (x, COMPRIMENTO)

    def aresta(a_, b_):
        g.add_edge(a_, b_, weight=manh(pos[a_], pos[b_]))

    for c in range(1, N_CORREDORES):
        aresta(f"VPf{c}", f"VPf{c + 1}")
        aresta(f"VPt{c}", f"VPt{c + 1}")
    aresta("ENTRADA", "VPf1")
    aresta("CAIXA", f"VPf{N_CORREDORES}")

    for c, grp in slots.groupby("corredor"):
        cadeia = [f"VPf{c}"]
        for _, s in grp.iterrows():
            k = int(s["idx"])
            pos[f"S{k}"] = (s.x_eixo, s.y)
            cadeia.append(f"S{k}")
        cadeia.append(f"VPt{c}")
        for u, v in zip(cadeia[:-1], cadeia[1:]):
            aresta(u, v)

    d_ent = nx.single_source_dijkstra_path_length(g, "ENTRADA")
    d_cai = nx.single_source_dijkstra_path_length(g, "CAIXA")
    rho = np.array([d_ent[f"S{i}"] + d_cai[f"S{i}"] for i in slots["idx"]])
    return Loja(slots=slots, grafo=g, rho=rho)


def carregar_arestas_g2(raiz: Path, ids: list[int]) -> tuple[list[tuple[int, int, float]], bool]:
    validos = set(ids)
    dados = raiz / "dados"
    candidatos = list(dados.rglob("*coocor*.csv")) + list(dados.rglob("*lift*.csv")) if dados.exists() else []
    for arq in candidatos:
        try:
            df = pd.read_csv(arq)
            if df.shape[1] < 3:
                continue
            u = df.iloc[:, 0].astype(int).to_numpy()
            v = df.iloc[:, 1].astype(int).to_numpy()
            w = df.iloc[:, 2].astype(float).to_numpy()
            if min(u.min(), v.min()) == 0 and 0 not in validos:
                u, v = u + 1, v + 1
            ok = np.isin(u, list(validos)) & np.isin(v, list(validos)) & (u != v)
            arestas = list(zip(u[ok].tolist(), v[ok].tolist(), w[ok].tolist()))
            if arestas:
                print(f"Arestas de G2 lidas de: {arq}")
                return arestas, True
        except Exception as e:
            warnings.warn(f"Falha ao ler {arq}: {e}")

    warnings.warn("Arquivo de coocorrência/lift não encontrado: G2 será ILUSTRATIVO (sintético).")
    rng = np.random.default_rng(42)
    ids_ord = sorted(ids)
    n = len(ids_ord)
    arestas = []
    bloco = np.arange(n) // 12
    for i in range(n):
        for j in range(i + 1, n):
            if bloco[i] == bloco[j] and rng.random() < 0.55:
                arestas.append((ids_ord[i], ids_ord[j], float(rng.uniform(1.8, 4.0))))
            elif rng.random() < 0.03:
                arestas.append((ids_ord[i], ids_ord[j], float(rng.uniform(1.05, 2.0))))
    return arestas, False


FIG_W = 3.35
FS = 6.0
FS_S = 5.5
plt.rcParams.update({"font.size": FS, "axes.titlesize": FS + 1, "legend.fontsize": FS_S})


def fmt(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


def pts_por_unidade(fig, ax):
    ax.apply_aspect()
    caixa = ax.get_window_extent()
    xl, yl = ax.get_xlim(), ax.get_ylim()
    return min(caixa.width / (xl[1] - xl[0]), caixa.height / (yl[1] - yl[0])) * 72.0 / fig.dpi


def area(ppu: float, lado: float, losango: bool = False) -> float:
    s_ = (lado * ppu) ** 2
    return s_ / 2.0 if losango else s_


def salvar(fig, saida: Path):
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, dpi=600, bbox_inches="tight", pad_inches=0.02, facecolor="white")
    plt.close(fig)
    print(f"Salvo: {saida}")


def gerar_cenario2(raiz: Path, saida: Path, com_titulo: bool = False, layout: str = "L2") -> None:
    loja = construir_loja(carregar_layout(raiz, layout))
    s = loja.slots
    fig, ax = plt.subplots(figsize=(FIG_W, 1.55))
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(-3, X_MAX + 3)
    ax.set_ylim(-7, COMPRIMENTO + 2.0)
    ax.axis("off")
    ax.add_patch(Rectangle((-2.0, -1.4), X_MAX + 4.0, COMPRIMENTO + 2.8, fc=COR_FUNDO_LOJA, ec=COR_EIXO,
                           lw=0.5, zorder=0))
    for y in (0.0, COMPRIMENTO):
        ax.plot([0, X_MAX], [y, y], color=COR_TRANSVERSAL, lw=1.0, zorder=2)
    for c in range(1, N_CORREDORES + 1):
        x = (c - 1) * DX
        ax.plot([x, x], [0, COMPRIMENTO], color=COR_EIXO, lw=0.7, zorder=2)
        ax.text(x, -2.8, f"{c}", ha="center", va="center", fontsize=FS_S, fontweight="bold", color=COR_VP)
    norm = Normalize(vmin=loja.rho.min(), vmax=loja.rho.max())
    sm = plt.cm.ScalarMappable(norm=norm, cmap="viridis_r")
    cb = fig.colorbar(sm, ax=ax, fraction=0.025, pad=0.06, aspect=18)
    cb.set_ticks([loja.rho.min(), loja.rho.max()])
    cb.set_ticklabels([fmt(loja.rho.min()), fmt(loja.rho.max())])
    cb.ax.tick_params(labelsize=FS_S, length=1.5, width=0.4, pad=1)
    cb.outline.set_linewidth(0.4)
    cb.set_label(r"$\rho(p)$ [m]", fontsize=FS)
    cb.ax.yaxis.set_label_coords(3.2, 0.5)

    ppu = pts_por_unidade(fig, ax)
    xs = np.repeat(np.arange(N_CORREDORES) * DX, 2)
    ys = np.tile([0.0, COMPRIMENTO], N_CORREDORES)
    ax.scatter(xs, ys, marker="D", s=area(ppu, 1.0, True), c=COR_VP, edgecolors="none", zorder=5)
    ax.scatter(s.x_slot, s.y, s=area(ppu, 0.85), marker="s", c=loja.rho, cmap="viridis_r", norm=norm,
               edgecolors="#0F172A", linewidths=0.2, zorder=6)
    for x, cor, face, nome in ((X_ENTRADA, COR_ENTRADA, "#DCFCE7", "ENTRADA"), (X_CAIXA, COR_CAIXA, "#FEE2E2", "CAIXA")):
        ax.scatter([x], [0], s=area(ppu, 1.5), marker="s", facecolor=face, edgecolor=cor, lw=0.7, zorder=7)
        ax.scatter([x], [0], s=area(ppu, 1.0, True), marker="D", c=COR_VP, edgecolors="none", zorder=8)
        ax.text(x, -5.0, nome, ha="center", va="top", fontsize=FS_S, fontweight="bold", color=cor)

    if com_titulo:
        ax.set_title(rf"Cenário 2: grafo único $G=(V,E,w)$", fontsize=FS + 1, fontweight="bold", pad=3)
    ax.legend(handles=[
        Line2D([], [], marker="D", ls="None", color=COR_VP, markersize=1.0 * ppu / 1.414, label="ponto de passagem"),
        Line2D([], [], marker="s", ls="None", markerfacecolor="#2A788E", markeredgecolor="#0F172A", markersize=0.85 * ppu,
               markeredgewidth=0.2, label=r"slot (cor $=\rho$)"),
        Line2D([], [], ls="None", label="nº = corredor"),
    ], loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=3, fontsize=FS_S, frameon=False,
        handletextpad=0.3, columnspacing=1.2)
    salvar(fig, saida)


def gerar_cenario1(raiz: Path, saida: Path, max_arestas: int = 0, com_titulo: bool = False,
                   layout: str = "L1") -> None:
    loja = construir_loja(carregar_layout(raiz, layout))
    n = loja.n_slots
    ids = loja.slots["aisle_id"].tolist()
    arestas, real = carregar_arestas_g2(raiz, ids)
    slot_de = {a_: i for i, a_ in enumerate(ids)}
    arestas = [(slot_de[u], slot_de[v], w_) for u, v, w_ in arestas]

    def proj(x, y, z=0.0):
        return x + 0.7 * y, 0.6 * y + z

    Z_SUP = 20.0
    s = loja.slots
    xs, ys = s["x_slot"].to_numpy(), s["y"].to_numpy()
    cores_slot = [COR_CORREDOR[int(c)] for c in s["corredor"]]

    fig, ax = plt.subplots(figsize=(FIG_W, 1.6))
    fig.subplots_adjust(left=0.0, right=1.0, top=1.0, bottom=0.0)
    ax.set_xlim(-17, 86)
    ax.set_ylim(-8, proj(0, COMPRIMENTO + 2.5, Z_SUP)[1] + 1)
    ax.set_aspect("equal", adjustable="box")
    ax.axis("off")
    ppu = pts_por_unidade(fig, ax)

    def plano(z, face, edge):
        pts = [proj(-2.5, -2.5, z), proj(X_MAX + 2.5, -2.5, z), proj(X_MAX + 2.5, COMPRIMENTO + 2.5, z),
               proj(-2.5, COMPRIMENTO + 2.5, z)]
        ax.add_patch(plt.Polygon(pts, closed=True, fc=face, ec=edge, lw=0.6, alpha=0.75, zorder=1 + z / 100))


    plano(0, "#DBEAFE", "#3B82F6")
    for y in (0.0, COMPRIMENTO):
        a_, b_ = proj(0, y), proj(X_MAX, y)
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color=COR_TRANSVERSAL, lw=0.9, zorder=2)
    for c in range(N_CORREDORES):
        a_, b_ = proj(c * DX, 0), proj(c * DX, COMPRIMENTO)
        ax.plot([a_[0], b_[0]], [a_[1], b_[1]], color=COR_CORREDOR[c + 1], lw=0.9, alpha=0.85, zorder=2)
    vp = np.array([proj(c * DX, y) for c in range(N_CORREDORES) for y in (0.0, COMPRIMENTO)])
    ax.scatter(vp[:, 0], vp[:, 1], marker="D", s=area(ppu, 0.72, True), c=COR_VP, edgecolors="none", zorder=5)
    sl1 = np.array([proj(x, y) for x, y in zip(xs, ys)])
    ax.scatter(sl1[:, 0], sl1[:, 1], s=area(ppu, 0.75), marker="s", c=cores_slot, edgecolors="black", linewidths=0.15,
               zorder=6)
    for xe, cor, face, nome, ha_, dx_ in ((X_ENTRADA, COR_ENTRADA, "#DCFCE7", "ENTRADA", "center", 0.0),
                                          (X_CAIXA, COR_CAIXA, "#FEE2E2", "CAIXA", "center", 0.0)):
        a_ = proj(xe, 0)
        ax.scatter(*a_, s=area(ppu, 1.0), marker="s", facecolor=face, edgecolor=cor, lw=0.7, zorder=7)
        ax.scatter(*a_, s=area(ppu, 0.72, True), marker="D", c=COR_VP, edgecolors="none", zorder=8)
        ax.text(a_[0] + dx_, a_[1] - 2.2, nome, ha=ha_, va="top", fontsize=FS_S, fontweight="bold", color=cor)


    plano(Z_SUP, "#FEF3C7", "#F59E0B")
    sl2 = np.array([proj(x, y, Z_SUP) for x, y in zip(xs, ys)])
    for i in range(n):
        ax.plot([sl1[i, 0], sl2[i, 0]], [sl1[i, 1], sl2[i, 1]], color=cores_slot[i], lw=0.4, ls=(0, (2, 1.5)),
                alpha=0.8, zorder=3)

    unicas = {}
    for u, v, w_ in arestas:
        k = (min(u, v), max(u, v))
        unicas[k] = max(w_, unicas.get(k, -np.inf))
    ar = sorted(((u, v, w_) for (u, v), w_ in unicas.items()), key=lambda t_: t_[2])
    if max_arestas > 0:
        ar = ar[-max_arestas:]
    w = np.array([t_[2] for t_ in ar])
    wn = (w - w.min()) / max(np.ptp(w), 1e-9)
    a_min = float(np.clip(150 / len(ar), 0.04, 0.35))
    segs = [[tuple(sl2[u]), tuple(sl2[v])] for u, v, _ in ar]
    cores = plt.cm.YlOrBr(0.55 + 0.4 * wn)
    cores[:, 3] = a_min + (min(0.9, a_min * 2.5) - a_min) * wn
    ax.add_collection(LineCollection(segs, colors=cores, linewidths=0.15 + 0.6 * wn, zorder=8))
    print(f"G2: {n} vértices, {len(ar)} arestas desenhadas (E2 total: {len(unicas)})")
    ax.scatter(sl2[:, 0], sl2[:, 1], s=area(ppu, 0.9), c=cores_slot, edgecolors="black", linewidths=0.15, zorder=9)

    if not real:
        warnings.warn("ATENÇÃO: E2 sintético (ilustrativo). Não use esta figura no artigo; coloque o CSV de lift em dados/.")
    ax.text(-16, proj(0, 10, Z_SUP)[1], "Camada\nlógica " r"$G_2$", fontsize=FS + 0.5, fontweight="bold",
            color="#78350F", va="center", ha="left", linespacing=1.2)
    ax.text(-16, proj(0, 10)[1], "Camada\nfísica " r"$G_1$", fontsize=FS + 0.5, fontweight="bold",
            color="#1E3A8A", va="center", ha="left", linespacing=1.2)

    if com_titulo:
        ax.set_title(r"Cenário 1: grafo multicamadas $M=(G,C)$", fontsize=FS + 1, fontweight="bold", pad=2)
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="None", markerfacecolor="#CBD5E1", markeredgecolor="black", markersize=0.9 * ppu,
               markeredgewidth=0.15, label="seção (cor = corredor)"),
        Line2D([], [], color=COR_ARESTA_G2, lw=1.0, label=r"afinidade $E_2$ (lift)"),
        Line2D([], [], marker="s", ls="None", markerfacecolor="#CBD5E1", markeredgecolor="black", markersize=0.75 * ppu,
               markeredgewidth=0.15, label="slot"),
        Line2D([], [], color="#64748B", lw=0.8, ls=(0, (2, 1.5)), label=r"alocação $\kappa$"),
    ], loc="upper center", bbox_to_anchor=(0.5, 0.02), ncol=4, fontsize=FS_S, frameon=False,
        handlelength=1.3, handletextpad=0.3, columnspacing=0.9)
    salvar(fig, saida)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", type=Path, default=Path(__file__).resolve().parent.parent)
    ap.add_argument("--cenario", choices=["1", "2", "ambos"], default="ambos")
    ap.add_argument("--max-arestas", type=int, default=0,
                    help="limita as arestas de G2 desenhadas às de maior Lift (0 = desenha todas, padrão)")
    ap.add_argument("--titulo", action="store_true", help="inclui o título dentro da imagem (padrão: sem título)")
    ap.add_argument("--layout", choices=["L0", "L1", "L2"], default=None,
                    help="layout usado na alocação (padrão: L1 no Cenário 1 e L2 no Cenário 2)")
    a = ap.parse_args()
    out = a.raiz / "modelagem"
    suf = f"_{a.layout}" if a.layout else ""
    if a.cenario in ("1", "ambos"):
        gerar_cenario1(a.raiz, out / f"cenario1_grafo_multicamadas{suf}.png", a.max_arestas, a.titulo,
                       a.layout or "L1")
    if a.cenario in ("2", "ambos"):
        gerar_cenario2(a.raiz, out / f"cenario2_grafo_unico{suf}.png", a.titulo, a.layout or "L2")


if __name__ == "__main__":
    main()
