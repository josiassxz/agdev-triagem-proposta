"""Testes das regras R1–R6, da precedência e das pendências.

Organização:
  1. Os 5 exemplos do enunciado (resultado esperado definido por nós)
  2. Uma seção por regra: caso positivo, negativo e de borda
  3. Precedência e acúmulo de motivos
  4. Pendências
  5. Robustez da entrada
"""

import json
from pathlib import Path

import pytest

from regras import (
    CAMPOS_OBRIGATORIOS,
    PENDENCIA_RECUSA,
    Parecer,
    avaliar,
)

EXEMPLOS = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "triagem-proposta" / "exemplos"

SEGUE = Parecer.SEGUE
REVISAO = Parecer.REVISAO_HUMANA
RECUSADA = Parecer.RECUSADA


def proposta(**alteracoes):
    """Proposta-base que SEGUE (igual à P-001); cada teste muda só o que importa."""
    base = {
        "id": "T-001",
        "area_degradada_ha": 850,
        "area_matricula_ha": 1200,
        "area_car_ha": 1190,
        "alerta_desmatamento": None,
        "situacao_car": "Ativo",
        "situacao_cadastral": "Regular",
    }
    base.update(alteracoes)
    return base


def sem(campo):
    p = proposta()
    del p[campo]
    return p


def regras(resultado):
    return [o.regra for o in resultado.ocorrencias]


# ---------------------------------------------------------------------------
# 1. Exemplos do enunciado
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "arquivo, parecer, regras_esperadas",
    [
        ("P-001", SEGUE, []),
        ("P-002", RECUSADA, ["R1"]),
        ("P-003", REVISAO, ["R5"]),
        ("P-004", RECUSADA, ["R2", "R3"]),   # recusa vence, mas lista os dois motivos
        ("P-005", REVISAO, ["R4", "R6"]),   # R5 não avaliada por falta da matrícula
    ],
)
def test_exemplos_do_enunciado(arquivo, parecer, regras_esperadas):
    dados = json.loads((EXEMPLOS / f"{arquivo}.json").read_text(encoding="utf-8"))
    resultado = avaliar(dados)
    assert resultado.parecer is parecer
    assert regras(resultado) == regras_esperadas


def test_p005_informa_que_r5_nao_foi_avaliada():
    dados = json.loads((EXEMPLOS / "P-005.json").read_text(encoding="utf-8"))
    assert avaliar(dados).nao_avaliadas == ["R5 (falta area_matricula_ha)"]


# ---------------------------------------------------------------------------
# 2. Regras individuais
# ---------------------------------------------------------------------------
class TestR1AreaMinima:
    @pytest.mark.parametrize("area", [100, 100.0, 100.01, 5000])
    def test_a_partir_de_100_ha_segue(self, area):
        assert avaliar(proposta(area_degradada_ha=area)).parecer is SEGUE

    @pytest.mark.parametrize("area", [99.99, 99, 1])
    def test_abaixo_de_100_ha_recusa(self, area):
        r = avaliar(proposta(area_degradada_ha=area))
        assert r.parecer is RECUSADA
        assert regras(r) == ["R1"]

    @pytest.mark.parametrize("valor", ["850", "1.200", 0, -10, True, [850], float("nan")])
    def test_valor_invalido_vai_para_revisao(self, valor):
        r = avaliar(proposta(area_degradada_ha=valor))
        assert r.parecer is REVISAO
        assert regras(r) == ["R1"]
        assert "valor inválido" in r.ocorrencias[0].motivo


class TestR2AlertaDesmatamento:
    @pytest.mark.parametrize("alerta", [None, [], "01/01/2020", "2020-01-01", "31/12/2019"])
    def test_sem_alerta_ou_ate_a_data_de_corte_segue(self, alerta):
        assert avaliar(proposta(alerta_desmatamento=alerta)).parecer is SEGUE

    @pytest.mark.parametrize("alerta", ["02/01/2020", "2020-01-02", "15/03/2023", " 15/03/2023 "])
    def test_alerta_depois_da_data_de_corte_recusa(self, alerta):
        r = avaliar(proposta(alerta_desmatamento=alerta))
        assert r.parecer is RECUSADA
        assert regras(r) == ["R2"]

    def test_data_entre_cortes_2020_e_2021_recusa(self):
        """O enunciado dizia 2021; o esclarecimento de 13/10 mudou para 2020."""
        assert avaliar(proposta(alerta_desmatamento="15/06/2020")).parecer is RECUSADA

    def test_lista_com_um_alerta_antigo_e_um_novo_recusa(self):
        r = avaliar(proposta(alerta_desmatamento=["10/05/2018", "20/08/2022"]))
        assert r.parecer is RECUSADA
        assert "20/08/2022" in r.ocorrencias[0].motivo
        assert "10/05/2018" not in r.ocorrencias[0].motivo

    def test_lista_so_com_alertas_antigos_segue(self):
        r = avaliar(proposta(alerta_desmatamento=["10/05/2018", "01/01/2020"]))
        assert r.parecer is SEGUE

    @pytest.mark.parametrize("alerta", ["15-03-2023", "31/02/2023", "ontem", 20230315, ["2023/03/15"]])
    def test_data_ilegivel_vai_para_revisao(self, alerta):
        r = avaliar(proposta(alerta_desmatamento=alerta))
        assert r.parecer is REVISAO
        assert regras(r) == ["R2"]

    def test_data_ilegivel_nao_esconde_alerta_valido_posterior(self):
        r = avaliar(proposta(alerta_desmatamento=["xx/yy/zzzz", "20/08/2022"]))
        assert r.parecer is RECUSADA
        assert [o.efeito for o in r.ocorrencias] == [RECUSADA, REVISAO]

    def test_objeto_no_lugar_de_data_vai_para_revisao(self):
        r = avaliar(proposta(alerta_desmatamento={"data": "15/03/2023"}))
        assert r.parecer is REVISAO
        assert "formato inválido" in r.ocorrencias[0].motivo


