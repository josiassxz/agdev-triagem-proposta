"""Gera o resumo em Markdown (card de tarefa) a partir de um Resultado."""

from __future__ import annotations

from regras import Parecer, Resultado

# Ícone que aparece ao lado do parecer.
_ICONE = {
    Parecer.SEGUE: "🟢",
    Parecer.REVISAO_HUMANA: "🟡",
    Parecer.RECUSADA: "🔴",
}

# Rótulo entre parênteses em cada motivo: "- **R2** (recusa): ...".
_EFEITO_CURTO = {
    Parecer.REVISAO_HUMANA: "revisão humana",
    Parecer.RECUSADA: "recusa",
}


def titulo(resultado: Resultado) -> str:
    """'Triagem P-004 — RECUSADA'. Também serve de nome da tarefa numa integração."""
    ident = resultado.id or "(sem id)"
    return f"Triagem {ident} — {resultado.parecer.value}"


def gerar_card(resultado: Resultado) -> str:
    """Monta o card: título, parecer, motivos, pendências, regras não avaliadas e rodapé."""
    # Cabeçalho: título e parecer com ícone.
    linhas = [
        f"## {titulo(resultado)}",
        "",
        f"**Parecer:** {_ICONE[resultado.parecer]} {resultado.parecer.value}",
        "",
        "**Motivos**",
        "",
    ]
    # Motivos: uma linha por regra que falhou.
    if resultado.ocorrencias:
        for o in resultado.ocorrencias:
            linhas.append(f"- **{o.regra}** ({_EFEITO_CURTO[o.efeito]}): {o.motivo}")
    else:
        linhas.append("- Todas as regras (R1 a R6) foram atendidas.")

    # Pendências em formato de checklist ("- [ ]"), para virar tarefa.
    linhas += ["", "**Pendências**", ""]
    if resultado.pendencias:
        linhas += [f"- [ ] {p}" for p in resultado.pendencias]
    else:
        linhas.append("- Nenhuma.")

    # Seção opcional: só aparece se alguma regra foi pulada por falta de dado.
    if resultado.nao_avaliadas:
        linhas += ["", "**Regras não avaliadas por falta de dado**", ""]
        linhas += [f"- {r}" for r in resultado.nao_avaliadas]

    # Rodapé com a versão das regras, para saber qual regra valeu nesta triagem.
    linhas += [
        "",
        "---",
        f"_Triagem automática · regras v{resultado.versao_regras} · "
        "não substitui a análise do comitê de crédito._",
    ]
    return "\n".join(linhas) + "\n"
