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
from matplotlib.lines import Line2D
from matplotlib.patches import ConnectionPatch, FancyBboxPatch, Rectangle


# Parâmetros do layout (seção 3.5 da modelagem)

N_CORREDORES = 17
COMPRIMENTO = 20.0   
DX = 4.0             
H_LATERAL = 1.0      
X_ENTRADA = -5.0    
X_CAIXA = (N_CORREDORES - 1) * DX + 5.0  
N_POS_MAX = 8        

# Paleta
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
DESTAQUES = ["#E11D48", "#7C3AED", "#059669", "#2563EB", "#DB2777", "#EA580C"]

plt.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "mathtext.fontset": "dejavusans",
        "axes.titleweight": "bold",
    }
)


# Dados

@dataclass
class Loja:
    """Geometria da loja (em metros) e grafo físico G1."""

    slots: pd.DataFrame     
    grafo: nx.Graph         
    rho: np.ndarray          

    @property
    def n_slots(self) -> int:
        return len(self.slots)


def localizar_layout(raiz: Path, layout: str) -> Path | None:
    """Procura dados/layouts/layout_<L>*.csv (prefere o arquivo '*_final')."""
    pasta = raiz / "dados" / "layouts"
    cands = sorted(pasta.glob(f"layout_{layout}*.csv")) if pasta.exists() else []
    cands.sort(key=lambda p_: (0 if "final" in p_.stem else 1, p_.name))
    return cands[0] if cands else None


def carregar_layout(raiz: Path, layout: str = "L0") -> pd.DataFrame:
    """Lê o layout (colunas: aisle_id, corredor, posicao_na_frente; aisle e department opcionais)."""
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

    # Grafo físico G1: ENTRADA, CAIXA, VP (frente/fundo), nós de acesso e slots
    g = nx.Graph()
    manh = lambda a, b: abs(a[0] - b[0]) + abs(a[1] - b[1])
    pos = {"ENTRADA": (X_ENTRADA, 0.0), "CAIXA": (X_CAIXA, 0.0)}
    for c in range(1, N_CORREDORES + 1):
        x = (c - 1) * DX
        pos[f"VPf{c}"], pos[f"VPt{c}"] = (x, 0.0), (x, COMPRIMENTO)

    def aresta(a, b, w=None):
        g.add_edge(a, b, weight=manh(pos[a], pos[b]) if w is None else w)

    for c in range(1, N_CORREDORES):                       # transversais
        aresta(f"VPf{c}", f"VPf{c + 1}")
        aresta(f"VPt{c}", f"VPt{c + 1}")
    aresta("ENTRADA", "VPf1")
    aresta("CAIXA", f"VPf{N_CORREDORES}")

    for c, grp in slots.groupby("corredor"):               # eixos + acessos + slots
        cadeia = [f"VPf{c}"]
        for _, s in grp.iterrows():
            k = int(s["idx"])
            a, sl = f"A{k}", f"S{k}"
            pos[a], pos[sl] = (s.x_eixo, s.y), (s.x_slot, s.y)
            cadeia.append(a)
            aresta(a, sl, w=H_LATERAL)
        cadeia.append(f"VPt{c}")
        for u, v in zip(cadeia[:-1], cadeia[1:]):
            aresta(u, v)

    d_ent = nx.single_source_dijkstra_path_length(g, "ENTRADA")
    d_cai = nx.single_source_dijkstra_path_length(g, "CAIXA")
    rho = np.array([d_ent[f"S{i}"] + d_cai[f"S{i}"] for i in slots["idx"]])
    return Loja(slots=slots, grafo=g, rho=rho)


def carregar_arestas_g2(raiz: Path, ids: list[int]) -> tuple[list[tuple[int, int, float]], bool]:
    """Retorna (arestas, dados_reais) com os extremos em aisle_id. Sem arquivo -> topologia ilustrativa."""
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
        except Exception as e:  # noqa: BLE001
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



# camada física 