class TestR3SituacaoCar:
    @pytest.mark.parametrize("valor", ["Ativo", "ativo", "ATIVO", "  Ativo  "])
    def test_ativo_segue_com_normalizacao(self, valor):
        assert avaliar(proposta(situacao_car=valor)).parecer is SEGUE

    @pytest.mark.parametrize("valor", ["Pendente", " PENDENTE "])
    def test_pendente_vai_para_revisao(self, valor):
        r = avaliar(proposta(situacao_car=valor))
        assert r.parecer is REVISAO
        assert regras(r) == ["R3"]

    @pytest.mark.parametrize("valor", ["Cancelado", "Suspenso", "suspenso"])
    def test_cancelado_ou_suspenso_recusa(self, valor):
        r = avaliar(proposta(situacao_car=valor))
        assert r.parecer is RECUSADA
        assert regras(r) == ["R3"]

    @pytest.mark.parametrize("valor", ["Inexistente", "Ativa", "Em análise", 1])
    def test_valor_desconhecido_vai_para_revisao_citando_o_valor(self, valor):
        r = avaliar(proposta(situacao_car=valor))
        assert r.parecer is REVISAO
        assert repr(valor) in r.ocorrencias[0].motivo


class TestR4SituacaoCadastral:
    @pytest.mark.parametrize("valor", ["Regular", "regular", " REGULAR "])
    def test_regular_segue(self, valor):
        assert avaliar(proposta(situacao_cadastral=valor)).parecer is SEGUE

    @pytest.mark.parametrize(
        "valor", ["Pendente de regularização", "Suspensa", "Cancelada", "Nula", "Ativa", "Irregular"]
    )
    def test_qualquer_outra_situacao_vai_para_revisao(self, valor):
        r = avaliar(proposta(situacao_cadastral=valor))
        assert r.parecer is REVISAO
        assert regras(r) == ["R4"]
        assert valor in r.ocorrencias[0].motivo


class TestR5DivergenciaDeArea:
    @pytest.mark.parametrize("car", [1050, 950])
    def test_diferenca_de_exatamente_5_por_cento_nao_aciona(self, car):
        assert avaliar(proposta(area_matricula_ha=1000, area_car_ha=car)).parecer is SEGUE

    @pytest.mark.parametrize("car", [1050.01, 949.99])
    def test_diferenca_logo_acima_de_5_por_cento_vai_para_revisao(self, car):
        r = avaliar(proposta(area_matricula_ha=1000, area_car_ha=car))
        assert r.parecer is REVISAO
        assert regras(r) == ["R5"]

    def test_limite_exato_com_decimais_nao_sofre_erro_de_ponto_flutuante(self):
        # Em float puro: abs(102.1 - 107.205) > 102.1 * 0.05 é True (falso positivo).
        # A diferença real é 5,105 ha, exatamente 5% de 102,1 ha: não deve acionar.
        assert abs(102.1 - 107.205) > 102.1 * 0.05  # documenta a armadilha do float
        assert avaliar(proposta(area_matricula_ha=102.1, area_car_ha=107.205)).parecer is SEGUE

    def test_base_do_percentual_e_a_matricula_e_nao_o_car(self):
        # diferença 50: 5% de 1000 (matrícula) = 50 -> segue; 5% de 950 (CAR) = 47,5 -> acionaria
        assert avaliar(proposta(area_matricula_ha=1000, area_car_ha=950)).parecer is SEGUE

    def test_motivo_mostra_numeros_para_conferencia(self):
        r = avaliar(proposta(area_matricula_ha=900, area_car_ha=1000))
        motivo = r.ocorrencias[0].motivo
        assert "100 ha" in motivo and "45 ha" in motivo and "11,11%" in motivo

    @pytest.mark.parametrize("campo", ["area_matricula_ha", "area_car_ha"])
    def test_area_invalida_vai_para_revisao(self, campo):
        r = avaliar(proposta(**{campo: "1.200"}))
        assert r.parecer is REVISAO
        assert regras(r) == ["R5"]


