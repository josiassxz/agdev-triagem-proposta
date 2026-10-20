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
    """Lê um dos exemplos do enunciado (P-001 a P-005) como dicionário."""
    return json.loads((EXEMPLOS / f"{nome}.json").read_text(encoding="utf-8"))


def rodar(*args, entrada=None):
    """Executa o triagem.py como processo separado, igual ao uso real; devolve código de saída, stdout e stderr."""
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        input=entrada, capture_output=True, text=True, encoding="utf-8",
    )


# --- Card --------------------------------------------------------------------
def test_card_tem_titulo_parecer_motivos_e_pendencias():
    """P-004 (RECUSADA): o card tem título, todas as seções, os dois motivos e a pendência de comunicar a recusa."""
    card = gerar_card(avaliar(carregar("P-004")))
    assert card.startswith("## Triagem P-004 — RECUSADA\n")
    for secao in ("**Parecer:**", "**Motivos**", "**Pendências**"):
        assert secao in card
    assert "- **R2** (recusa):" in card
    assert "- **R3** (revisão humana):" in card
    assert "- [ ] Comunicar a recusa" in card


def test_card_de_proposta_que_segue():
    """P-001 (SEGUE): ícone verde, mensagem de regras atendidas e nenhuma pendência."""
    card = gerar_card(avaliar(carregar("P-001")))
    assert "🟢 SEGUE" in card
    assert "Todas as regras (R1 a R6) foram atendidas." in card
    assert "**Pendências**\n\n- Nenhuma." in card


def test_card_mostra_regras_nao_avaliadas():
    """P-005: a R5 foi pulada por falta da matrícula e isso precisa aparecer no card."""
    card = gerar_card(avaliar(carregar("P-005")))
    assert "**Regras não avaliadas por falta de dado**" in card
    assert "- R5 (falta area_matricula_ha)" in card


def test_card_traz_versao_das_regras():
    """O rodapé mostra a versão das regras, para auditar qual regra valeu."""
    assert "regras v2.0.0" in gerar_card(avaliar(carregar("P-001")))


def test_titulo_sem_id():
    """Proposta vazia: o título não quebra e mostra '(sem id)'."""
    assert titulo(avaliar({})) == "Triagem (sem id) — REVISÃO HUMANA"


# --- CLI ---------------------------------------------------------------------
def test_cli_markdown_por_padrao():
    """Sem --formato, a saída é o card em Markdown e o código de saída é 0."""
    r = rodar(str(EXEMPLOS / "P-003.json"))
    assert r.returncode == 0
    assert r.stdout.startswith("## Triagem P-003 — REVISÃO HUMANA")


def test_cli_json_de_uma_proposta():
    """Com --formato json e uma proposta, a saída é um objeto JSON com parecer, motivos e versão."""
    r = rodar(str(EXEMPLOS / "P-002.json"), "--formato", "json")
    saida = json.loads(r.stdout)
    assert saida["parecer"] == "RECUSADA"
    assert saida["motivos"][0]["regra"] == "R1"
    assert saida["versao_regras"] == "2.0.0"


def test_cli_lote_mantem_a_ordem():
    """Lote (todas.json): devolve uma lista com os pareceres na mesma ordem da entrada."""
    r = rodar(str(EXEMPLOS / "todas.json"), "--formato", "json")
    pareceres = [item["parecer"] for item in json.loads(r.stdout)]
    assert pareceres == ["SEGUE", "RECUSADA", "REVISÃO HUMANA", "RECUSADA", "REVISÃO HUMANA"]


def test_cli_le_da_entrada_padrao():
    """Com '-', lê o JSON da entrada padrão (é assim que o Claude envia JSON colado)."""
    r = rodar("-", entrada=json.dumps(carregar("P-001")))
    assert r.returncode == 0 and "SEGUE" in r.stdout


def test_cli_json_malformado_retorna_erro_2():
    """JSON quebrado: código 2, mensagem no stderr e nenhum parecer no stdout."""
    r = rodar("-", entrada='{"id": "P-001",')
    assert r.returncode == 2
    assert "JSON inválido" in r.stderr
    assert r.stdout == ""


def test_cli_arquivo_inexistente_retorna_erro_2():
    """Arquivo que não existe: código 2 com mensagem clara."""
    r = rodar("nao-existe.json")
    assert r.returncode == 2
    assert "não encontrado" in r.stderr


def test_cli_item_que_nao_e_objeto_retorna_erro_2():
    """Lote com item inválido: código 2, dizendo qual item é o problema."""
    r = rodar("-", entrada='[{"id": "P-001"}, "lixo"]')
    assert r.returncode == 2
    assert "item 2" in r.stderr


def test_cli_lista_vazia_retorna_erro_2():
    """Lista vazia: código 2 (não há o que triar)."""
    r = rodar("-", entrada="[]")
    assert r.returncode == 2 and "vazia" in r.stderr


def test_cli_aceita_json_com_bom(tmp_path):
    """JSON salvo no Windows com BOM (marca no início do arquivo) é aceito normalmente."""
    arquivo = tmp_path / "bom.json"
    arquivo.write_text(json.dumps(carregar("P-001")), encoding="utf-8-sig")
    r = rodar(str(arquivo))
    assert r.returncode == 0 and "SEGUE" in r.stdout


def test_cli_arquivo_fora_de_utf8_retorna_erro_2(tmp_path):
    """Arquivo em Latin-1: código 2 pedindo para salvar em UTF-8, em vez de acentos corrompidos."""
    arquivo = tmp_path / "latin1.json"
    arquivo.write_bytes('{"situacao_cadastral": "Pendente de regularização"}'.encode("latin-1"))
    r = rodar(str(arquivo))
    assert r.returncode == 2 and "UTF-8" in r.stderr


def test_cli_pasta_no_lugar_de_arquivo_retorna_erro_2(tmp_path):
    """Pasta no lugar de arquivo: código 2 com mensagem, sem Traceback do Python."""
    r = rodar(str(tmp_path))
    assert r.returncode == 2 and "Traceback" not in r.stderr
