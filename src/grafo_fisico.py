"""Grafo fisico da loja (G1) e matriz de distancias D.

Indices dos nos: primeiro os slots (0 a n_slots-1), depois ENTRADA e CAIXA e, por fim,
os nos auxiliares: um no de acesso por slot (no eixo do corredor) e dois nos de
passagem por corredor (frente e fundo). O peso de cada aresta e a distancia de
Manhattan entre as pontas. D guarda o caminho minimo entre slots, ENTRADA e CAIXA,
calculado com Dijkstra a partir de cada um deles.
"""
import heapq

import numpy as np
import pandas as pd

from config import GEOMETRIA, LAYOUTS


class GrafoFisico:
    def __init__(self, slots, geom=GEOMETRIA):
        # slots: lista de (corredor, posicao)
        self.geom = geom
        self.slots = sorted(slots)
        self.n_slots = len(self.slots)
        self.ENTRADA = self.n_slots
        self.CAIXA = self.n_slots + 1
        self.n_D = self.n_slots + 2
        self.slot_corredor = np.array([c for c, _ in self.slots])
        self.slot_posicao = np.array([p for _, p in self.slots])
        self._indice = {s: i for i, s in enumerate(self.slots)}
        self._coord = []
        self._adj = []
        self._construir()

    def indice_slot(self, corredor, posicao):
        return self._indice[(corredor, posicao)]

    def _novo_no(self, x, y):
        self._coord.append((x, y))
        self._adj.append([])
        return len(self._adj) - 1

    def _aresta(self, u, v):
        xu, yu = self._coord[u]
        xv, yv = self._coord[v]
        peso = abs(xu - xv) + abs(yu - yv)
        self._adj[u].append((v, peso))
        self._adj[v].append((u, peso))

    def _construir(self):
        g = self.geom
        corredores = sorted({c for c, _ in self.slots})

        def x_eixo(c):
            return (c - 1) * g["espaco_eixos"]

        def y_slot(pos):
            return g["y_primeiro_slot"] + (pos - 1) * g["espaco_slots"]

        # slots, ENTRADA e CAIXA primeiro, para os indices baterem com os de D
        for c, p in self.slots:
            self._novo_no(x_eixo(c) + g["h_lateral"], y_slot(p))
        ent = self._novo_no(x_eixo(corredores[0]), g["y_transversal_frente"])
        cax = self._novo_no(x_eixo(corredores[-1]), g["y_transversal_frente"])

        frente = {}
        fundo = {}
        for c in corredores:
            frente[c] = self._novo_no(x_eixo(c), g["y_transversal_frente"])
            fundo[c] = self._novo_no(x_eixo(c), g["y_transversal_fundo"])

            acessos = []
            for p in sorted(pos for cc, pos in self.slots if cc == c):
                acesso = self._novo_no(x_eixo(c), y_slot(p))
                self._aresta(self._indice[(c, p)], acesso)
                acessos.append(acesso)

            self._aresta(frente[c], acessos[0])
            for a, b in zip(acessos, acessos[1:]):
                self._aresta(a, b)
            self._aresta(acessos[-1], fundo[c])

        # so da para trocar de corredor pela frente ou pelo fundo
        for c, d in zip(corredores, corredores[1:]):
            self._aresta(frente[c], frente[d])
            self._aresta(fundo[c], fundo[d])

        self._aresta(ent, frente[corredores[0]])
        self._aresta(cax, frente[corredores[-1]])

    def dijkstra(self, origem):
        dist = [float("inf")] * len(self._adj)
        dist[origem] = 0.0
        fila = [(0.0, origem)]
        while fila:
            d, u = heapq.heappop(fila)
            if d > dist[u]:
                continue
            for v, peso in self._adj[u]:
                nova = d + peso
                if nova < dist[v]:
                    dist[v] = nova
                    heapq.heappush(fila, (nova, v))
        return dist

    def matriz_D(self):
        D = np.zeros((self.n_D, self.n_D))
        for i in range(self.n_D):
            # os nos auxiliares ficam de fora
            D[i] = self.dijkstra(i)[: self.n_D]
        return D


def carregar_layout(nome):
    """Le o layout ('L0', 'L1' ou 'L2'). Devolve (DataFrame, dict aisle_id -> (corredor, posicao))."""
    df = pd.read_csv(LAYOUTS[nome])
    mapa = {int(r.aisle_id): (int(r.corredor), int(r.posicao_na_frente)) for r in df.itertuples()}
    return df, mapa


def grafo_padrao():
    # a malha fisica e a mesma nos tres layouts, entao basta usar os slots do L0
    df, _ = carregar_layout("L0")
    return GrafoFisico(list(zip(df.corredor, df.posicao_na_frente)))


if __name__ == "__main__":
    from config import PASTA_RESULTADOS
    g = grafo_padrao()
    D = g.matriz_D()
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    np.save(PASTA_RESULTADOS / "D.npy", D)
    print("D", D.shape, "salva em", PASTA_RESULTADOS / "D.npy")
