# Decide em que ORDEM o funcionario visita os itens de um pedido e mede quantos metros
# essa ordem custa.
#
# Um pedido e um conjunto de slots a visitar (os slots das secoes do pedido).
# Uma rota e uma ordem de visita: ENTRADA -> slot 1 -> ... -> slot k -> CAIXA.
# O custo da rota e a soma das distancias da matriz D entre pontos consecutivos.
#
# Todas as estrategias recebem os slots NA ORDEM DO CARRINHO e devolvem a ordem de visita:
#   sigma_ref   segue a ordem do carrinho (referencia, sem criterio)
#   sigma_corr  varredura por corredores: corredores em ordem crescente, sentido alternando
#   sigma_nn    vizinho mais proximo, a partir da ENTRADA
#   sigma_opt   rota de custo minimo: Held-Karp (exato) ate 15 secoes;
#               acima disso, vizinho mais proximo + melhoria 2-opt (heuristica)
from config import LIMITE_HELD_KARP

ESTRATEGIAS = ("ref", "corr", "nn", "opt")


def custo_rota(ordem, D, g):
    # Mede quantos metros custa a rota ENTRADA -> ordem -> CAIXA.
    # Monta o percurso completo, com a ENTRADA no inicio e a CAIXA no fim.
    percurso = [g.ENTRADA] + list(ordem) + [g.CAIXA]
    return sum(D[a, b] for a, b in zip(percurso, percurso[1:]))


def sigma_ref(slots, D, g):
    # Referencia: nao faz nada, devolve os slots na mesma ordem do carrinho.
    return list(slots)


def sigma_corr(slots, D, g):
    # Varredura por corredores: passa pelos corredores em ordem crescente e alterna o sentido.
    # 1o corredor com itens: da frente ao fundo; 2o: do fundo a frente; 3o: da frente ao fundo...
    # (o sentido alterna entre os corredores que TEM itens, pulando os vazios).

    # Agrupa os slots por corredor: {corredor: [slots do pedido nesse corredor]}.
    por_corredor = {}
    for s in slots:
        por_corredor.setdefault(g.slot_corredor[s], []).append(s)

    ordem = []
    # n conta os corredores com itens (0, 1, 2, ...); nao e o numero do corredor.
    for n, corredor in enumerate(sorted(por_corredor)):
        # Ordena os slots do corredor da frente para o fundo.
        do_corredor = sorted(por_corredor[corredor], key=lambda s: g.slot_posicao[s])
        # Nos corredores de ordem impar (2o, 4o, ...), inverte: do fundo para a frente.
        if n % 2 == 1:
            do_corredor.reverse()
        ordem += do_corredor
    return ordem


def sigma_nn(slots, D, g):
    # Vizinho mais proximo: sempre vai ao slot ainda nao visitado mais perto de onde esta.
    # Em caso de empate de distancia, vence o menor numero de slot.
    faltam = sorted(slots)          # slots que ainda precisam ser visitados
    atual = g.ENTRADA               # comeca na ENTRADA
    ordem = []
    while faltam:
        # Escolhe o slot de menor distancia ate o ponto atual (o 2o item da tupla desempata).
        proximo = min(faltam, key=lambda s: (D[atual, s], s))
        ordem.append(proximo)
        faltam.remove(proximo)
        atual = proximo             # agora o funcionario esta nesse slot
    return ordem


def dois_opt(ordem, D, g):
    # Melhora uma rota pronta invertendo trechos dela, enquanto isso reduzir o custo.
    # A ENTRADA e a CAIXA ficam sempre fixas (primeiro e ultimo da lista).
    rota = [g.ENTRADA] + list(ordem) + [g.CAIXA]
    melhorou = True
    while melhorou:                 # repete ate nenhuma inversao melhorar a rota
        melhorou = False
        # Testa todos os trechos da rota, do ponto i ao ponto j.
        for i in range(1, len(rota) - 2):
            for j in range(i + 1, len(rota) - 1):
                # Inverter o trecho muda so 2 ligacoes: a que entra nele e a que sai dele.
                # As ligacoes de dentro do trecho sao as mesmas, so percorridas ao contrario.
                antes = D[rota[i - 1], rota[i]] + D[rota[j], rota[j + 1]]
                depois = D[rota[i - 1], rota[j]] + D[rota[i], rota[j + 1]]
                # So inverte se ficar menor (a folga de 1e-9 evita erro de arredondamento).
                if depois < antes - 1e-9:
                    rota[i:j + 1] = reversed(rota[i:j + 1])
                    melhorou = True
    return rota[1:-1]               # devolve so os slots, sem a ENTRADA e a CAIXA


