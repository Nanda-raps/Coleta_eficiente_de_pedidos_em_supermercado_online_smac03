# Transforma a loja em um grafo e calcula a matriz D,
# a tabela com a menor distancia, em metros, entre quaisquer dois pontos importantes.
#
# Numeracao dos nos (pontos do grafo):
#   0 a n_slots-1   -> os slots (prateleiras)
#   n_slots         -> ENTRADA
#   n_slots + 1     -> CAIXA
#   depois          -> nos auxiliares: um "no de acesso" por slot (no eixo do corredor)
#                      e dois "nos de passagem" por corredor (frente e fundo)
#
# O peso de cada aresta é a distancia de Manhattan entre as duas pontas.
# A matriz D guarda so a distancia entre slots, ENTRADA e CAIXA, calculada com Dijkstra
# partindo de cada um deles.
import heapq    # fila de prioridade: o Dijkstra a usa para pegar sempre o ponto mais proximo

import numpy as np
import pandas as pd

from config import GEOMETRIA, LAYOUTS


class GrafoFisico:

    def __init__(self, slots, geom=GEOMETRIA):
        # slots: lista de pares (corredor, posicao), um para cada prateleira da loja.
        self.geom = geom

        # Ordena os slots para que o numero de cada um (0, 1, 2, ...) seja sempre o mesmo.
        self.slots = sorted(slots)
        self.n_slots = len(self.slots)

        # ENTRADA e CAIXA recebem os dois numeros logo depois do ultimo slot.
        self.ENTRADA = self.n_slots
        self.CAIXA = self.n_slots + 1

        # Tamanho da matriz D: todos os slots + ENTRADA + CAIXA (134 + 2 = 136).
        self.n_D = self.n_slots + 2

        # Dado o numero de um slot, estes vetores dizem em que corredor ele esta
        # e em que posicao dentro do corredor.
        self.slot_corredor = np.array([c for c, _ in self.slots])
        self.slot_posicao = np.array([p for _, p in self.slots])

        # Dicionario inverso: (corredor, posicao) -> numero do slot.
        self._indice = {s: i for i, s in enumerate(self.slots)}

        # _coord[no] = (x, y) do no no mapa, em metros.
        self._coord = []
        # _adj[no] = lista de vizinhos desse no, no formato (vizinho, comprimento da rua).
        self._adj = []

        # Cria todos os nos e arestas.
        self._construir()

    def indice_slot(self, corredor, posicao):
        # Devolve o numero do slot que fica neste corredor e nesta posicao.
        return self._indice[(corredor, posicao)]

    def _novo_no(self, x, y):
        # Cria um ponto novo no mapa nas coordenadas (x, y) e devolve o numero dele.
        self._coord.append((x, y))
        self._adj.append([])                # no novo ainda nao tem vizinhos
        return len(self._adj) - 1           # o numero do no e a ultima posicao da lista

    def _aresta(self, u, v):
        # Liga os nos u e v com uma rua.
        xu, yu = self._coord[u]
        xv, yv = self._coord[v]
        # Comprimento da rua = distancia de Manhattan (anda em "L", nunca na diagonal).
        peso = abs(xu - xv) + abs(yu - yv)
        # A rua vale nos dois sentidos, entao registra a ligacao nos dois nos.
        self._adj[u].append((v, peso))
        self._adj[v].append((u, peso))

    def _construir(self):
        # Monta o mapa inteiro: cria os pontos e liga com ruas.
        g = self.geom
        # Numeros dos corredores existentes, em ordem crescente (1, 2, ..., 17).
        corredores = sorted({c for c, _ in self.slots})

        def x_eixo(c):
            # Coordenada x do eixo do corredor c: corredor 1 em x=0, corredor 2 em x=4, ...
            return (c - 1) * g["espaco_eixos"]

        def y_slot(pos):
            # Coordenada y do slot na posicao pos: comeca em 1,25 m e soma 2,5 m por slot anterior.
            return g["y_primeiro_slot"] + (pos - 1) * g["espaco_slots"]

        # PASSO 1: cria primeiro os nos dos slots, depois ENTRADA e CAIXA.
        # Fazer nessa ordem faz os numeros dos nos baterem com os indices da matriz D.
        for c, p in self.slots:
            self._novo_no(x_eixo(c) + g["h_lateral"], y_slot(p))
        # ENTRADA fica na frente do primeiro corredor; CAIXA, na frente do ultimo.
        ent = self._novo_no(x_eixo(corredores[0]), g["y_transversal_frente"])
        cax = self._novo_no(x_eixo(corredores[-1]), g["y_transversal_frente"])

        # frente[c] e fundo[c]: os pontos de passagem nas duas pontas do corredor c.
        frente = {}
        fundo = {}

        # PASSO 2: monta cada corredor.
        for c in corredores:
            frente[c] = self._novo_no(x_eixo(c), g["y_transversal_frente"])
            fundo[c] = self._novo_no(x_eixo(c), g["y_transversal_fundo"])

            # Um "no de acesso" por slot: o ponto no meio do corredor, na altura do slot.
            # E por onde o funcionario realmente anda.
            acessos = []
            for p in sorted(pos for cc, pos in self.slots if cc == c):
                acesso = self._novo_no(x_eixo(c), y_slot(p))
                # Liga a prateleira ao seu ponto de acesso (peso = h_lateral, hoje 0).
                self._aresta(self._indice[(c, p)], acesso)
                acessos.append(acesso)

            # Liga a frente do corredor ao primeiro acesso.
            self._aresta(frente[c], acessos[0])
            # Liga cada acesso ao seguinte, ao longo do corredor.
            for a, b in zip(acessos, acessos[1:]):
                self._aresta(a, b)
            # Liga o ultimo acesso ao fundo do corredor.
            self._aresta(acessos[-1], fundo[c])

        # PASSO 3: so da para trocar de corredor pela frente ou pelo fundo (nao se atravessa prateleira).
        for c, d in zip(corredores, corredores[1:]):
            self._aresta(frente[c], frente[d])
            self._aresta(fundo[c], fundo[d])

        # PASSO 4: liga a ENTRADA e a CAIXA a frente dos seus corredores.
        self._aresta(ent, frente[corredores[0]])
        self._aresta(cax, frente[corredores[-1]])

    def dijkstra(self, origem):
        # Calcula o caminho mais curto de 'origem' ate TODOS os outros nos.
        # Devolve uma lista: dist[no] = menor distancia, em metros, de origem ate esse no.

        # No comeco so se sabe chegar na propria origem (0 m); o resto esta a distancia infinita.
        dist = [float("inf")] * len(self._adj)
        dist[origem] = 0.0
        # Fila de nos a processar, no formato (distancia, no). Comeca so com a origem.
        fila = [(0.0, origem)]

        while fila:
            # Tira da fila o no mais proximo da origem ainda nao processado.
            d, u = heapq.heappop(fila)
            # Se d e maior que a melhor distancia ja conhecida, esta entrada e antiga: ignora.
            if d > dist[u]:
                continue
            # Olha cada vizinho de u e testa se passar por u encurta o caminho ate ele.
            for v, peso in self._adj[u]:
                nova = d + peso
                if nova < dist[v]:
                    dist[v] = nova                          # achou um caminho melhor: atualiza
                    heapq.heappush(fila, (nova, v))         # e poe o vizinho na fila para processar
        return dist

    def matriz_D(self):
        # Monta a matriz D (136 x 136): D[a][b] = menor distancia em metros entre os pontos a e b.
        D = np.zeros((self.n_D, self.n_D))
        for i in range(self.n_D):
            # Roda o Dijkstra partindo do ponto i e guarda o resultado como a linha i da matriz.
            # O corte [: self.n_D] descarta os nos auxiliares (acessos e passagens),
            # que ficam depois dos slots, da ENTRADA e da CAIXA.
            D[i] = self.dijkstra(i)[: self.n_D]
        return D


