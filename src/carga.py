# Transforma os pedidos de avaliacao em listas de slots a visitar.
# Caminho dos dados ate a rota:
#   nome da secao -> aisle_id (catalogo) -> (corredor, posicao) (layout) -> numero do slot em D
# A ordem do carrinho nao vem do Pedidos.csv (em 82 dos 100 pedidos a ordem difere):
# vem de pedidos_avaliacao_carrinho.csv, coluna add_to_cart_order.
#
# Uso:
#   pedidos = carregar_pedidos_avaliacao()
#   _, mapa = carregar_layout('L1')
#   slots = slots_do_pedido(pedidos.loc[0, 'secoes'], mapa, g)

import pandas as pd

from config import RAIZ

# Arquivos de entrada.
PEDIDOS_CSV = RAIZ / "dados" / "amostras" / "Pedidos.csv"
AISLES_CSV = RAIZ / "dados" / "curados" / "catalogo_aisles_departamentos.csv"
CARRINHO_CSV = RAIZ / "dados" / "amostras" / "pedidos_avaliacao_carrinho.csv"


def mapa_nome_para_id():
    # Dicionario nome da secao -> aisle_id.
    aisles = pd.read_csv(AISLES_CSV)
    return dict(zip(aisles["aisle"], aisles["aisle_id"].astype(int)))


def secoes_listadas_no_csv():
    # Le o Pedidos.csv e devolve id_teste, order_id, n_itens e as secoes (aisle_id)
    # na ordem em que o CSV as lista.
    if not PEDIDOS_CSV.exists():
        raise FileNotFoundError(f"Nao encontrei {PEDIDOS_CSV}")
    # utf-8-sig porque o arquivo comeca com BOM.
    brutos = pd.read_csv(PEDIDOS_CSV, encoding="utf-8-sig")
    nome_para_id = mapa_nome_para_id()

    def nomes_para_ids(texto):
        # Converte 'secao A; secao B' em [id_A, id_B]; erro se algum nome nao existir no catalogo.
        ids = []
        for nome in texto.split(";"):
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
    # Para cada order_id, devolve (secoes, n_itens) a partir de pedidos_avaliacao_carrinho.csv.
    # secoes = aisle_id distintos na ordem do carrinho (fica a PRIMEIRA aparicao de cada secao).
    # n_itens = linhas (itens) do pedido.
    if not CARRINHO_CSV.exists():
        raise FileNotFoundError(
            f"Nao encontrei {CARRINHO_CSV}. Ele vem no repositorio (dados/amostras/)."
        )
    itens = pd.read_csv(CARRINHO_CSV, usecols=["order_id", "aisle_id", "add_to_cart_order"])
    # So os pedidos de interesse, na ordem do carrinho.
    itens = itens[itens["order_id"].isin(order_ids)]
    itens = itens.sort_values(["order_id", "add_to_cart_order"])

    n_itens = itens.groupby("order_id").size()
    # Mantem so a 1a aparicao de cada secao em cada pedido.
    primeiras = itens.drop_duplicates(["order_id", "aisle_id"])
    secoes = primeiras.groupby("order_id")["aisle_id"].apply(lambda s: [int(a) for a in s])

    faltando = set(order_ids) - set(secoes.index)
    if faltando:
        raise ValueError(f"Pedidos sem itens em pedidos_avaliacao_carrinho.csv: {sorted(faltando)}")
    return secoes, n_itens


def carregar_pedidos_avaliacao():
    # Os 100 pedidos de avaliacao: id_teste, order_id, n_itens,
    # n_itens_carrinho (deve ser igual a n_itens),
    # secoes (aisle_id na ordem do carrinho, usada pela ref) e
    # secoes_listadas (ordem do Pedidos.csv, so para conferencia).
    pedidos = secoes_listadas_no_csv()
    secoes, n_itens = ordem_do_carrinho(list(pedidos["order_id"]))
    pedidos["n_itens_carrinho"] = pedidos["order_id"].map(n_itens)
    pedidos["secoes"] = pedidos["order_id"].map(secoes)
    return pedidos[["id_teste", "order_id", "n_itens", "n_itens_carrinho", "secoes", "secoes_listadas"]]


def slots_do_pedido(secoes, mapa_layout, g):
    # Converte secoes (aisle_id) em numeros de slot, mantendo a ordem.
    # mapa_layout vem de carregar_layout(...)[1]; g.indice_slot converte (corredor, posicao) no indice de D.
    return [g.indice_slot(*mapa_layout[a]) for a in secoes]
