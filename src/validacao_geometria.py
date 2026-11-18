"""Validacao da geometria da loja: nosso G1 reproduz a calibracao dos modeladores?

O documento de modelagem nao define o espaco entre slots, o h_i nem a posicao das transversais;
esses valores sao premissas nossas (config.GEOMETRIA). Os modeladores calcularam, na amostra de
validacao (1.000 pedidos), a distancia media de sigma_opt em L0 e em L1 (n_min = 300), e guardaram
em dados/amostras/calibracao_n_min.csv:  L0 = 157,234 m  e  L1 = 144,783 m.

Aqui recalculamos essas duas medias com o NOSSO grafo G1 e a NOSSA matriz D. A rota e a de sigma_opt
(Held-Karp, exata, ate 15 secoes), mas nos pedidos com mais de 15 secoes usamos so vizinho mais proximo
+ 2-opt, como (provavelmente) os modeladores: o sigma_opt do projeto parte tambem da varredura por
corredores e fica com a menor rota, o que da ~0,1 m a menos na media e misturaria heuristica com geometria.
    - se bater (diferenca <= TOLERANCIA_VALIDACAO_M), nossa geometria e equivalente a deles;
    - se nao bater, algo difere (h_i, espacamento, transversais ou um bug) e vale descobrir antes
      do experimento.
Isso NAO prova que a loja "de verdade" tem essa geometria: so mostra que usamos a mesma dos modeladores.

Uso (na raiz do repositorio):
    python src/validacao_geometria.py        # imprime a tabela e salva resultados/validacao_geometria.csv
"""
import numpy as np
import pandas as pd

from config import PASTA_RESULTADOS, RAIZ, TOLERANCIA_VALIDACAO_M
from grafo_fisico import carregar_layout, grafo_padrao
from rotas import custo_rota, dois_opt, held_karp, opt_e_exata, sigma_nn

VALIDACAO_CSV = RAIZ / "dados" / "amostras" / "amostra_validacao_1000.csv"
CALIBRACAO_CSV = RAIZ / "dados" / "amostras" / "calibracao_n_min.csv"
SAIDA_CSV = PASTA_RESULTADOS / "validacao_geometria.csv"

N_MIN_FINAL = 300                   # n_min escolhido na calibracao; layout_L1_final.csv corresponde a ele
LAYOUTS_VALIDADOS = ("L0", "L1")    # so existem valores de calibracao para esses dois


def carregar_validacao():
    """Os 1.000 pedidos de validacao: lista de pedidos, cada um uma lista de aisle_id.

    No CSV, a coluna 'aisles' traz as secoes separadas por ';' (por exemplo '84;94').
    A ordem nao importa aqui: sigma_opt nao depende da ordem em que as secoes chegam.
    """
    tabela = pd.read_csv(VALIDACAO_CSV)
    return [[int(a) for a in str(texto).split(";")] for texto in tabela["aisles"]]


def esperado_calibracao():
    """Distancias medias dos modeladores (linha n_min = 300), lidas do CSV e nao copiadas no codigo.

    Devolve {"L0": ..., "L1": ...}, em metros.
    """
    tabela = pd.read_csv(CALIBRACAO_CSV)
    linha = tabela[tabela["n_min"] == N_MIN_FINAL]
    if linha.empty:
        raise ValueError(f"n_min = {N_MIN_FINAL} nao esta em {CALIBRACAO_CSV}")
    linha = linha.iloc[0]
    return {"L0": float(linha["dist_L0_validacao_m"]),
            "L1": float(linha["dist_media_validacao_m"])}


def custo_validacao(slots, D, g):
    """Custo da rota usada na validacao.

    Ate 15 secoes: Held-Karp (exato), igual ao sigma_opt. Acima: so vizinho mais proximo + 2-opt
    (sem a segunda partida pela varredura por corredores que o sigma_opt faz).
    """
    if opt_e_exata(slots):
        return custo_rota(held_karp(slots, D, g), D, g)
    return custo_rota(dois_opt(sigma_nn(slots, D, g), D, g), D, g)


def media_opt(pedidos, mapa, D, g, rotulo=None):
    """Distancia media da rota de validacao (ver custo_validacao) nos pedidos, com o mapeamento dado.

    mapa: dicionario aisle_id -> (corredor, posicao), vindo de carregar_layout(...)[1].
    Devolve (media em metros, quantos pedidos usaram a heuristica, isto e, tinham mais de 15 secoes).
    rotulo: se vier, imprime o andamento (Held-Karp e lento nos pedidos grandes).
    """
    custos = []
    heuristicos = 0
    for i, secoes in enumerate(pedidos, start=1):
        slots = [g.indice_slot(*mapa[a]) for a in secoes]
        custos.append(custo_validacao(slots, D, g))
        heuristicos += not opt_e_exata(slots)
        if rotulo and i % 100 == 0:
            print(f"  {rotulo}: {i}/{len(pedidos)} pedidos", flush=True)
    return float(np.mean(custos)), heuristicos


def montar_tabela(obtidas, esperadas, heuristicos, tolerancia=TOLERANCIA_VALIDACAO_M):
    """Compara o que recalculamos com o que os modeladores obtiveram. Uma linha por layout.

    obtidas, esperadas, heuristicos: dicionarios layout -> valor.
    dentro_da_tolerancia: True quando |obtida - esperada| <= tolerancia.
    """
    linhas = []
    for nome in obtidas:
        diferenca = obtidas[nome] - esperadas[nome]
        linhas.append({
            "layout": nome,
            "distancia_obtida_m": obtidas[nome],
            "distancia_calibracao_m": esperadas[nome],
            "diferenca_m": diferenca,
            "pedidos_heuristicos": heuristicos[nome],
            "dentro_da_tolerancia": bool(abs(diferenca) <= tolerancia),
        })
    return pd.DataFrame(linhas)


def main():
    g = grafo_padrao()
    D = g.matriz_D()                                   # Dijkstra a partir de cada no, uma vez so
    pedidos = carregar_validacao()
    esperadas = esperado_calibracao()

    obtidas, heuristicos = {}, {}
    for nome in LAYOUTS_VALIDADOS:
        _, mapa = carregar_layout(nome)
        obtidas[nome], heuristicos[nome] = media_opt(pedidos, mapa, D, g, rotulo=nome)

    tabela = montar_tabela(obtidas, esperadas, heuristicos)
    PASTA_RESULTADOS.mkdir(exist_ok=True)
    tabela.to_csv(SAIDA_CSV, index=False, float_format="%.3f")

    print(f"\nValidacao da geometria ({len(pedidos)} pedidos, n_min = {N_MIN_FINAL}, "
          f"tolerancia = {TOLERANCIA_VALIDACAO_M} m)")
    print(tabela.to_string(index=False, float_format=lambda x: f"{x:.3f}"))
    print("\nSalvo em", SAIDA_CSV)
    if not tabela["dentro_da_tolerancia"].all():
        raise SystemExit("FALHA: a geometria nao reproduz a calibracao dos modeladores.")
    print("OK: a geometria reproduz a calibracao dos modeladores.")


if __name__ == "__main__":
    main()
