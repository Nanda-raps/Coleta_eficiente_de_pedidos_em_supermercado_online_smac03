"""Testes da carga dos pedidos. Rodar na raiz do repositorio: python tests/test_carga.py

Precisa de dados/curados/dados_integrados_train.csv (gerado pelo notebook de curadoria).
"""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from carga import PEDIDOS_CSV, carregar_pedidos_avaliacao, mapa_nome_para_id, slots_do_pedido   # noqa: E402
from grafo_fisico import grafo_padrao, carregar_layout                                          # noqa: E402

pedidos = carregar_pedidos_avaliacao()
brutos = pd.read_csv(PEDIDOS_CSV, encoding="utf-8-sig")        # Pedidos.csv como esta no arquivo
g = grafo_padrao()


def test_cem_pedidos_e_todas_as_secoes_convertidas():
    assert len(pedidos) == 100 and pedidos["order_id"].is_unique
    ids_validos = set(mapa_nome_para_id().values())
    for secoes in pedidos["secoes"]:
        assert len(secoes) >= 1 and set(secoes) <= ids_validos          # todo nome virou um aisle_id


def test_conjunto_de_secoes_igual_ao_pedidos_csv():
    for r in pedidos.itertuples():
        assert set(r.secoes) == set(r.secoes_listadas), r.order_id      # mesmas secoes, so a ordem muda
        assert len(r.secoes) == len(r.secoes_listadas)


def test_numero_de_secoes_bate_com_a_coluna_do_csv():
    assert list(pedidos["secoes"].apply(len)) == list(brutos["seções distintas"])


def test_itens_batem():
    assert (pedidos["n_itens"] == pedidos["n_itens_carrinho"]).all()    # pedido a pedido
    assert pedidos["n_itens_carrinho"].sum() == brutos["itens no pedido"].sum()


def test_sem_secao_repetida():
    for secoes in pedidos["secoes"]:
        assert len(secoes) == len(set(secoes))


def test_ordem_do_carrinho_difere_da_listada():
    # O plano de divisao registra que em 82 dos 100 pedidos a ordem do Pedidos.csv nao e a do carrinho
    # (o CSV lista as secoes em ordem crescente de aisle_id).
    diferentes = sum(a != b for a, b in zip(pedidos["secoes"], pedidos["secoes_listadas"]))
    assert diferentes == 82, diferentes


def test_pedido_conferido_a_mao():
    # Conferido nas linhas de dados_integrados_train.csv, ordenadas por add_to_cart_order:
    # pedido 40098: 129, 77, 45, 21, 107, 31, 77 (repetida: ignorar), 98
    por_pedido = pedidos.set_index("order_id")
    assert por_pedido.loc[40098, "secoes"] == [129, 77, 45, 21, 107, 31, 98]
    assert por_pedido.loc[40098, "n_itens"] == 8                         # 8 itens, 7 secoes
    # pedido 21461: frutas (24), vegetais frescos (83), vegetais embalados (123); 12 itens, 3 secoes
    assert por_pedido.loc[21461, "secoes"] == [24, 83, 123]
    assert por_pedido.loc[21461, "n_itens"] == 12


def test_slots_do_pedido():
    for nome in ("L0", "L1", "L2"):
        _, mapa = carregar_layout(nome)
        for secoes in pedidos["secoes"]:
            slots = slots_do_pedido(secoes, mapa, g)
            assert len(slots) == len(secoes) and len(set(slots)) == len(slots)   # um slot por secao
            assert all(0 <= s < g.n_slots for s in slots)
            assert slots == [g.indice_slot(*mapa[a]) for a in secoes]            # mesma ordem do carrinho


for nome, f in list(globals().items()):
    if nome.startswith("test_"):
        f()
        print("OK", nome)