def desenhar_fisico(ax, loja: Loja, cores_slots=None, tamanho_slot=70, cmap=None, vmin=None, vmax=None):
    """Planta de G1. Retorna o scatter dos slots (útil para colorbar)."""
    ax.set_aspect("equal", adjustable="box")
    ax.set_xlim(X_ENTRADA - 4.5, X_CAIXA + 4.5)
    ax.set_ylim(-6.5, COMPRIMENTO + 3.0)
    ax.axis("off")

    x_max = (N_CORREDORES - 1) * DX
    ax.add_patch(Rectangle((-2.0, -1.4), x_max + 4.0, COMPRIMENTO + 2.8,
                           facecolor=COR_FUNDO_LOJA, edgecolor=COR_EIXO, lw=1.0, zorder=0))

    for y in (0.0, COMPRIMENTO):
        ax.plot([0, x_max], [y, y], color=COR_TRANSVERSAL, lw=2.2, solid_capstyle="round", zorder=2)
    
    for c in range(1, N_CORREDORES + 1):
        x = (c - 1) * DX
        ax.plot([x, x], [0, COMPRIMENTO], color=COR_EIXO, lw=1.6, zorder=2)
        ax.text(x, -2.4, f"C{c}", ha="center", va="center", fontsize=9, fontweight="bold", color=COR_VP)

    xs = np.repeat(np.arange(N_CORREDORES) * DX, 2)
    ys = np.tile([0.0, COMPRIMENTO], N_CORREDORES)
    ax.scatter(xs, ys, marker="D", s=44, c=COR_VP, edgecolors="white", linewidths=0.8, zorder=5)

    s = loja.slots
    ax.scatter(s.x_eixo, s.y, s=10, c="#64748B", zorder=3)
    ax.plot(np.vstack([s.x_eixo, s.x_slot]), np.vstack([s.y, s.y]), color="#475569", lw=1.0, zorder=3)
    kw = dict(s=tamanho_slot, marker="s", linewidths=0.8, zorder=6)
    if cores_slots is None:
        sc = ax.scatter(s.x_slot, s.y, c=COR_SLOT, edgecolors=COR_SLOT_BORDA, **kw)
    else:
        sc = ax.scatter(s.x_slot, s.y, c=cores_slots, cmap=cmap, vmin=vmin, vmax=vmax,
                        edgecolors="#0F172A", **kw)

    # ENTRADA / CAIXA
    for x, cor, face, nome, x_vp in (
        (X_ENTRADA, COR_ENTRADA, "#DCFCE7", "ENTRADA\n($v_{in}$)", 0.0),
        (X_CAIXA, COR_CAIXA, "#FEE2E2", "CAIXA\n($v_{out}$)", x_max),
    ):
        ax.plot([x, x_vp], [0, 0], color=cor, lw=2.0, ls="--", zorder=3)
        ax.scatter([x], [0], s=230, marker="s", facecolor=face, edgecolor=cor, lw=2.0, zorder=7)
        ax.text(x, -2.4, nome, ha="center", va="top", fontsize=9.5, fontweight="bold", color=cor)
    return sc


def legenda_fisica(extra=None):
    h = [
        Line2D([], [], marker="D", ls="None", color=COR_VP, markeredgecolor="white", markersize=8,
               label="Pontos de passagem $VP$"),
        Line2D([], [], marker="o", ls="None", color="#64748B", markersize=5,
               label="Nós de acesso no eixo do corredor"),
        Line2D([], [], color="#475569", lw=1.2, label="Aresta slot–acesso (peso $h_i$)"),
        Line2D([], [], color=COR_TRANSVERSAL, lw=2.2, label="Circulação: eixos e transversais (peso Manhattan)"),
    ]
    return h + (extra or [])


def salvar(fig, saida: Path):
    saida.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(saida, dpi=300, bbox_inches="tight", pad_inches=0.25, facecolor="white")
    plt.close(fig)
    print(f"Salvo: {saida}")


# Cenário 2: grafo único

