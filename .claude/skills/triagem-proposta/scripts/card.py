"""Gera o resumo em Markdown (card de tarefa) a partir de um Resultado."""

from __future__ import annotations

from regras import Parecer, Resultado

_ICONE = {
    Parecer.SEGUE: "🟢",
    Parecer.REVISAO_HUMANA: "🟡",
    Parecer.RECUSADA: "🔴",
}

_EFEITO_CURTO = {
    Parecer.REVISAO_HUMANA: "revisão humana",
    Parecer.RECUSADA: "recusa",
}


def titulo(resultado: Resultado) -> str:
    ident = resultado.id or "(sem id)"
    return f"Triagem {ident} — {resultado.parecer.value}"


def gerar_card(resultado: Resultado) -> str:
    linhas = [
        f"## {titulo(resultado)}",
        "",
        f"**Parecer:** {_ICONE[resultado.parecer]} {resultado.parecer.value}",
        "",
        "**Motivos**",
        "",
    ]
    if resultado.ocorrencias:
        for o in resultado.ocorrencias:
            linhas.append(f"- **{o.regra}** ({_EFEITO_CURTO[o.efeito]}): {o.motivo}")
    else:
        linhas.append("- Todas as regras (R1 a R6) foram atendidas.")

    linhas += ["", "**Pendências**", ""]
    if resultado.pendencias:
        linhas += [f"- [ ] {p}" for p in resultado.pendencias]
    else:
        linhas.append("- Nenhuma.")

    if resultado.nao_avaliadas:
        linhas += ["", "**Regras não avaliadas por falta de dado**", ""]
        linhas += [f"- {r}" for r in resultado.nao_avaliadas]

    linhas += [
        "",
        "---",
        f"_Triagem automática · regras v{resultado.versao_regras} · "
        "não substitui a análise do comitê de crédito._",
    ]
    return "\n".join(linhas) + "\n"
