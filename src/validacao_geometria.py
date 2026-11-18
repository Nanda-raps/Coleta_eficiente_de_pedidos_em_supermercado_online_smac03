# Confere se o nosso grafo reproduz a calibracao dos modeladores.
#
# Os modeladores calcularam, em 1.000 pedidos de validacao, a distancia media do sigma_opt em L0
# (157,234 m) e em L1 com n_min = 300 (144,783 m), guardadas em dados/amostras/calibracao_n_min.csv.
# Aqui recalculamos as duas medias com o nosso grafo e a nossa matriz D:
#   - diferenca <= TOLERANCIA_VALIDACAO_M: a nossa geometria e equivalente a deles;
#   - senao: algo difere (h_i, espacamentos, passagens ou um bug).
# Nos pedidos com mais de 15 secoes usamos so nn + 2-opt (e nao o sigma_opt completo),
# para medir a geometria sem misturar com a heuristica.
# Isso nao prova que a loja real tem essa geometria: so que usamos a mesma dos modeladores.
#
# Uso (na raiz do projeto): python src/validacao_geometria.py

import numpy as np
import pandas as pd

from config import PASTA_RESULTADOS, RAIZ, TOLERANCIA_VALIDACAO_M
from grafo_fisico import carregar_layout, grafo_padrao
from rotas import custo_rota, dois_opt, held_karp, opt_e_exata, sigma_nn

VALIDACAO_CSV = RAIZ / "dados" / "amostras" / "amostra_validacao_1000.csv"
CALIBRACAO_CSV = RAIZ / "dados" / "amostras" / "calibracao_n_min.csv"
SAIDA_CSV = PASTA_RESULTADOS / "validacao_geometria.csv"

# n_min escolhido na calibracao; layout_L1_final.csv corresponde a ele.
N_MIN_FINAL = 300
# So L0 e L1 tem valor de calibracao.
LAYOUTS_VALIDADOS = ("L0", "L1")


def carregar_validacao():
    # Os 1.000 pedidos de validacao: cada um e uma lista de aisle_id (coluna 'aisles', separada por ';').
    # A ordem nao importa para o sigma_opt.
    tabela = pd.read_csv(VALIDACAO_CSV)
    return [[int(a) for a in str(texto).split(";")] for texto in tabela["aisles"]]


def esperado_calibracao():
    # Distancias medias dos modeladores (linha n_min = 300 do CSV): {'L0': ..., 'L1': ...}, em metros.
    tabela = pd.read_csv(CALIBRACAO_CSV)
    linha = tabela[tabela["n_min"] == N_MIN_FINAL]
    if linha.empty:
        raise ValueError(f"n_min = {N_MIN_FINAL} nao esta em {CALIBRACAO_CSV}")
    linha = linha.iloc[0]
    return {"L0": float(linha["dist_L0_validacao_m"]),
            "L1": float(linha["dist_media_validacao_m"])}


def custo_validacao(slots, D, g):
    # Custo da rota de validacao: Held-Karp ate 15 secoes; acima disso, so nn + 2-opt.
    if opt_e_exata(slots):
        return custo_rota(held_karp(slots, D, g), D, g)
    return custo_rota(dois_opt(sigma_nn(slots, D, g), D, g), D, g)


def media_opt(pedidos, mapa, D, g, rotulo=None):
    # Distancia media da rota de validacao nos pedidos, no layout dado
    # (mapa = aisle_id -> (corredor, posicao)).
    # Devolve (media em metros, quantos pedidos usaram heuristica).
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
    # Compara o recalculado com o dos modeladores, uma linha por layout.
    # dentro_da_tolerancia = |diferenca| <= tolerancia.
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
    D = g.matriz_D()
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
    # Termina com erro se algum layout fugir da tolerancia.
    if not tabela["dentro_da_tolerancia"].all():
        raise SystemExit("FALHA: a geometria nao reproduz a calibracao dos modeladores.")
    print("OK: a geometria reproduz a calibracao dos modeladores.")


if __name__ == "__main__":
    main()
