# Demonstra o prototipo em UM pedido real: converte as secoes em slots, roda as quatro estrategias
# e mostra distancia, tempo, ganho e a ordem de visita.
#
# Uso (na raiz do projeto):
#   python src/demo.py                 pedido 40098, layout L0
#   python src/demo.py 40098 L1        outro layout (L0, L1 ou L2)
#   python src/demo.py --lista         lista os 100 pedidos de avaliacao

import argparse

from carga import carregar_pedidos_avaliacao, mapa_nome_para_id, slots_do_pedido
from grafo_fisico import carregar_layout, grafo_padrao
from indicadores import ganho, n_corredores, pares_equivalentes, tempo_coleta
from rotas import ESTRATEGIAS, executar, opt_e_exata

# Nome de cada estrategia na tabela impressa.
NOMES = {
    "ref": "ref  (ordem do carrinho)",
    "corr": "corr (varredura por corredores)",
    "nn": "nn   (vizinho mais proximo)",
    "opt": "opt  (rota de custo minimo)",
}


def listar(pedidos):
    # Imprime os pedidos de avaliacao, para escolher um numero.
    print("id_teste  order_id  itens  secoes")
    for p in pedidos.itertuples():
        print(f"{p.id_teste:>8}  {p.order_id:>8}  {p.n_itens:>5}  {len(p.secoes):>6}")


def demonstrar(pedidos, order_id, nome_layout):
    # Roda as quatro estrategias no pedido order_id e imprime o resultado.
    linha = pedidos[pedidos["order_id"] == order_id]
    if linha.empty:
        raise SystemExit(f"Pedido {order_id} nao esta nos 100 pedidos de avaliacao. "
                         "Use 'python src/demo.py --lista' para ver os disponiveis.")
    pedido = linha.iloc[0]

    # Grafo da loja e matriz D (Dijkstra a partir de cada ponto).
    g = grafo_padrao()
    D = g.matriz_D()
    # Posicao (corredor, posicao) de cada secao neste layout.
    _, mapa = carregar_layout(nome_layout)
    # Slots do pedido na ordem do carrinho, sem repetidos.
    slots = list(dict.fromkeys(slots_do_pedido(pedido["secoes"], mapa, g)))
    # Dicionarios para imprimir o nome da secao de cada parada.
    nome_da_secao = {v: k for k, v in mapa_nome_para_id().items()}
    secao_do_slot = {g.indice_slot(*mapa[a]): nome_da_secao[a] for a in pedido["secoes"]}

    print(f"\nPEDIDO {order_id} | layout {nome_layout}")
    print(f"{pedido['n_itens']} itens, {len(slots)} secoes distintas, "
          f"{n_corredores(slots, g)} corredores distintos")
    print("\nParadas (corredor, posicao) na ordem do carrinho:")
    for s in slots:
        print(f"  ({g.slot_corredor[s]:>2},{g.slot_posicao[s]})  {secao_do_slot[s]}")

    # Roda todas as estrategias: estrategia -> (ordem, custo).
    resultados = {e: executar(e, slots, D, g) for e in ESTRATEGIAS}
    custos = {e: custo for e, (_, custo) in resultados.items()}

    print("\nEstrategia                         distancia   tempo    ganho vs ref")
    # Tabela: distancia, tempo (min) e ganho de cada estrategia contra a ref.
    for e in ESTRATEGIAS:
        tempo_min = tempo_coleta(custos[e], pedido["n_itens"]) / 60
        g_e = ganho(custos["ref"], custos[e])
        extra = ""
        # So no opt: avisa se a rota foi exata ou heuristica.
        if e == "opt":
            extra = "  [exata]" if opt_e_exata(slots) else "  [heuristica: 2-opt]"
        print(f"{NOMES[e]:<33}{custos[e]:>8.1f} m {tempo_min:>6.1f} min {g_e:>8.0%}{extra}")

    print("\nOrdem de visita (ENTRADA -> ... -> CAIXA):")
    for e in ESTRATEGIAS:
        ordem, _ = resultados[e]
        trajeto = " -> ".join(f"({g.slot_corredor[s]},{g.slot_posicao[s]})" for s in ordem)
        print(f"  {e:<5}{trajeto}")

    # Estrategias que deram a mesma distancia neste pedido.
    iguais = pares_equivalentes(custos)
    if iguais:
        print("\nEstrategias equivalentes neste pedido: " + ", ".join(f"{a} = {b}" for a, b in iguais))


def main():
    ap = argparse.ArgumentParser(description="Demonstracao da coleta de um pedido real.")
    ap.add_argument("pedido", nargs="?", type=int, default=40098, help="order_id (padrao: 40098)")
    ap.add_argument("layout", nargs="?", default="L0", choices=("L0", "L1", "L2"), help="layout (padrao: L0)")
    ap.add_argument("--lista", action="store_true", help="lista os 100 pedidos de avaliacao")
    args = ap.parse_args()

    pedidos = carregar_pedidos_avaliacao()
    if args.lista:
        listar(pedidos)
    else:
        demonstrar(pedidos, args.pedido, args.layout)


if __name__ == "__main__":
    main()
