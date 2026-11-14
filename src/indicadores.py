"""Indicadores de eficiencia da coleta (modelagem 3.2.3).

A distancia D(pi) de uma rota ja e calculada por rotas.custo_rota / rotas.executar;
aqui ficam os indicadores derivados dela:

    tempo_coleta        T(o) = D/v + t_item * |o| + t_fixo      (|o| = itens do pedido)
    pedidos_por_turno   H / T medio
    ganho               G(o) = (D_ref - D_sigma) / D_ref
    n_corredores        corredores distintos que o pedido visita
    contar_equivalentes pedidos em que estrategias distintas dao a mesma distancia

Os parametros de tempo (v, t_item, t_fixo, H) vem de config.TEMPO.
"""
from itertools import combinations

from config import TEMPO


def tempo_coleta(distancia, n_itens, tempo=TEMPO):
    """Tempo estimado de coleta, em segundos.

    distancia: D(pi) em metros. n_itens: itens do pedido (nao confundir com secoes).
    Funciona com numeros ou com arrays (varios pedidos de uma vez).
    """
    return distancia / tempo["velocidade"] + tempo["t_item"] * n_itens + tempo["t_fixo"]


def pedidos_por_turno(tempos, tempo=TEMPO):
    """Pedidos atendidos por turno: H dividido pelo tempo MEDIO de coleta.

    A media vem antes da divisao (H / media(T)), nao a media de H / T de cada pedido.
    """
    tempos = list(tempos)
    if not tempos:
        raise ValueError("Preciso de pelo menos um tempo")
    return tempo["turno"] / (sum(tempos) / len(tempos))


def ganho(d_ref, d_sigma):
    """Ganho relativo de uma estrategia sobre a referencia: (D_ref - D_sigma) / D_ref.

    0 = igual a referencia; 0,5 = metade da distancia. Nunca divide por zero, porque
    toda rota custa pelo menos D(ENTRADA, CAIXA) = 64 m.
    """
    return (d_ref - d_sigma) / d_ref


def n_corredores(slots, g):
    """Numero de corredores fisicos distintos visitados pelo pedido (slots = indices de slot)."""
    return len({int(g.slot_corredor[s]) for s in slots})


def pares_equivalentes(custos, tol=1e-9):
    """Pares de estrategias com a mesma distancia em UM pedido.

    custos: dict estrategia -> distancia, por exemplo {"ref": 365.5, "nn": 154.5, "opt": 154.5}.
    Duas estrategias sao equivalentes quando |D1 - D2| <= tol (modelagem 3.2.3).
    """
    return [(a, b) for a, b in combinations(custos, 2) if abs(custos[a] - custos[b]) <= tol]


def contar_equivalentes(custos_por_pedido, tol=1e-9):
    """Quantos pedidos tem pelo menos um par de estrategias equivalentes.

    custos_por_pedido: lista de dicts estrategia -> distancia (um dict por pedido).
    """
    return sum(1 for custos in custos_por_pedido if pares_equivalentes(custos, tol))
