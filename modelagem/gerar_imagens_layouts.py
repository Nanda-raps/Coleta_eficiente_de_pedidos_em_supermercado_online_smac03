from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches

DEPARTAMENTOS_ORDEM = [
    "produce", "bakery", "deli", "meat seafood", "breakfast",
    "pantry", "dry goods pasta", "canned goods", "international", "bulk",
    "snacks", "beverages", "alcohol", "dairy eggs", "frozen",
    "household", "personal care", "babies", "pets", "other", "missing"
]

tab20 = plt.get_cmap("tab20").colors
CORES_DEPARTAMENTO = {
    "produce": tab20[0],
    "bakery": tab20[1],
    "deli": tab20[2],
    "meat seafood": tab20[3],
    "breakfast": tab20[4],
    "pantry": tab20[5],
    "dry goods pasta": tab20[6],
    "canned goods": tab20[7],
    "international": tab20[8],
    "bulk": tab20[9],
    "snacks": tab20[10],
    "beverages": tab20[11],
    "alcohol": tab20[12],
    "dairy eggs": tab20[13],
    "frozen": tab20[14],
    "household": tab20[15],
    "personal care": tab20[16],
    "babies": tab20[17],
    "pets": tab20[18],
    "other": tab20[19],
    "missing": "#BDBDBD",
}

def plotar_layout(csv_path: Path, png_path: Path, titulo: str) -> None:
    df = pd.read_csv(csv_path)

    fig, ax = plt.subplots(figsize=(18, 7.5), dpi=300)
    ax.set_xlim(0.2, 17.8)
    ax.set_ylim(-2.2, 9.2)
    ax.axis("off")

    largura = 0.54
    altura = 0.72

    for _, row in df.iterrows():
        x = float(row["corredor"])
        y = float(row["posicao_na_frente"])
        dept = str(row["department"])
        cor = CORES_DEPARTAMENTO.get(dept, "#CCCCCC")

        rect = patches.Rectangle(
            (x - largura / 2, y - altura / 2),
            largura,
            altura,
            facecolor=cor,
            edgecolor="none",
            zorder=2,
        )
        ax.add_patch(rect)

        ax.text(
            x,
            y,
            str(int(row["aisle_id"])),
            ha="center",
            va="center",
            fontsize=8.5,
            color="#111111",
            zorder=3,
        )

    y_slot_base = 1.0 - altura / 2
    y_no_extremo = -1.15
    tam_extremo = 0.42

    ax.plot([1, 1], [y_slot_base, y_no_extremo + tam_extremo / 2], color="#D3D3D3", lw=1.5, zorder=1)
    ax.plot([17, 17], [y_slot_base, y_no_extremo + tam_extremo / 2], color="#D3D3D3", lw=1.5, zorder=1)

    entrada_patch = patches.Rectangle(
        (1 - tam_extremo / 2, y_no_extremo - tam_extremo / 2),
        tam_extremo,
        tam_extremo,
        facecolor="#007A00",
        edgecolor="none",
        zorder=2,
    )
    ax.add_patch(entrada_patch)
    ax.text(1, y_no_extremo - 0.62, "ENTRADA", ha="center", va="center", fontsize=10, fontweight="bold")

    caixa_patch = patches.Rectangle(
        (17 - tam_extremo / 2, y_no_extremo - tam_extremo / 2),
        tam_extremo,
        tam_extremo,
        facecolor="#FF0000",
        edgecolor="none",
        zorder=2,
    )
    ax.add_patch(caixa_patch)
    ax.text(17, y_no_extremo - 0.62, "CAIXA", ha="center", va="center", fontsize=10, fontweight="bold")

    ax.set_title(titulo, fontsize=13.5, pad=14, color="#111111")

    handles = [
        patches.Patch(facecolor=CORES_DEPARTAMENTO[d], edgecolor="none", label=d)
        for d in DEPARTAMENTOS_ORDEM
    ]
    legenda = ax.legend(
        handles=handles,
        title="Departamento",
        loc="center left",
        bbox_to_anchor=(1.005, 0.5),
        frameon=False,
        fontsize=10,
        title_fontsize=11,
        labelspacing=0.45,
        handlelength=1.6,
        handleheight=1.1,
    )
    legenda.get_title().set_ha("left")

    plt.tight_layout()
    png_path.parent.mkdir(parents=True, exist_ok=True)
    plt.savefig(png_path, dpi=300, bbox_inches="tight")
    plt.close(fig)
    print(f"Imagem gerada com sucesso: {png_path}")


def main() -> None:
    raiz_projeto = Path(__file__).resolve().parent.parent
    pasta_layouts = raiz_projeto / "dados" / "layouts"

    if not pasta_layouts.exists():
        raise FileNotFoundError(f"Pasta 'layouts' não encontrada em {pasta_layouts}")

    configuracoes = [
        (
            pasta_layouts / "layout_L0.csv",
            pasta_layouts / "layout_L0.png",
            "Layout $L_0$ (sem organização) — 17 corredores: 15 com 8 seções e 2 com 7 (134 seções; alocação aleatória, semente 42)",
        ),
        (
            pasta_layouts / "layout_L1_final.csv",
            pasta_layouts / "layout_L1_final.png",
            "Layout $L_1$ final ($\\omega = \\mathrm{Lift} - 1$, $n_{min} = 300$ calibrado na validação, busca local a partir de $L_0$) — 17 corredores: 15 com 8 seções e 2 com 7",
        ),
        (
            pasta_layouts / "layout_L2_final.csv",
            pasta_layouts / "layout_L2_final.png",
            "Layout $L_2$ final (demanda $f(s)$ do prior, mais demandadas nas posições de menor $\\rho$) — 17 corredores: 15 com 8 seções e 2 com 7",
        ),
    ]

    for csv_file, png_file, titulo in configuracoes:
        plotar_layout(csv_file, png_file, titulo)


if __name__ == "__main__":
    main()
