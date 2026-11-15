"""Testes das estrategias de rota e do mapeamento dos layouts.

Rodar na raiz do repositorio:  python tests/test_rotas.py
"""
import itertools
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import LIMITE_HELD_KARP                                                  # noqa: E402
from grafo_fisico import grafo_padrao, carregar_layout                               # noqa: E402
from rotas import (ESTRATEGIAS, executar, held_karp, dois_opt, sigma_nn,            # noqa: E402
                   custo_rota, opt_e_exata)

g = grafo_padrao()
D = g.matriz_D()


def sorteio():
    """Gerador proprio de cada teste (semente fixa): um teste nao depende da ordem dos outros."""
    return random.Random(42)


def slots_aleatorios(rng, k):
    return rng.sample(range(g.n_slots), k)


def test_mapeamento_dos_layouts():
    slots_l0 = None
    for nome in ("L0", "L1", "L2"):
        _, mapa = carregar_layout(nome)
        assert len(mapa) == 134 and len(set(mapa.values())) == 134      # cada secao em um slot proprio
        slots = set(mapa.values())
        slots_l0 = slots_l0 or slots
        assert slots == slots_l0                                         # mesmos 134 slots nos 3 layouts
        for corredor, posicao in mapa.values():
            g.indice_slot(corredor, posicao)                             # existe no grafo


def test_um_so_ponto_todas_iguais():                                     # hipotese H4
    for s in (0, 50, 133):
        custos = {e: executar(e, [s], D, g)[1] for e in ESTRATEGIAS}
        assert len(set(custos.values())) == 1, custos


def test_todas_visitam_todos_os_slots():
    rng = sorteio()
    for _ in range(30):
        pts = slots_aleatorios(rng, rng.randint(2, 20))
        for e in ESTRATEGIAS:
            ordem, _ = executar(e, pts, D, g)
            assert sorted(ordem) == sorted(pts), (e, ordem)              # permutacao: nenhum slot some ou se repete


def test_ref_mantem_a_ordem_e_executar_remove_repetidos():
    rng = sorteio()
    pts = slots_aleatorios(rng, 8)
    assert executar("ref", pts, D, g)[0] == pts
    com_repeticao = [pts[0], pts[1], pts[0], pts[2], pts[1]]             # duas secoes no mesmo slot = uma parada
    for e in ESTRATEGIAS:
        assert sorted(executar(e, com_repeticao, D, g)[0]) == sorted(pts[:3])
    assert executar("ref", com_repeticao, D, g)[0] == pts[:3]            # mantem a ordem da 1a aparicao


def test_held_karp_igual_forca_bruta():
    rng = sorteio()
    for _ in range(30):
        pts = slots_aleatorios(rng, rng.randint(2, 7))
        melhor = min(custo_rota(list(p), D, g) for p in itertools.permutations(pts))
        assert abs(custo_rota(held_karp(pts, D, g), D, g) - melhor) < 1e-9


def test_opt_nao_perde_para_as_outras():
    rng = sorteio()
    for _ in range(40):
        pts = slots_aleatorios(rng, rng.randint(2, 12))
        custos = {e: executar(e, pts, D, g)[1] for e in ESTRATEGIAS}
        assert custos["opt"] <= min(custos["ref"], custos["corr"], custos["nn"]) + 1e-9, custos


def test_limite_do_held_karp():
    assert opt_e_exata(list(range(LIMITE_HELD_KARP)))
    assert not opt_e_exata(list(range(LIMITE_HELD_KARP + 1)))


def test_opt_acima_do_limite_nao_perde_para_nn_e_corr():
    # ramo heuristico (mais de 15 secoes): por construcao, opt nunca perde para nn nem para corr
    rng = sorteio()
    for _ in range(15):
        pts = slots_aleatorios(rng, rng.randint(LIMITE_HELD_KARP + 1, 22))
        assert not opt_e_exata(pts)
        custos = {e: executar(e, pts, D, g)[1] for e in ESTRATEGIAS}
        assert custos["opt"] <= min(custos["corr"], custos["nn"]) + 1e-9, custos


def test_dois_opt_nao_piora_a_rota():
    rng = sorteio()
    for _ in range(40):
        pts = slots_aleatorios(rng, rng.randint(3, 20))
        nn = sigma_nn(pts, D, g)
        assert custo_rota(dois_opt(nn, D, g), D, g) <= custo_rota(nn, D, g) + 1e-9


def test_corr_varredura_em_s():
    rng = sorteio()
    for _ in range(30):
        pts = slots_aleatorios(rng, rng.randint(2, 15))
        ordem, _ = executar("corr", pts, D, g)
        corredores = [g.slot_corredor[s] for s in ordem]
        assert corredores == sorted(corredores)                          # corredores em ordem crescente
        visitados = sorted(set(corredores))
        for n, c in enumerate(visitados):                                # sentido alterna a cada corredor
            posicoes = [g.slot_posicao[s] for s in ordem if g.slot_corredor[s] == c]
            esperado = sorted(posicoes, reverse=(n % 2 == 1))
            assert posicoes == esperado, (c, posicoes)


def test_corr_exemplo_a_mao():
    # corredor 1: posicoes 2 e 5 (ida: 2, 5); corredor 3: posicoes 1 e 6 (volta: 6, 1); corredor 4: posicao 3
    pts = [g.indice_slot(3, 1), g.indice_slot(1, 5), g.indice_slot(4, 3), g.indice_slot(1, 2), g.indice_slot(3, 6)]
    ordem, _ = executar("corr", pts, D, g)
    esperado = [g.indice_slot(1, 2), g.indice_slot(1, 5), g.indice_slot(3, 6), g.indice_slot(3, 1), g.indice_slot(4, 3)]
    assert ordem == esperado


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("OK", nome)
