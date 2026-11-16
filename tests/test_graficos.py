"""Testes das figuras: os dados que entram nos graficos e a geracao dos arquivos (PNG e PDF).

Um teste automatico nao diz se o grafico esta bonito ou legivel; isso se confere abrindo as imagens em
resultados/figuras/. Aqui se confere o que da para conferir: as contas, que os arquivos existem e sao
validos, e que rodar duas vezes gera arquivos identicos.

Rodar na raiz do repositorio:  python tests/test_graficos.py
"""
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from config import LAYOUTS                                                           # noqa: E402
from experimento import FAIXAS_SECOES                                                # noqa: E402
from graficos import (dados_boxplot, faixas_presentes, figura_distancia,             # noqa: E402
                      figura_ganho_faixa, figura_reducao, formatar_pct, pontos_floresta,
                      serie_ganho_faixa)
from rotas import ESTRATEGIAS                                                        # noqa: E402

BASE = [100, 150, 200, 250, 300, 350]
FATOR_LAYOUT = {"L0": 1.0, "L1": 0.9, "L2": 0.7}
FATOR_ESTRATEGIA = {"ref": 1.0, "corr": 0.6, "nn": 0.65, "opt": 0.55}


def resultados_ficticios():
    """6 pedidos de mentira em formato longo, com as linhas em ordem trocada (para testar a ordenacao)."""
    linhas = [{"id_teste": i, "layout": layout, "estrategia": e,
               "distancia_m": BASE[i - 1] * FATOR_LAYOUT[layout] * FATOR_ESTRATEGIA[e]}
              for layout in LAYOUTS for e in ESTRATEGIAS for i in range(1, 7)]
    return pd.DataFrame(linhas[::-1])


def reducao_ficticia():
    """tabela_reducao_layouts de mentira; no caso (L1 vs L0, nn) o IC contem o 0."""
    valores = {("L1 vs L0", e): (7.0, 4.0, 10.0) for e in ESTRATEGIAS}
    valores[("L1 vs L0", "nn")] = (1.0, -2.0, 3.0)
    valores.update({("L2 vs L0", e): (20.0, 15.0, 25.0) for e in ESTRATEGIAS})
    valores.update({("L1 vs L2", e): (-20.0, -25.0, -15.0) for e in ESTRATEGIAS})
    return pd.DataFrame([{"estrategia": e, "comparacao": c, "reducao_pct": v[0], "ic_inf_pct": v[1],
                          "ic_sup_pct": v[2]} for (c, e), v in valores.items()])


def faixas_ficticias(sem=()):
    """tabela_ganho_faixa_secoes de mentira: 7 faixas, ganho crescente; so a faixa 16+ tem pedidos heuristicos.
    sem: nomes de faixas a omitir. As linhas saem em ordem trocada."""
    linhas = []
    for layout in LAYOUTS:
        for e in ("corr", "nn", "opt"):
            for i, (nome, _, _) in enumerate(FAIXAS_SECOES):
                if nome in sem:
                    continue
                ganho = 10.0 * (i + 1) + (0 if e == "corr" else 1 if e == "nn" else 2)
                linhas.append({"layout": layout, "faixa_secoes": nome, "n_pedidos": 10 + i, "estrategia": e,
                               "ganho_medio_pct": ganho, "ic_inf_pct": ganho - 3, "ic_sup_pct": ganho + 3,
                               "n_pedidos_opt_heuristico": 8 if nome == "16+" else 0})
    return pd.DataFrame(linhas[::-1])


def test_formatar_pct():
    assert formatar_pct(-6.7) == "−6,7%"
    assert formatar_pct(7.44) == "+7,4%"
    assert formatar_pct(0.0) == "+0,0%"


def test_dados_boxplot_a_mao():
    dados = dados_boxplot(resultados_ficticios())
    assert set(dados) == set(ESTRATEGIAS) and all(set(dados[e]) == set(LAYOUTS) for e in ESTRATEGIAS)
    esperado = np.array(BASE) * 0.9 * 0.55                       # opt em L1, pedidos 1 a 6 (ordem de id_teste)
    assert np.allclose(dados["opt"]["L1"], esperado)
    assert np.allclose(dados["ref"]["L0"], BASE)
    assert all(len(dados[e][layout]) == 6 for e in ESTRATEGIAS for layout in LAYOUTS)


def test_pontos_floresta_a_mao():
    pontos = pontos_floresta(reducao_ficticia())
    assert list(pontos) == ["L1 vs L0", "L2 vs L0", "L1 vs L2"]                 # ordem dos paineis
    assert all(list(t.index) == list(ESTRATEGIAS) for t in pontos.values())     # ref no topo, opt embaixo
    assert not pontos["L1 vs L0"].loc["nn", "exclui_zero"]                       # IC de -2 a 3 contem o 0
    assert pontos["L1 vs L0"].loc["opt", "exclui_zero"]                          # IC de 4 a 10: so positivo
    assert pontos["L1 vs L2"]["exclui_zero"].all()                               # IC de -25 a -15: so negativo
    assert pontos["L2 vs L0"].loc["corr", "reducao_pct"] == 20.0


def test_serie_ganho_faixa_em_ordem():
    tabela = faixas_ficticias()
    s = serie_ganho_faixa(tabela, "L1", "opt")
    assert list(s["faixa_secoes"]) == [nome for nome, _, _ in FAIXAS_SECOES]    # ordem das faixas, nao da tabela
    assert list(s["ganho_medio_pct"]) == [12.0, 22.0, 32.0, 42.0, 52.0, 62.0, 72.0]
    assert list(s["n_pedidos"]) == [10, 11, 12, 13, 14, 15, 16]


def test_faixas_presentes_pula_as_ausentes():
    tabela = faixas_ficticias(sem=("5-6",))
    assert "5-6" not in faixas_presentes(tabela) and len(faixas_presentes(tabela)) == 6
    assert list(serie_ganho_faixa(tabela, "L0", "nn")["faixa_secoes"]) == faixas_presentes(tabela)


def _desenhar(pasta):
    base = Path(pasta)
    return (figura_distancia(resultados_ficticios(), base / "f1")
            + figura_reducao(reducao_ficticia(), base / "f2")
            + figura_ganho_faixa(faixas_ficticias(), base / "f3"))


def test_figuras_geram_png_e_pdf_validos():
    with tempfile.TemporaryDirectory() as pasta:
        caminhos = _desenhar(pasta)
        assert len(caminhos) == 6
        for c in caminhos:
            conteudo = c.read_bytes()
            assert len(conteudo) > 5000, c                                       # nao e um arquivo vazio
            assert conteudo.startswith(b"\x89PNG\r\n\x1a\n" if c.suffix == ".png" else b"%PDF"), c


def test_figuras_reprodutiveis():
    with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
        for c1, c2 in zip(_desenhar(a), _desenhar(b)):
            assert c1.name == c2.name and c1.read_bytes() == c2.read_bytes(), c1.name


if __name__ == "__main__":
    for nome, f in list(globals().items()):
        if nome.startswith("test_") and callable(f):
            f()
            print("OK", nome)
