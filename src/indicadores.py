"""Indicadores de eficiencia da coleta (modelagem 3.2.3).

A distancia D(pi) de uma rota ja e calculada por rotas.custo_rota / rotas.executar;
aqui ficam os indicadores derivados dela:

    tempo_coleta        T(o) = D/v + t_item * |o| + t_fixo      (|o| = itens do pedido)
    pedidos_por_turno   H / T medio
    ganho               G(o) = (D_ref - D_sigma) / D_ref
    n_corredores        corredores distintos que o pedido visita
    contar_equivalentes pedidos em que estrategias distintas dao a mesma distancia
    resumo              media e mediana
    reducao_media       reducao de um layout contra outro (razao das medias)
    ganho_medio         media dos ganhos G(o) de uma estrategia contra a referencia
    bootstrap_ic        intervalo de confianca por bootstrap pareado, com semente fixa

Os parametros de tempo (v, t_item, t_fixo, H) vem de config.TEMPO; os do bootstrap,
de config.SEMENTE e config.BOOTSTRAP.
"""
from itertools import combinations

import numpy as np

from config import BOOTSTRAP, SEMENTE, TEMPO


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


# ---- resumo estatistico e bootstrap ----------------------------------------------------
def resumo(valores):
    """Media e mediana de uma lista de valores (por exemplo, a distancia de cada pedido)."""
    v = np.asarray(valores, dtype=float)
    return {"media": float(v.mean()), "mediana": float(np.median(v))}


def reducao_media(d_base, d_novo):
    """Reducao de d_novo contra d_base: 1 - media(d_novo) / media(d_base).

    E a razao das MEDIAS (como em calibracao_n_min.csv: (157,234 - 144,783) / 157,234 = 7,92%),
    nao a media das reducoes de cada pedido. d_base e d_novo: uma distancia por pedido.
    """
    return 1.0 - float(np.mean(d_novo)) / float(np.mean(d_base))


def ganho_medio(d_ref, d_sigma):
    """Media dos ganhos G(o) = (D_ref - D_sigma) / D_ref, calculados pedido a pedido."""
    return float(np.mean(ganho(np.asarray(d_ref, dtype=float), np.asarray(d_sigma, dtype=float))))


def bootstrap_ic(estatistica, *series, repeticoes=BOOTSTRAP["repeticoes"], nivel=BOOTSTRAP["nivel"],
                 semente=SEMENTE):
    """Intervalo de confianca por bootstrap PAREADO.

    Ideia: temos so uma amostra de pedidos. Sorteamos pedidos COM reposicao da propria amostra
    (mesmo tamanho), calculamos a estatistica nessa amostra re-sorteada, e repetimos muitas vezes.
    O intervalo que contem a parte central dos resultados (95%: do percentil 2,5 ao 97,5) e o IC.

    Pareado: o sorteio escolhe PEDIDOS (posicoes), e a mesma escolha vale para todas as series.
    Assim o pedido i continua com seus valores em todos os layouts/estrategias.

    estatistica: funcao que recebe uma amostra de cada serie (arrays do mesmo tamanho) e devolve um numero.
        bootstrap_ic(np.mean, d_L1)                           media de L1
        bootstrap_ic(reducao_media, d_L0, d_L1)               reducao de L1 contra L0
        bootstrap_ic(ganho_medio, d_ref, d_opt)               ganho medio de opt contra ref
    series: uma ou mais listas, uma distancia por pedido, na MESMA ordem de pedidos.
    Devolve (estimativa na amostra original, limite inferior, limite superior).
    """
    if not series:
        raise ValueError("Preciso de pelo menos uma serie")
    series = [np.asarray(s, dtype=float) for s in series]
    n = len(series[0])
    if n == 0 or any(len(s) != n for s in series):
        raise ValueError("As series precisam ter o mesmo tamanho e pelo menos um pedido")
    if not 0.0 < nivel < 1.0:
        raise ValueError("nivel precisa estar entre 0 e 1")

    estimativa = float(estatistica(*series))
    rng = np.random.default_rng(semente)
    sorteios = rng.integers(0, n, size=(repeticoes, n))             # cada linha: um re-sorteio de pedidos
    valores = np.array([estatistica(*(s[i] for s in series)) for i in sorteios])
    cauda = (1.0 - nivel) / 2.0
    inferior, superior = np.percentile(valores, [100 * cauda, 100 * (1 - cauda)])
    return estimativa, float(inferior), float(superior)
