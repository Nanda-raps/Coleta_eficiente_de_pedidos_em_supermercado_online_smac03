# Transforma a distancia de uma rota (calculada em rotas.py) nos indicadores do trabalho:
# tempo, pedidos por turno, ganho, equivalencia entre estrategias e intervalos de confianca.
# Tempo: config.TEMPO. Bootstrap: config.SEMENTE e config.BOOTSTRAP.

from itertools import combinations

import numpy as np

from config import BOOTSTRAP, SEMENTE, TEMPO


def tempo_coleta(distancia, n_itens, tempo=TEMPO):
    # Tempo de coleta em segundos: T = D/v + t_item * itens + t_fixo.
    # n_itens e o numero de itens do pedido (nao de secoes). Funciona com numeros ou arrays.
    return distancia / tempo["velocidade"] + tempo["t_item"] * n_itens + tempo["t_fixo"]


def pedidos_por_turno(tempos, tempo=TEMPO):
    # H / tempo MEDIO de coleta (a media vem antes da divisao).
    tempos = list(tempos)
    if not tempos:
        raise ValueError("Preciso de pelo menos um tempo")
    return tempo["turno"] / (sum(tempos) / len(tempos))


def ganho(d_ref, d_sigma):
    # Ganho sobre a referencia: (D_ref - D_sigma) / D_ref. 0 = igual a ref; 0,5 = metade da distancia.
    # Nunca divide por zero: toda rota custa pelo menos 64 m (ENTRADA a CAIXA).
    return (d_ref - d_sigma) / d_ref


def n_corredores(slots, g):
    # Corredores distintos que o pedido visita (slots = numeros de slot).
    return len({int(g.slot_corredor[s]) for s in slots})


def pares_equivalentes(custos, tol=1e-9):
    # Pares de estrategias com a mesma distancia em UM pedido (|D1 - D2| <= tol).
    # custos = {estrategia: distancia}.
    return [(a, b) for a, b in combinations(custos, 2) if abs(custos[a] - custos[b]) <= tol]


def contar_equivalentes(custos_por_pedido, tol=1e-9):
    # Quantos pedidos tem pelo menos um par de estrategias equivalentes.
    return sum(1 for custos in custos_por_pedido if pares_equivalentes(custos, tol))


def resumo(valores):
    # Media e mediana.
    v = np.asarray(valores, dtype=float)
    return {"media": float(v.mean()), "mediana": float(np.median(v))}


def reducao_media(d_base, d_novo):
    # 1 - media(d_novo) / media(d_base): a razao das MEDIAS (como em calibracao_n_min.csv),
    # nao a media das reducoes de cada pedido.
    return 1.0 - float(np.mean(d_novo)) / float(np.mean(d_base))


def ganho_medio(d_ref, d_sigma):
    # Media dos ganhos G(o), calculados pedido a pedido.
    return float(np.mean(ganho(np.asarray(d_ref, dtype=float), np.asarray(d_sigma, dtype=float))))


def bootstrap_ic(estatistica, *series, repeticoes=BOOTSTRAP["repeticoes"], nivel=BOOTSTRAP["nivel"],
                 semente=SEMENTE):
    # Intervalo de confianca por bootstrap PAREADO.
    # Sorteia pedidos com reposicao da amostra, recalcula a estatistica e repete muitas vezes;
    # o IC e a faixa central dos resultados (95%: percentis 2,5 e 97,5).
    # Pareado: o sorteio escolhe pedidos, e a mesma escolha vale para todas as series;
    # entao o pedido i mantem seus valores em todos os layouts e estrategias.
    #
    # estatistica recebe uma amostra de cada serie. Exemplos:
    #   bootstrap_ic(np.mean, d_L1)                 media de L1
    #   bootstrap_ic(reducao_media, d_L0, d_L1)     reducao de L1 contra L0
    # Devolve (estimativa na amostra original, limite inferior, limite superior).
    # Confere as entradas.
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
    # Cada linha de 'sorteios' e um re-sorteio de pedidos (posicoes).
    sorteios = rng.integers(0, n, size=(repeticoes, n))
    valores = np.array([estatistica(*(s[i] for s in series)) for i in sorteios])
    cauda = (1.0 - nivel) / 2.0
    inferior, superior = np.percentile(valores, [100 * cauda, 100 * (1 - cauda)])
    return estimativa, float(inferior), float(superior)
