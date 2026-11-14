"""Carga dos pedidos de avaliacao: de Pedidos.csv ate a lista de slots a visitar.

O Pedidos.csv traz, para cada um dos 100 pedidos, os NOMES das secoes, numa ordem que
NAO e a do carrinho (em 82 dos 100 pedidos a ordem difere). Para a estrategia sigma_ref
precisamos da ordem em que o cliente colocou os itens no carrinho. Ela vem de
dados_integrados_train.csv (gerado pelo notebook de curadoria), coluna add_to_cart_order.

Caminho dos dados ate a rota:
    nome da secao --(aisles.csv)--> aisle_id
    aisle_id, na ordem do carrinho --(layout)--> (corredor, posicao) --> indice do slot em D

Uso:
    pedidos = carregar_pedidos_avaliacao()
    _, mapa = carregar_layout("L1")
    slots = slots_do_pedido(pedidos.loc[0, "secoes"], mapa, g)
"""
import pandas as pd

from config import RAIZ

PEDIDOS_CSV = RAIZ / "dados" / "amostras" / "Pedidos.csv"
AISLES_CSV = RAIZ / "dados" / "instacart" / "aisles.csv"
INTEGRADOS_CSV = RAIZ / "dados" / "curados" / "dados_integrados_train.csv"


def mapa_nome_para_id():
    """Dicionario nome da secao -> aisle_id, lido de aisles.csv."""
    aisles = pd.read_csv(AISLES_CSV)
    return dict(zip(aisles["aisle"], aisles["aisle_id"].astype(int)))


def secoes_listadas_no_csv():
    """Le Pedidos.csv. Devolve um DataFrame com as colunas:
        id_teste, order_id, n_itens (coluna "itens no pedido"),
        secoes_listadas (aisle_id na ordem em que o CSV lista os nomes).
    """
    if not PEDIDOS_CSV.exists():
        raise FileNotFoundError(f"Nao encontrei {PEDIDOS_CSV}")
    brutos = pd.read_csv(PEDIDOS_CSV, encoding="utf-8-sig")        # o arquivo comeca com BOM
    nome_para_id = mapa_nome_para_id()

    def nomes_para_ids(texto):
        ids = []
        for nome in texto.split(";"):                               # nomes separados por "; "
            nome = nome.strip()
            if nome not in nome_para_id:
                raise ValueError(f"Secao desconhecida em Pedidos.csv: {nome!r}")
            ids.append(nome_para_id[nome])
        return ids

    return pd.DataFrame({
        "id_teste": brutos["id_teste"],
        "order_id": brutos["order_id"],
        "n_itens": brutos["itens no pedido"],
        "secoes_listadas": brutos["seções do pedido"].apply(nomes_para_ids),
    })


def ordem_do_carrinho(order_ids):
    """Para cada order_id, devolve (secoes, n_itens) a partir de dados_integrados_train.csv.

    secoes: aisle_id distintos na ordem do carrinho, ficando com a PRIMEIRA aparicao de
    cada secao (o cliente pode voltar a pegar item da mesma secao mais tarde).
    n_itens: quantidade de linhas (itens) do pedido no arquivo.
    Resultado: duas Series indexadas por order_id.
    """
    if not INTEGRADOS_CSV.exists():
        raise FileNotFoundError(
            f"Nao encontrei {INTEGRADOS_CSV}. Rode o notebook notebooks/curadoria_dados_cenario5.ipynb "
            "(a pasta dados/curados/ recebe o arquivo)."
        )
    itens = pd.read_csv(INTEGRADOS_CSV, usecols=["order_id", "aisle_id", "add_to_cart_order"])
    itens = itens[itens["order_id"].isin(order_ids)]                # so os pedidos que interessam
    itens = itens.sort_values(["order_id", "add_to_cart_order"])    # ordem do carrinho

    n_itens = itens.groupby("order_id").size()
    primeiras = itens.drop_duplicates(["order_id", "aisle_id"])     # mantem a 1a aparicao de cada secao
    secoes = primeiras.groupby("order_id")["aisle_id"].apply(lambda s: [int(a) for a in s])

    faltando = set(order_ids) - set(secoes.index)
    if faltando:
        raise ValueError(f"Pedidos sem itens em dados_integrados_train.csv: {sorted(faltando)}")
    return secoes, n_itens


def carregar_pedidos_avaliacao():
    """Os 100 pedidos de avaliacao. DataFrame com as colunas:
        id_teste, order_id,
        n_itens            itens segundo o Pedidos.csv
        n_itens_carrinho   itens segundo dados_integrados_train.csv (deve ser igual)
        secoes             aisle_id distintos NA ORDEM DO CARRINHO (usar em sigma_ref)
        secoes_listadas    aisle_id na ordem em que o Pedidos.csv lista (so para conferencia)
    """
    pedidos = secoes_listadas_no_csv()
    secoes, n_itens = ordem_do_carrinho(list(pedidos["order_id"]))
    pedidos["n_itens_carrinho"] = pedidos["order_id"].map(n_itens)
    pedidos["secoes"] = pedidos["order_id"].map(secoes)
    return pedidos[["id_teste", "order_id", "n_itens", "n_itens_carrinho", "secoes", "secoes_listadas"]]


def slots_do_pedido(secoes, mapa_layout, g):
    """Converte secoes (aisle_id) em indices de slot, mantendo a ordem.

    mapa_layout: dicionario aisle_id -> (corredor, posicao), vindo de carregar_layout(...)[1].
    g: GrafoFisico (g.indice_slot converte (corredor, posicao) no indice usado em D).
    """
    return [g.indice_slot(*mapa_layout[a]) for a in secoes]
