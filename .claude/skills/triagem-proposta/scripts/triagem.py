#!/usr/bin/env python3
"""Linha de comando da triagem de propostas.

Uso:
    python triagem.py proposta.json              # card em Markdown
    python triagem.py proposta.json --formato json
    cat proposta.json | python triagem.py -      # lê da entrada padrão

O arquivo pode conter uma proposta (objeto) ou várias (lista de objetos).

Códigos de saída:
    0  triagem concluída (qualquer parecer)
    2  entrada inválida: arquivo inexistente ou ilegível, JSON malformado, lista
       vazia ou item que não é objeto. Nesse caso nenhum parecer é emitido.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from card import gerar_card                 # Resultado -> Markdown
from regras import VERSAO_REGRAS, avaliar   # proposta -> Resultado

ERRO_ENTRADA = 2  # código de saída para entrada inválida


def _ler_entrada(origem: str) -> Any:
    """Lê o JSON de um arquivo ou, se a origem for '-', da entrada padrão."""
    if origem == "-":
        texto = sys.stdin.buffer.read().decode("utf-8-sig")
    else:
        texto = Path(origem).read_text(encoding="utf-8-sig")  # aceita BOM do Windows
    return json.loads(texto)


def main(argv: list[str] | None = None) -> int:
    """Lê as propostas, roda a triagem e imprime o resultado. Devolve o código de saída."""
    for fluxo in (sys.stdout, sys.stderr):  # acentos e emojis no Windows
        if hasattr(fluxo, "reconfigure"):
            fluxo.reconfigure(encoding="utf-8")

    # 1. Argumentos da linha de comando.
    parser = argparse.ArgumentParser(
        prog="triagem",
        description="Triagem de propostas de recuperação de pastagem (regras R1–R6).",
    )
    parser.add_argument("entrada", help="arquivo JSON com a proposta (ou lista), ou '-' para stdin")
    parser.add_argument(
        "--formato", choices=("md", "json"), default="md",
        help="md = card em Markdown (padrão); json = resultado estruturado",
    )
    parser.add_argument("--versao", action="version", version=f"regras v{VERSAO_REGRAS}")
    args = parser.parse_args(argv)

    # 2. Leitura do JSON. Cada erro tem uma mensagem clara e sai com código 2, sem parecer.
    try:
        dados = _ler_entrada(args.entrada)
    except FileNotFoundError:
        print(f"Erro: arquivo não encontrado: {args.entrada}", file=sys.stderr)
        return ERRO_ENTRADA
    except UnicodeDecodeError:
        print("Erro: o arquivo não está em UTF-8. Salve o JSON como UTF-8 e tente de novo.",
              file=sys.stderr)
        return ERRO_ENTRADA
    except OSError as erro:
        print(f"Erro: não foi possível ler {args.entrada} ({erro.strerror}).", file=sys.stderr)
        return ERRO_ENTRADA
    except json.JSONDecodeError as erro:
        print(f"Erro: JSON inválido ({erro.msg}, linha {erro.lineno}, coluna {erro.colno}).",
              file=sys.stderr)
        return ERRO_ENTRADA

    # 3. Aceita uma proposta ou uma lista. Valida tudo antes de avaliar, para não
    #    emitir parecer parcial de um lote com item inválido.
    propostas = dados if isinstance(dados, list) else [dados]
    if not propostas:
        print("Erro: a lista de propostas está vazia.", file=sys.stderr)
        return ERRO_ENTRADA
    for posicao, proposta in enumerate(propostas, start=1):
        if not isinstance(proposta, dict):
            print(f"Erro: o item {posicao} não é um objeto JSON de proposta.", file=sys.stderr)
            return ERRO_ENTRADA

    # 4. Triagem: o parecer sai daqui, do motor em regras.py.
    resultados = [avaliar(p) for p in propostas]

    # 5. Saída: JSON (objeto ou lista, igual à entrada) ou cards em Markdown.
    if args.formato == "json":
        saida = [r.to_dict() for r in resultados]
        print(json.dumps(saida if isinstance(dados, list) else saida[0],
                         ensure_ascii=False, indent=2))
    else:
        print("\n".join(gerar_card(r) for r in resultados), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