def carregar_layout(nome):
    # Le o CSV do layout ('L0', 'L1' ou 'L2').
    # Devolve (tabela completa, dicionario aisle_id -> (corredor, posicao)).
    df = pd.read_csv(LAYOUTS[nome])
    # Para cada linha do CSV, liga o numero da secao (aisle_id) ao seu corredor e posicao.
    mapa = {int(r.aisle_id): (int(r.corredor), int(r.posicao_na_frente)) for r in df.itertuples()}
    return df, mapa


def grafo_padrao():
    # Monta o grafo da loja usando os slots do layout L0.
    # A malha fisica e a mesma nos tres layouts (so muda qual secao ocupa cada slot),
    # entao qualquer layout serve para criar o grafo.
    df, _ = carregar_layout("L0")
    return GrafoFisico(list(zip(df.corredor, df.posicao_na_frente)))


# Este bloco so roda quando o arquivo e executado direto (python grafo_fisico.py).
# Gera a matriz D e salva em resultados/D.npy.
if __name__ == "__main__":
    from config import PASTA_RESULTADOS
    g = grafo_padrao()
    D = g.matriz_D()
    PASTA_RESULTADOS.mkdir(exist_ok=True)           # cria a pasta resultados/ se nao existir
    np.save(PASTA_RESULTADOS / "D.npy", D)
    print("D", D.shape, "salva em", PASTA_RESULTADOS / "D.npy")