def gerar_cenario2(raiz: Path, saida: Path, com_titulo: bool = False, layout: str = "L2") -> None:
    loja = construir_loja(carregar_layout(raiz, layout))
    fig, ax = plt.subplots(figsize=(16, 6.8))

    sc = desenhar_fisico(ax, loja, cores_slots=loja.rho, cmap="viridis_r", tamanho_slot=75)
    cb = fig.colorbar(sc, ax=ax, fraction=0.018, pad=0.01)
    cb.set_label(r"Custo do slot  $\rho(p) = d(v_{in},p) + d(p,v_{out})$  [m]", fontsize=10.5)
    cb.ax.text(0.5, 1.03, "mais caro\n(fundo)", transform=cb.ax.transAxes, ha="center", va="bottom", fontsize=9)
    cb.ax.text(0.5, -0.03, "mais barato\n(frente)", transform=cb.ax.transAxes, ha="center", va="top", fontsize=9)
    ax.text(-8.8, COMPRIMENTO + 1.2, "FUNDO", fontsize=9, color="#64748B", fontweight="bold", ha="left")
    ax.text(-8.8, 1.2, "FRENTE", fontsize=9, color="#64748B", fontweight="bold", ha="left")

    if com_titulo:
        ax.set_title(
            rf"Cenário 2: grafo único $G=(V,E,w)$ — {N_CORREDORES} corredores e {loja.n_slots} slots",
            fontsize=14, pad=10)
    ax.legend(handles=legenda_fisica([
        Line2D([], [], marker="s", ls="None", markerfacecolor="#FDE725", markeredgecolor="#0F172A", markersize=8,
               label=r"Slot $VS$: amarelo = menor $\rho$ (recebe as seções de maior demanda $f(s)$)"),
    ]), loc="upper center", bbox_to_anchor=(0.5, -0.01), ncol=2, fontsize=9.5, frameon=True,
        edgecolor="#CBD5E1")
    salvar(fig, saida)


# Cenário 1: multicamadas heterogêneo (V1 = 17 corredores, V2 = 134 seções)

