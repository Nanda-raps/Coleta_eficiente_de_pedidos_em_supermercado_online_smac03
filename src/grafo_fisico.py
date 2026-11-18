# Transforma a loja em um grafo e calcula a matriz D: a menor distancia, em metros,
# entre quaisquer dois pontos importantes (slots, ENTRADA e CAIXA).
#
# Numeracao dos nos: 0 a n_slots-1 = slots; n_slots = ENTRADA; n_slots+1 = CAIXA;
# os demais sao auxiliares (um 'no de acesso' por slot e dois 'nos de passagem' por corredor).
# O peso de cada aresta e a distancia de Manhattan entre as pontas.

import heapq

import numpy as np
import pandas as pd

from config import GEOMETRIA, LAYOUTS


class GrafoFisico:
    # Loja como grafo: nos (pontos) ligados por arestas (ruas) com comprimento em metros.
    def __init__(self, slots, geom=GEOMETRIA):
        # Recebe os slots como pares (corredor, posicao) e prepara o grafo.
        self.geom = geom

        # Ordena por (corredor, posicao). O numero de cada slot e a posicao dele nesta lista
        # e e o indice usado em D; a ordem fixa impede que a numeracao mude se o CSV vier embaralhado.
        self.slots = sorted(slots)
        self.n_slots = len(self.slots)

        # ENTRADA e CAIXA recebem os dois numeros depois do ultimo slot.
        self.ENTRADA = self.n_slots
        self.CAIXA = self.n_slots + 1

        # Tamanho da matriz D: slots + ENTRADA + CAIXA (136).
        self.n_D = self.n_slots + 2

        # Dado o numero de um slot: em que corredor ele esta e em que posicao do corredor.
        self.slot_corredor = np.array([c for c, _ in self.slots])
        self.slot_posicao = np.array([p for _, p in self.slots])

        # Inverso: (corredor, posicao) -> numero do slot.
        self._indice = {s: i for i, s in enumerate(self.slots)}

        # _coord[no] = (x, y) do no, em metros.
        self._coord = []
        # _adj[no] = lista de vizinhos, no formato (vizinho, comprimento da rua).
        self._adj = []

        self._construir()

    def indice_slot(self, corredor, posicao):
        # Numero do slot que fica neste corredor e nesta posicao.
        return self._indice[(corredor, posicao)]

    def _novo_no(self, x, y):
        # Cria um no em (x, y) e devolve o numero dele.
        self._coord.append((x, y))
        self._adj.append([])
        return len(self._adj) - 1

    def _aresta(self, u, v):
        # Liga u e v com uma rua que vale nos dois sentidos.
        # Comprimento = distancia de Manhattan (anda em L, nunca na diagonal).
        xu, yu = self._coord[u]
        xv, yv = self._coord[v]
        peso = abs(xu - xv) + abs(yu - yv)
        self._adj[u].append((v, peso))
        self._adj[v].append((u, peso))

    def _construir(self):
        # Cria todos os nos e liga com ruas.
        g = self.geom
        corredores = sorted({c for c, _ in self.slots})

        def x_eixo(c):
            # x do eixo do corredor c: corredor 1 em x = 0, corredor 2 em x = 4, ...
            return (c - 1) * g["espaco_eixos"]

        def y_slot(pos):
            # y do slot na posicao pos: 1,25 m + 2,5 m por slot anterior.
            return g["y_primeiro_slot"] + (pos - 1) * g["espaco_slots"]

        # 1) Slots, ENTRADA e CAIXA primeiro, para os numeros dos nos baterem com os indices de D.
        # ENTRADA fica na frente do primeiro corredor e CAIXA na frente do ultimo.
        for c, p in self.slots:
            self._novo_no(x_eixo(c) + g["h_lateral"], y_slot(p))
        ent = self._novo_no(x_eixo(corredores[0]), g["y_transversal_frente"])
        cax = self._novo_no(x_eixo(corredores[-1]), g["y_transversal_frente"])

        # frente[c] e fundo[c]: pontos de passagem nas duas pontas do corredor c.
        frente = {}
        fundo = {}

        # 2) Monta cada corredor: frente, fundo e um no de acesso por slot (o ponto no eixo, por onde se anda).
        for c in corredores:
            frente[c] = self._novo_no(x_eixo(c), g["y_transversal_frente"])
            fundo[c] = self._novo_no(x_eixo(c), g["y_transversal_fundo"])

            acessos = []
            for p in sorted(pos for cc, pos in self.slots if cc == c):
                acesso = self._novo_no(x_eixo(c), y_slot(p))
                # Prateleira -> seu acesso (peso = h_lateral, hoje 0).
                self._aresta(self._indice[(c, p)], acesso)
                acessos.append(acesso)

            # Frente -> acessos em fila -> fundo, ao longo do corredor.
            self._aresta(frente[c], acessos[0])
            for a, b in zip(acessos, acessos[1:]):
                self._aresta(a, b)
            self._aresta(acessos[-1], fundo[c])

        # 3) So da para trocar de corredor pela frente ou pelo fundo (nao se atravessa prateleira).
        for c, d in zip(corredores, corredores[1:]):
            self._aresta(frente[c], frente[d])
            self._aresta(fundo[c], fundo[d])

        # 4) ENTRADA e CAIXA ligadas a frente dos seus corredores.
        self._aresta(ent, frente[corredores[0]])
        self._aresta(cax, frente[corredores[-1]])

    def dijkstra(self, origem):
        # Menor caminho de 'origem' ate todos os nos. Devolve dist[no], em metros.
        # Processa sempre o no mais proximo ainda nao resolvido
        # e testa se passar por ele encurta o caminho dos vizinhos.
        # No comeco so se conhece a origem (0 m); o resto esta a distancia infinita.
        dist = [float("inf")] * len(self._adj)
        dist[origem] = 0.0
        # Fila de (distancia, no) a processar; o heapq entrega sempre o de menor distancia.
        fila = [(0.0, origem)]

        while fila:
            d, u = heapq.heappop(fila)
            # Entrada antiga (ja existe caminho melhor): ignora.
            if d > dist[u]:
                continue
            for v, peso in self._adj[u]:
                # Passar por u encurta o caminho ate o vizinho v?
                nova = d + peso
                if nova < dist[v]:
                    dist[v] = nova
                    heapq.heappush(fila, (nova, v))
        return dist

    def matriz_D(self):
        # D[a][b] = menor distancia entre os pontos a e b.
        # Roda o Dijkstra a partir de cada um dos 136 pontos; cada resultado e uma linha da matriz.
        D = np.zeros((self.n_D, self.n_D))
        for i in range(self.n_D):
            # O corte [: n_D] descarta os nos auxiliares, que ficam depois da CAIXA.
            D[i] = self.dijkstra(i)[: self.n_D]
        return D


def carregar_layout(nome):
    # Le o CSV do layout (L0, L1 ou L2).
    # Devolve (tabela, dicionario aisle_id -> (corredor, posicao)).
    df = pd.read_csv(LAYOUTS[nome])
    mapa = {int(r.aisle_id): (int(r.corredor), int(r.posicao_na_frente)) for r in df.itertuples()}
    return df, mapa


def grafo_padrao():
    # Monta o grafo com os slots do L0. A malha e igual nos tres layouts (so muda qual secao ocupa cada slot).
    df, _ = carregar_layout("L0")
    return GrafoFisico(list(zip(df.corredor, df.posicao_na_frente)))


# Executado direto, gera a matriz D e salva em resultados/D.npy.
if __name__ == "__main__":
    from config import PASTA_RESULTADOS
    g = grafo_padrao()
    D = g.matriz_D()
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    np.save(PASTA_RESULTADOS / "D.npy", D)
    print("D", D.shape, "salva em", PASTA_RESULTADOS / "D.npy")