class TestR6CamposObrigatorios:
    @pytest.mark.parametrize("campo", CAMPOS_OBRIGATORIOS)
    def test_cada_campo_ausente_vai_para_revisao_dizendo_qual(self, campo):
        r = avaliar(sem(campo))
        assert r.parecer is REVISAO
        r6 = [o for o in r.ocorrencias if o.regra == "R6"]
        assert len(r6) == 1 and campo in r6[0].motivo

    def test_alerta_nulo_e_valido_mas_alerta_ausente_nao(self):
        assert avaliar(proposta(alerta_desmatamento=None)).parecer is SEGUE
        assert avaliar(sem("alerta_desmatamento")).parecer is REVISAO

    @pytest.mark.parametrize("campo", ["area_degradada_ha", "situacao_car", "id"])
    def test_outros_campos_nulos_contam_como_ausentes(self, campo):
        r = avaliar(proposta(**{campo: None}))
        assert regras(r) == ["R6"]

    @pytest.mark.parametrize("valor", ["", "   "])
    def test_texto_vazio_conta_como_ausente(self, valor):
        assert regras(avaliar(proposta(situacao_cadastral=valor))) == ["R6"]

    def test_lista_todos_os_campos_ausentes(self):
        r = avaliar({})
        assert r.parecer is REVISAO
        assert len(r.ocorrencias) == len(CAMPOS_OBRIGATORIOS)
        assert len(r.nao_avaliadas) == 5  # R1 a R5

    def test_campo_ausente_impede_recusa_pela_regra_dependente(self):
        """Sem a área degradada não dá para recusar por R1: vai para revisão."""
        r = avaliar(sem("area_degradada_ha"))
        assert r.parecer is REVISAO
        assert "R1 (falta area_degradada_ha)" in r.nao_avaliadas

    def test_campos_extras_sao_ignorados(self):
        assert avaliar(proposta(observacao="qualquer coisa")).parecer is SEGUE


# ---------------------------------------------------------------------------
# 3. Precedência e acúmulo de motivos
# ---------------------------------------------------------------------------
def test_recusa_vence_revisao_e_todos_os_motivos_sao_listados():
    r = avaliar(proposta(
        area_degradada_ha=50,                 # R1 recusa
        alerta_desmatamento="20/08/2022",     # R2 recusa
        situacao_car="Pendente",              # R3 revisão
        situacao_cadastral="Suspensa",        # R4 revisão
        area_car_ha=2000,                     # R5 revisão
    ))
    assert r.parecer is RECUSADA
    assert regras(r) == ["R1", "R2", "R3", "R4", "R5"]


def test_revisao_com_varios_motivos_nao_para_na_primeira_falha():
    r = avaliar(proposta(situacao_car="Pendente", situacao_cadastral="Suspensa", area_car_ha=2000))
    assert r.parecer is REVISAO
    assert regras(r) == ["R3", "R4", "R5"]


def test_resultado_e_deterministico():
    p = proposta(situacao_car="Pendente", alerta_desmatamento=["2023-01-01", "2021-05-05"])
    assert avaliar(p).to_dict() == avaliar(dict(p)).to_dict()


# ---------------------------------------------------------------------------
# 4. Pendências
# ---------------------------------------------------------------------------
def test_segue_nao_tem_pendencias():
    assert avaliar(proposta()).pendencias == []


def test_revisao_tem_uma_pendencia_por_problema():
    r = avaliar(proposta(situacao_car="Pendente", situacao_cadastral="Suspensa"))
    assert len(r.pendencias) == 2
    assert all(p != PENDENCIA_RECUSA for p in r.pendencias)


def test_recusa_comeca_pela_comunicacao_e_mantem_itens_de_revisao_marcados():
    r = avaliar(proposta(area_degradada_ha=50, situacao_car="Pendente"))
    assert r.pendencias[0] == PENDENCIA_RECUSA
    assert r.pendencias[1].startswith("Se a proposta for reapresentada:")


def test_recusa_sem_itens_de_revisao_tem_so_a_comunicacao():
    assert avaliar(proposta(area_degradada_ha=50)).pendencias == [PENDENCIA_RECUSA]


# ---------------------------------------------------------------------------
# 5. Robustez da entrada
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("entrada", [None, [], "P-001", 42])
def test_entrada_que_nao_e_objeto_gera_erro_explicito(entrada):
    with pytest.raises(TypeError):
        avaliar(entrada)


def test_avaliar_nao_altera_a_proposta_recebida():
    p = proposta(alerta_desmatamento=["20/08/2022"])
    copia = json.loads(json.dumps(p))
    avaliar(p)
    assert p == copia


def test_id_numerico_e_aceito_e_aparece_como_texto():
    assert avaliar(proposta(id=7)).id == "7"


def test_alerta_repetido_aparece_uma_vez_no_motivo():
    r = avaliar(proposta(alerta_desmatamento=["20/08/2022", "2022-08-20"]))
    assert r.ocorrencias[0].motivo.count("20/08/2022") == 1


def test_percentual_logo_acima_do_limite_nao_aparece_como_5_por_cento():
    # 5.001 / 100.000 = 5,001%: com 2 casas viraria "5,00%", contradizendo "acima do limite".
    r = avaliar(proposta(area_matricula_ha=100000, area_car_ha=105001))
    assert r.parecer is REVISAO
    assert "5,0010%" in r.ocorrencias[0].motivo
