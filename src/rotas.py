# Decide a ORDEM em que o funcionario visita os slots de um pedido e mede quantos metros ela custa.
# Rota = ENTRADA -> slots do pedido -> CAIXA; custo = soma das distancias de D entre pontos consecutivos.
#
# Todas as estrategias recebem os slots na ordem do carrinho e devolvem a ordem de visita:
#   ref   ordem do carrinho (referencia, sem criterio)
#   corr  varredura por corredores, alternando o sentido
#   nn    vizinho mais proximo, a partir da ENTRADA
#   opt   rota de menor custo: exata (Held-Karp) ate 15 secoes; acima disso, heuristica (nn ou corr + 2-opt)

from config import LIMITE_HELD_KARP

# Nomes das estrategias; demo.py e experimento.py rodam todas.
ESTRATEGIAS = ("ref", "corr", "nn", "opt")


def custo_rota(ordem, D, g):
    # Metros da rota ENTRADA -> ordem -> CAIXA.
    # Percurso completo, com a ENTRADA no inicio e a CAIXA no fim.
    percurso = [g.ENTRADA] + list(ordem) + [g.CAIXA]
    # Soma a distancia de cada par de pontos vizinhos.
    return sum(D[a, b] for a, b in zip(percurso, percurso[1:]))


def sigma_ref(slots, D, g):
    # Referencia: mantem a ordem do carrinho.
    return list(slots)


def sigma_corr(slots, D, g):
    # Corredores em ordem crescente, alternando o sentido: o 1o corredor com itens vai da frente ao fundo,
    # o 2o do fundo a frente, e assim por diante (corredores sem itens sao pulados).
    # Agrupa os slots por corredor.
    por_corredor = {}
    for s in slots:
        por_corredor.setdefault(g.slot_corredor[s], []).append(s)

    ordem = []
    # n conta so os corredores com itens (nao e o numero do corredor).
    for n, corredor in enumerate(sorted(por_corredor)):
        do_corredor = sorted(por_corredor[corredor], key=lambda s: g.slot_posicao[s])
        # Corredores de ordem impar (2o, 4o, ...) sao percorridos do fundo para a frente.
        if n % 2 == 1:
            do_corredor.reverse()
        ordem += do_corredor
    return ordem


def sigma_nn(slots, D, g):
    # Vai sempre ao slot ainda nao visitado mais proximo; em empate, vence o menor numero de slot.
    faltam = sorted(slots)
    atual = g.ENTRADA
    ordem = []
    while faltam:
        # Escolhe o mais proximo do ponto atual (o 2o item da tupla desempata).
        proximo = min(faltam, key=lambda s: (D[atual, s], s))
        ordem.append(proximo)
        faltam.remove(proximo)
        atual = proximo
    return ordem


def dois_opt(ordem, D, g):
    # Melhora uma rota invertendo trechos enquanto isso reduzir o custo. ENTRADA e CAIXA ficam fixas.
    rota = [g.ENTRADA] + list(ordem) + [g.CAIXA]
    melhorou = True
    while melhorou:
        melhorou = False
        for i in range(1, len(rota) - 2):
            for j in range(i + 1, len(rota) - 1):
                # Inverter o trecho i..j troca so 2 ligacoes (a que entra e a que sai);
                # as de dentro so mudam de sentido.
                antes = D[rota[i - 1], rota[i]] + D[rota[j], rota[j + 1]]
                depois = D[rota[i - 1], rota[j]] + D[rota[i], rota[j + 1]]
                # Inverte so se ficar menor (1e-9 evita ruido de arredondamento).
                if depois < antes - 1e-9:
                    rota[i:j + 1] = reversed(rota[i:j + 1])
                    melhorou = True
    return rota[1:-1]


def held_karp(slots, D, g):
    # Rota de menor custo, exata, por programacao dinamica.
    # custo[mascara][j] = menor custo saindo da ENTRADA, visitando exatamente os pontos da mascara
    # e terminando em j.
    # A mascara e um numero binario: o bit i ligado significa 'ponto i ja visitado'.
    # Cada resposta reaproveita as de conjuntos menores, sem testar todas as ordens.
    k = len(slots)

    # Distancias entre os pontos do pedido (indices 0 a k-1), da ENTRADA a cada um e de cada um a CAIXA.
    d = [[D[a, b] for b in slots] for a in slots]
    d_ent = [D[g.ENTRADA, s] for s in slots]
    d_cx = [D[s, g.CAIXA] for s in slots]

    INF = float("inf")
    # Uma linha por mascara (2^k) e uma coluna por ponto final.
    # pai[mascara][j] = ponto visitado antes de j, para reconstruir a rota.
    custo = [[INF] * k for _ in range(1 << k)]
    pai = [[-1] * k for _ in range(1 << k)]

    for j in range(k):
        # Caso base: so o ponto j visitado; o custo e ir da ENTRADA ate ele.
        custo[1 << j][j] = d_ent[j]

    # Preenche dos conjuntos menores para os maiores.
    for mascara in range(1, 1 << k):
        for j in range(k):
            if not mascara >> j & 1:
                continue
            # O mesmo conjunto, sem o ponto j.
            anterior = mascara ^ (1 << j)
            if anterior == 0:
                continue
            for i in range(k):
                # Testa de qual ponto i do conjunto anterior e melhor vir ate j.
                if anterior >> i & 1:
                    c = custo[anterior][i] + d[i][j]
                    if c < custo[mascara][j]:
                        custo[mascara][j] = c
                        pai[mascara][j] = i

    # Conjunto com todos os pontos. O ultimo ponto e o que minimiza: custo ate la + distancia ate a CAIXA.
    cheia = (1 << k) - 1
    ultimo = min(range(k), key=lambda j: custo[cheia][j] + d_cx[j])

    # Reconstroi a rota de tras para frente, seguindo o 'pai' de cada ponto.
    ordem, mascara, j = [], cheia, ultimo
    while j != -1:
        ordem.append(slots[j])
        # O lado direito e calculado antes: pai usa a mascara e o j antigos.
        mascara, j = mascara ^ (1 << j), pai[mascara][j]
    # Inverte: a rota saiu de tras para frente.
    return ordem[::-1]


def opt_e_exata(slots):
    # True se o pedido tem ate 15 secoes (opt exata).
    return len(slots) <= LIMITE_HELD_KARP


def sigma_opt(slots, D, g):
    # Exata ate 15 secoes. Acima, heuristica: melhora com 2-opt a rota do nn e a do corr
    # e fica com a menor (nunca perde para nenhuma das duas).
    if opt_e_exata(slots):
        return held_karp(slots, D, g)
    candidatas = [dois_opt(sigma_nn(slots, D, g), D, g),
                  dois_opt(sigma_corr(slots, D, g), D, g)]
    return min(candidatas, key=lambda ordem: custo_rota(ordem, D, g))


def executar(estrategia, slots_carrinho, D, g):
    # Ponto de entrada: aplica a estrategia a um pedido. Devolve (ordem de visita, custo em metros).
    # Remove slots repetidos mantendo a ordem do carrinho (varios itens da mesma secao caem no mesmo slot).
    slots = list(dict.fromkeys(slots_carrinho))

    # Escolhe a funcao pelo nome. Sem parenteses: so guarda a funcao; a chamada abaixo a executa.
    funcao = {"ref": sigma_ref, "corr": sigma_corr, "nn": sigma_nn, "opt": sigma_opt}[estrategia]

    ordem = funcao(slots, D, g)

    return ordem, custo_rota(ordem, D, g)
