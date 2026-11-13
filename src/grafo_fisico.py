"""Grafo fisico G1 da loja (nao direcionado e ponderado) e matriz de distancias D.

Estrutura dos nos (indices):
    0 .. n_slots-1      slots (posicoes nas prateleiras), ordenados por (corredor, posicao)
    n_slots             ENTRADA
    n_slots + 1         CAIXA
    depois              nos auxiliares: um no de ACESSO por slot (no eixo do corredor)
                        e dois nos de PASSAGEM por corredor (frente e fundo)

Arestas (todas com peso = distancia de Manhattan entre as extremidades):
    slot <-> seu no de acesso            peso h_i (profundidade lateral)
    acesso <-> acesso vizinho            ao longo do eixo do corredor
    passagem da frente <-> 1o acesso     e ultimo acesso <-> passagem do fundo
    passagem <-> passagem                corredores adjacentes (transversais da frente e do fundo)
    ENTRADA <-> passagem da frente do 1o corredor, CAIXA <-> idem do ultimo (peso 0)

A matriz D (136 x 136 com 134 slots) guarda o caminho minimo entre slots, ENTRADA e
CAIXA, calculado por Dijkstra: so percorre arestas permitidas, entao respeita as
prateleiras (nao ha atalho atravessando uma prateleira).
"""
import heapq

import numpy as np
import pandas as pd

from config import GEOMETRIA, LAYOUTS


class GrafoFisico:
    def __init__(self, slots, geom=GEOMETRIA):
        """slots: lista de (corredor, posicao), sem repeticao."""
        self.geom = geom
        self.slots = sorted(slots)
        self.n_slots = len(self.slots)
        self.ENTRADA = self.n_slots
        self.CAIXA = self.n_slots + 1
        self.n_D = self.n_slots + 2                       # linhas/colunas de D
        self.slot_corredor = np.array([c for c, _ in self.slots])
        self.slot_posicao = np.array([p for _, p in self.slots])
        self._indice = {s: i for i, s in enumerate(self.slots)}
        self._coord = []                                  # (x, y) de cada no
        self._adj = []                                    # lista de adjacencia: [(vizinho, peso)]
        self._construir()

    def indice_slot(self, corredor, posicao):
        """Indice do slot (corredor, posicao) em D."""
        return self._indice[(corredor, posicao)]

    # ---- construcao do grafo -------------------------------------------------
    def _novo_no(self, x, y):
        self._coord.append((x, y))
        self._adj.append([])
        return len(self._adj) - 1

    def _aresta(self, u, v):
        (xu, yu), (xv, yv) = self._coord[u], self._coord[v]
        peso = abs(xu - xv) + abs(yu - yv)                # distancia de Manhattan
        self._adj[u].append((v, peso))
        self._adj[v].append((u, peso))

    def _construir(self):
        g = self.geom
        corredores = sorted({c for c, _ in self.slots})
        x_eixo = {c: (c - 1) * g["espaco_eixos"] for c in corredores}
        y_slot = lambda pos: g["y_primeiro_slot"] + (pos - 1) * g["espaco_slots"]

        # 1) nos reservados: slots, ENTRADA e CAIXA (nesta ordem, para bater com os indices de D)
        for c, p in self.slots:
            self._novo_no(x_eixo[c] + g["h_lateral"], y_slot(p))
        ent = self._novo_no(x_eixo[corredores[0]], g["y_transversal_frente"])
        cax = self._novo_no(x_eixo[corredores[-1]], g["y_transversal_frente"])
        assert (ent, cax) == (self.ENTRADA, self.CAIXA)

        # 2) por corredor: nos de passagem, nos de acesso e arestas do eixo
        passagem_frente, passagem_fundo = {}, {}
        for c in corredores:
            passagem_frente[c] = self._novo_no(x_eixo[c], g["y_transversal_frente"])
            passagem_fundo[c] = self._novo_no(x_eixo[c], g["y_transversal_fundo"])
            acessos = []
            for p in sorted(pos for cc, pos in self.slots if cc == c):
                acesso = self._novo_no(x_eixo[c], y_slot(p))
                self._aresta(self._indice[(c, p)], acesso)        # slot -> acesso (custo h_i)
                acessos.append(acesso)
            self._aresta(passagem_frente[c], acessos[0])
            for a, b in zip(acessos, acessos[1:]):
                self._aresta(a, b)                                # eixo do corredor
            self._aresta(acessos[-1], passagem_fundo[c])

        # 3) transversais: troca de corredor so pela frente ou pelo fundo
        for c, d in zip(corredores, corredores[1:]):
            self._aresta(passagem_frente[c], passagem_frente[d])
            self._aresta(passagem_fundo[c], passagem_fundo[d])

        # 4) ENTRADA e CAIXA (custo de acesso zero)
        self._aresta(ent, passagem_frente[corredores[0]])
        self._aresta(cax, passagem_frente[corredores[-1]])

    # ---- caminhos minimos ----------------------------------------------------
    def dijkstra(self, origem):
        """Distancia minima de `origem` a todos os nos do grafo."""
        dist = [float("inf")] * len(self._adj)
        dist[origem] = 0.0
        fila = [(0.0, origem)]
        while fila:
            d, u = heapq.heappop(fila)
            if d > dist[u]:
                continue                                          # entrada velha da fila
            for v, peso in self._adj[u]:
                nova = d + peso
                if nova < dist[v]:
                    dist[v] = nova
                    heapq.heappush(fila, (nova, v))
        return dist

    def matriz_D(self):
        """Matriz D (n_slots+2 x n_slots+2): 136 x 136 com os 134 slots."""
        D = np.zeros((self.n_D, self.n_D))
        for i in range(self.n_D):
            D[i] = self.dijkstra(i)[: self.n_D]                   # ignora os nos auxiliares
        return D


def carregar_layout(nome):
    """Le o layout ('L0', 'L1' ou 'L2'). Devolve (DataFrame, dict aisle_id -> (corredor, posicao))."""
    df = pd.read_csv(LAYOUTS[nome])
    mapa = {int(r.aisle_id): (int(r.corredor), int(r.posicao_na_frente)) for r in df.itertuples()}
    return df, mapa


def grafo_padrao():
    """Grafo construido a partir dos slots do layout L0 (a malha fisica e a mesma nos tres layouts)."""
    df, _ = carregar_layout("L0")
    return GrafoFisico(list(zip(df.corredor, df.posicao_na_frente)))


if __name__ == "__main__":
    from config import PASTA_RESULTADOS
    g = grafo_padrao()
    D = g.matriz_D()
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    np.save(PASTA_RESULTADOS / "D.npy", D)
    print("D", D.shape, "salva em", PASTA_RESULTADOS / "D.npy")
