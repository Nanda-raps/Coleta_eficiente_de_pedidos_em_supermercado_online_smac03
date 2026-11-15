"""Estrategias de coleta de um pedido.

Um pedido e um conjunto de slots a visitar (os slots das secoes do pedido).
Uma rota e uma ordem de visita: ENTRADA -> slot 1 -> ... -> slot k -> CAIXA.
O custo da rota e a soma das distancias de D entre pontos consecutivos.

Todas as estrategias recebem os slots NA ORDEM DO CARRINHO e devolvem a ordem de visita:
    sigma_ref   ordem do carrinho (referencia, sem criterio)
    sigma_corr  varredura em S: corredores em ordem crescente, sentido alternando a cada corredor
    sigma_nn    vizinho mais proximo, a partir da ENTRADA
    sigma_opt   rota de custo minimo: Held-Karp (exato) ate 15 secoes;
                acima disso, vizinho mais proximo + melhoria 2-opt (heuristica)
"""
from config import LIMITE_HELD_KARP

ESTRATEGIAS = ("ref", "corr", "nn", "opt")


def custo_rota(ordem, D, g):
    """Custo de ENTRADA -> ordem -> CAIXA."""
    percurso = [g.ENTRADA] + list(ordem) + [g.CAIXA]
    return sum(D[a, b] for a, b in zip(percurso, percurso[1:]))


def sigma_ref(slots, D, g):
    return list(slots)


def sigma_corr(slots, D, g):
    """Varredura em S: corredores em ordem crescente, alternando o sentido a cada corredor visitado.

    1o corredor com itens: da frente ao fundo; 2o: do fundo a frente; 3o: da frente ao fundo; ...
    (o sentido alterna entre os corredores que tem itens, pulando os vazios).
    """
    por_corredor = {}
    for s in slots:
        por_corredor.setdefault(g.slot_corredor[s], []).append(s)
    ordem = []
    for n, corredor in enumerate(sorted(por_corredor)):
        do_corredor = sorted(por_corredor[corredor], key=lambda s: g.slot_posicao[s])   # frente -> fundo
        if n % 2 == 1:
            do_corredor.reverse()                                                       # fundo -> frente
        ordem += do_corredor
    return ordem


def sigma_nn(slots, D, g):
    """Vai sempre ao slot ainda nao visitado mais proximo. Empate: menor indice de slot."""
    faltam = sorted(slots)
    atual = g.ENTRADA
    ordem = []
    while faltam:
        proximo = min(faltam, key=lambda s: (D[atual, s], s))
        ordem.append(proximo)
        faltam.remove(proximo)
        atual = proximo
    return ordem


def dois_opt(ordem, D, g):
    """Melhora uma rota invertendo trechos enquanto isso reduzir o custo (ENTRADA e CAIXA ficam fixas)."""
    rota = [g.ENTRADA] + list(ordem) + [g.CAIXA]
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(1, len(rota) - 2):
            for j in range(i + 1, len(rota) - 1):
                antes = D[rota[i - 1], rota[i]] + D[rota[j], rota[j + 1]]
                depois = D[rota[i - 1], rota[j]] + D[rota[i], rota[j + 1]]
                if depois < antes - 1e-9:
                    rota[i:j + 1] = reversed(rota[i:j + 1])
                    melhorou = True
    return rota[1:-1]


def held_karp(slots, D, g):
    """Rota de custo minimo por programacao dinamica (exata).

    custo[mascara][j] = menor custo saindo da ENTRADA, visitando exatamente os pontos
    da mascara (bit i ligado = ponto i visitado) e terminando no ponto j.
    """
    k = len(slots)
    d = [[D[a, b] for b in slots] for a in slots]            # distancias entre os pontos do pedido
    d_ent = [D[g.ENTRADA, s] for s in slots]
    d_cx = [D[s, g.CAIXA] for s in slots]
    INF = float("inf")
    custo = [[INF] * k for _ in range(1 << k)]
    pai = [[-1] * k for _ in range(1 << k)]
    for j in range(k):
        custo[1 << j][j] = d_ent[j]                           # visitar so o ponto j
    for mascara in range(1, 1 << k):
        for j in range(k):
            if not mascara >> j & 1:
                continue
            anterior = mascara ^ (1 << j)                     # mascara sem o ponto j
            if anterior == 0:
                continue
            for i in range(k):
                if anterior >> i & 1:
                    c = custo[anterior][i] + d[i][j]
                    if c < custo[mascara][j]:
                        custo[mascara][j] = c
                        pai[mascara][j] = i
    cheia = (1 << k) - 1
    ultimo = min(range(k), key=lambda j: custo[cheia][j] + d_cx[j])
    ordem, mascara, j = [], cheia, ultimo
    while j != -1:                                            # reconstroi o caminho de tras para frente
        ordem.append(slots[j])
        mascara, j = mascara ^ (1 << j), pai[mascara][j]
    return ordem[::-1]


def opt_e_exata(slots):
    """True se sigma_opt resolve este pedido de forma exata (Held-Karp)."""
    return len(slots) <= LIMITE_HELD_KARP


def sigma_opt(slots, D, g):
    if opt_e_exata(slots):
        return held_karp(slots, D, g)
    # Muitas secoes: heuristica. Melhora com 2-opt a rota do vizinho mais proximo e a da
    # varredura em S, e fica com a menor (assim nunca perde para sigma_nn nem sigma_corr).
    candidatas = [dois_opt(sigma_nn(slots, D, g), D, g),
                  dois_opt(sigma_corr(slots, D, g), D, g)]
    return min(candidatas, key=lambda ordem: custo_rota(ordem, D, g))


def executar(estrategia, slots_carrinho, D, g):
    """Aplica a estrategia a um pedido. Devolve (ordem de visita, custo em metros)."""
    slots = list(dict.fromkeys(slots_carrinho))               # slots distintos, mantendo a ordem do carrinho
    funcao = {"ref": sigma_ref, "corr": sigma_corr, "nn": sigma_nn, "opt": sigma_opt}[estrategia]
    ordem = funcao(slots, D, g)
    return ordem, custo_rota(ordem, D, g)