def gerar_cenario1(raiz: Path, saida: Path, max_arestas: int = 0, com_titulo: bool = False,
                   layout: str = "L1") -> None:
    loja = construir_loja(carregar_layout(raiz, layout))
    n = loja.n_slots
    ids = loja.slots["aisle_id"].tolist()
    arestas, real = carregar_arestas_g2(raiz, ids)
    slot_de = {a_: i for i, a_ in enumerate(ids)}         
    arestas = [(slot_de[u], slot_de[v], w_) for u, v, w_ in arestas]
    s = loja.slots
    corr = s["corredor"].to_numpy()            # corredor ocupado por cada seção (seção i -> slot i)
    cont = s.groupby("corredor").size()        # nº de seções por corredor

    def proj(x, y, z=0.0):
        return x + 0.7 * y, 0.6 * y + z

    Z_SUP, Y_C = 19.0, 4.0
    x_max = (N_CORREDORES - 1) * DX
    cmap = plt.cm.tab20
    cor_c = {c: cmap((c - 1) % 20) for c in range(1, N_CORREDORES + 1)}

    fig, ax = plt.subplots(figsize=(16, 10.5))
    ax.set_aspect("equal")
    ax.axis("off")

    def plano(z, y0, y1, face, edge):
        pts = [proj(-2.5, y0, z), proj(x_max + 2.5, y0, z), proj(x_max + 2.5, y1, z), proj(-2.5, y1, z)]
        ax.add_patch(plt.Polygon(pts, closed=True, fc=face, ec=edge, lw=1.6, alpha=0.75, zorder=1 + z / 100))

    plano(0, -3, 11, "#DBEAFE", "#3B82F6")
    pos1 = {c: proj((c - 1) * DX, Y_C) for c in range(1, N_CORREDORES + 1)}
    for c in range(1, N_CORREDORES):
        a, b = pos1[c], pos1[c + 1]
        ax.plot([a[0], b[0]], [a[1], b[1]], color=COR_TRANSVERSAL, lw=2.6, zorder=4)
    for xe, cor, face, nome, c_viz in ((X_ENTRADA, COR_ENTRADA, "#DCFCE7", "ENTRADA", 1),
                                       (X_CAIXA, COR_CAIXA, "#FEE2E2", "CAIXA", N_CORREDORES)):
        a, b = proj(xe, Y_C), pos1[c_viz]
        ax.plot([a[0], b[0]], [a[1], b[1]], color=cor, lw=2.0, ls="--", zorder=4)
        ax.scatter(*a, s=190, marker="s", facecolor=face, edgecolor=cor, lw=1.8, zorder=7)
        ax.text(a[0], a[1] - 1.5, nome, ha="center", va="top", fontsize=9, fontweight="bold", color=cor)
    for c, (px, py) in pos1.items():
        ax.scatter(px, py, s=720, c=[cor_c[c]], edgecolors="black", linewidths=1.3, zorder=8)
        ax.text(px, py, f"C{c}", ha="center", va="center", fontsize=8.5, fontweight="bold", zorder=9)
        ax.text(px, py - 2.6, rf"$n={cont[c]}$", ha="center", va="top", fontsize=9, color="#1E3A8A", zorder=9)

    # ---------------- G2 (em cima): 134 seções, agrupadas acima do corredor que ocupam
    plano(Z_SUP, -2.5, 22.5, "#FEF3C7", "#F59E0B")
    pos2 = np.array([proj((c - 1) * DX, y, Z_SUP) for c, y in zip(corr, s["y"])])

    for i in range(n):  # intercamadas: seção -> corredor 
        a, b = pos2[i], pos1[int(corr[i])]
        ax.plot([a[0], b[0]], [a[1], b[1]], color=cor_c[int(corr[i])], lw=0.8, alpha=0.6, zorder=3)

    # E2 completo (sem pares duplicados); max_arestas > 0 limita às de maior Lift
    unicas = {}
    for u, v, w_ in arestas:
        k = (min(u, v), max(u, v))
        unicas[k] = max(w_, unicas.get(k, -np.inf))
    ar = sorted(((u, v, w_) for (u, v), w_ in unicas.items()), key=lambda t_: t_[2])
    if max_arestas > 0:
        ar = ar[-max_arestas:]
    w = np.array([t_[2] for t_ in ar])
    wn = (w - w.min()) / max(np.ptp(w), 1e-9)
    # com muitas arestas, linhas mais finas e transparentes para continuar legível
    a_min = float(np.clip(250 / len(ar), 0.05, 0.35))
    lw_min = 0.5 if len(ar) <= 1500 else 0.25
    segs = [[tuple(pos2[u]), tuple(pos2[v])] for u, v, _ in ar]
    cores = plt.cm.YlOrBr(0.55 + 0.4 * wn)
    cores[:, 3] = a_min + (min(0.9, a_min * 2.5) - a_min) * wn
    ax.add_collection(LineCollection(segs, colors=cores, linewidths=lw_min + 1.4 * wn, zorder=8))
    print(f"G2: {n} vértices, {len(ar)} arestas desenhadas (E2 total: {len(unicas)})")
    ax.scatter(pos2[:, 0], pos2[:, 1], s=40, c=[cor_c[int(c)] for c in corr], edgecolors="black",
               linewidths=0.7, zorder=9)
    for i in (0, n - 1):
        ax.annotate(rf"$s_{{{ids[i]}}}$", pos2[i], xytext=(0, 9), textcoords="offset points", ha="center",
                    fontsize=9, fontweight="bold", color="#78350F", zorder=12,
                    bbox=dict(boxstyle="round,pad=0.12", fc="white", ec="none", alpha=0.9))

    nota = "\n(ilustrativo)" if not real else ""
    ax.text(-18.5, proj(0, 10, Z_SUP)[1], r"Camada lógica" "\n" r"$G_2$" + nota,
            fontsize=13, fontweight="bold", color="#78350F", va="center", ha="left", linespacing=1.4)
    ax.text(-18.5, proj(0, Y_C)[1], r"Camada física" "\n" r"$G_1$",
            fontsize=13, fontweight="bold", color="#1E3A8A", va="center", ha="left", linespacing=1.4)

    ax.set_xlim(-19, 88)
    ax.set_ylim(-6, proj(0, 22.5, Z_SUP)[1] + 4)
    if com_titulo:
        ax.set_title(rf"Cenário 1: grafo multicamadas heterogêneo $M=(G,C)$ — {N_CORREDORES} corredores × {n} seções",
                     fontsize=15, fontweight="bold", pad=10)
    ax.legend(handles=[
        Line2D([], [], marker="o", ls="None", markerfacecolor="#FDE68A", markeredgecolor="black", markersize=7,
               label=r"Seção $s_i \in V_2$ (cor = corredor ocupado)"),
        Line2D([], [], color=COR_ARESTA_G2, lw=2, label=r"Afinidade $E_2$ (espessura = Lift)"),
        Line2D([], [], color="#64748B", lw=1.4, label=r"Aresta intercamada $\kappa$: seção $\to$ corredor"),
        Line2D([], [], marker="o", ls="None", markerfacecolor="#BFDBFE", markeredgecolor="black", markersize=11,
               label=r"Corredor $C_j \in V_1$"),
        Line2D([], [], color=COR_TRANSVERSAL, lw=2.6, label=r"Aresta física $E_1$ (corredores vizinhos)"),
    ], loc="upper center", bbox_to_anchor=(0.5, 0.0), ncol=3, fontsize=10, frameon=True, edgecolor="#CBD5E1")
    salvar(fig, saida)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
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
