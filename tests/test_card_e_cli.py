"""Testes do card em Markdown e da linha de comando."""

import json
import subprocess
import sys
from pathlib import Path

from card import gerar_card, titulo
from regras import avaliar

SKILL = Path(__file__).resolve().parents[1] / ".claude" / "skills" / "triagem-proposta"
SCRIPT = SKILL / "scripts" / "triagem.py"
EXEMPLOS = SKILL / "exemplos"


def carregar(nome):
    return json.loads((EXEMPLOS / f"{nome}.json").read_text(encoding="utf-8"))


def rodar(*args, entrada=None):
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=entrada, capture_output=True, text=True, encoding="utf-8",
    )


# --- Card --------------------------------------------------------------------
def test_card_tem_titulo_parecer_motivos_e_pendencias():
    card = gerar_card(avaliar(carregar("P-004")))
    assert card.startswith("## Triagem P-004 — RECUSADA\n")
    for secao in ("**Parecer:**", "**Motivos**", "**Pendências**"):
        assert secao in card
    assert "- **R2** (recusa):" in card
    assert "- **R3** (revisão humana):" in card
    assert "- [ ] Comunicar a recusa" in card


def test_card_de_proposta_que_segue():
    card = gerar_card(avaliar(carregar("P-001")))
    assert "🟢 SEGUE" in card
    assert "Todas as regras (R1 a R6) foram atendidas." in card
    assert "**Pendências**\n\n- Nenhuma." in card


def test_card_mostra_regras_nao_avaliadas():
    card = gerar_card(avaliar(carregar("P-005")))
    assert "**Regras não avaliadas por falta de dado**" in card
    assert "- R5 (falta area_matricula_ha)" in card


def test_card_traz_versao_das_regras():
    assert "regras v1.0.0" in gerar_card(avaliar(carregar("P-001")))


def test_titulo_sem_id():
    assert titulo(avaliar({})) == "Triagem (sem id) — REVISÃO HUMANA"


# --- CLI ---------------------------------------------------------------------
def test_cli_markdown_por_padrao():
    r = rodar(str(EXEMPLOS / "P-003.json"))
    assert r.returncode == 0
    assert r.stdout.startswith("## Triagem P-003 — REVISÃO HUMANA")


def test_cli_json_de_uma_proposta():
    r = rodar(str(EXEMPLOS / "P-002.json"), "--formato", "json")
    saida = json.loads(r.stdout)
    assert saida["parecer"] == "RECUSADA"
    assert saida["motivos"][0]["regra"] == "R1"
    assert saida["versao_regras"] == "1.0.0"


def test_cli_lote_mantem_a_ordem():
    r = rodar(str(EXEMPLOS / "todas.json"), "--formato", "json")
    pareceres = [item["parecer"] for item in json.loads(r.stdout)]
    assert pareceres == ["SEGUE", "RECUSADA", "REVISÃO HUMANA", "RECUSADA", "REVISÃO HUMANA"]


def test_cli_le_da_entrada_padrao():
    r = rodar("-", entrada=json.dumps(carregar("P-001")))
    assert r.returncode == 0 and "SEGUE" in r.stdout


def test_cli_json_malformado_retorna_erro_2():
    r = rodar("-", entrada='{"id": "P-001",')
    assert r.returncode == 2
    assert "JSON inválido" in r.stderr
    assert r.stdout == ""


def test_cli_arquivo_inexistente_retorna_erro_2():
    r = rodar("nao-existe.json")
    assert r.returncode == 2
    assert "não encontrado" in r.stderr


def test_cli_item_que_nao_e_objeto_retorna_erro_2():
    r = rodar("-", entrada='[{"id": "P-001"}, "lixo"]')
    assert r.returncode == 2
    assert "item 2" in r.stderr


def test_cli_lista_vazia_retorna_erro_2():
    r = rodar("-", entrada="[]")
    assert r.returncode == 2 and "vazia" in r.stderr


def test_cli_aceita_json_com_bom(tmp_path):
    arquivo = tmp_path / "bom.json"
    arquivo.write_text(json.dumps(carregar("P-001")), encoding="utf-8-sig")
    r = rodar(str(arquivo))
    assert r.returncode == 0 and "SEGUE" in r.stdout


def test_cli_arquivo_fora_de_utf8_retorna_erro_2(tmp_path):
    arquivo = tmp_path / "latin1.json"
    arquivo.write_bytes('{"situacao_cadastral": "Pendente de regularização"}'.encode("latin-1"))
    r = rodar(str(arquivo))
    assert r.returncode == 2 and "UTF-8" in r.stderr


def test_cli_pasta_no_lugar_de_arquivo_retorna_erro_2(tmp_path):
    r = rodar(str(tmp_path))
    assert r.returncode == 2 and "Traceback" not in r.stderr