def held_karp(slots, D, g):
    # Rota de custo minimo exata, por programacao dinamica (Held-Karp).
    #
    # Ideia: custo[mascara][j] = menor custo saindo da ENTRADA, visitando exatamente
    # os pontos da mascara e terminando no ponto j.
    # A mascara e um numero em binario: o bit i ligado significa "o ponto i foi visitado".

    k = len(slots)

    # Copia as distancias necessarias para listas simples (indices 0..k-1 = pontos do pedido).
    d = [[D[a, b] for b in slots] for a in slots]            # distancia entre os pontos do pedido
    d_ent = [D[g.ENTRADA, s] for s in slots]                 # distancia da ENTRADA a cada ponto
    d_cx = [D[s, g.CAIXA] for s in slots]                    # distancia de cada ponto a CAIXA

    INF = float("inf")
    # Tabelas com uma linha por mascara (2^k) e uma coluna por ponto final (k).
    custo = [[INF] * k for _ in range(1 << k)]
    # pai[mascara][j] = ponto visitado imediatamente antes de j (serve para reconstruir a rota).
    pai = [[-1] * k for _ in range(1 << k)]

    # Caso base: conjunto com um so ponto j; o custo e ir da ENTRADA ate ele.
    for j in range(k):
        custo[1 << j][j] = d_ent[j]

    # Preenche a tabela, dos conjuntos menores para os maiores.
    for mascara in range(1, 1 << k):
        for j in range(k):
            if not mascara >> j & 1:                         # j nao esta neste conjunto: pula
                continue
            anterior = mascara ^ (1 << j)                    # o mesmo conjunto, sem o ponto j
            if anterior == 0:                                # conjunto de um ponto: ja preenchido
                continue
            # Testa de qual ponto i do conjunto anterior e melhor vir ate j.
            for i in range(k):
                if anterior >> i & 1:
                    c = custo[anterior][i] + d[i][j]
                    if c < custo[mascara][j]:
                        custo[mascara][j] = c
                        pai[mascara][j] = i

    # Todos os pontos visitados (todos os bits ligados).
    cheia = (1 << k) - 1
    # Escolhe o ultimo ponto que minimiza: custo ate la + distancia dele ate a CAIXA.
    ultimo = min(range(k), key=lambda j: custo[cheia][j] + d_cx[j])

    # Reconstroi a rota de tras para frente seguindo o 'pai' de cada ponto.
    ordem, mascara, j = [], cheia, ultimo
    while j != -1:
        ordem.append(slots[j])
        # O lado direito e calculado primeiro: pai[mascara][j] usa a mascara e o j ANTIGOS.
        mascara, j = mascara ^ (1 << j), pai[mascara][j]
    return ordem[::-1]                                       # inverte: ficou de tras para frente


def opt_e_exata(slots):
    # Diz se o sigma_opt resolve este pedido de forma exata (ate 15 secoes) ou por heuristica.
    return len(slots) <= LIMITE_HELD_KARP


def sigma_opt(slots, D, g):
    # Rota de menor custo: exata quando o pedido e pequeno, aproximada quando e grande.
    if opt_e_exata(slots):
        return held_karp(slots, D, g)
    # Muitas secoes: usa heuristica. Melhora com 2-opt a rota do vizinho mais proximo e a da
    # varredura por corredores, e fica com a menor (assim nunca perde para sigma_nn nem sigma_corr).
    candidatas = [dois_opt(sigma_nn(slots, D, g), D, g),
                  dois_opt(sigma_corr(slots, D, g), D, g)]
    return min(candidatas, key=lambda ordem: custo_rota(ordem, D, g))


def executar(estrategia, slots_carrinho, D, g):
    # Ponto de entrada: aplica a estrategia escolhida a um pedido.
    # Devolve (ordem de visita, custo em metros).

    # Tira slots repetidos mantendo a ordem do carrinho
    # (varios itens da mesma secao caem no mesmo slot, que so precisa ser visitado uma vez).
    slots = list(dict.fromkeys(slots_carrinho))

    # Escolhe a funcao pelo nome da estrategia. 
    # aqui so sao guardadas
    funcao = {"ref": sigma_ref, "corr": sigma_corr, "nn": sigma_nn, "opt": sigma_opt}[estrategia]

    # Executa a estrategia escolhida e obtem a ordem de visita.
    ordem = funcao(slots, D, g)

    # Devolve a ordem e quantos metros ela custa.
    return ordem, custo_rota(ordem, D, g)
