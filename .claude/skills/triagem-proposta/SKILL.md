---
name: triagem-proposta
description: Faz a triagem de uma proposta de crédito para recuperação de pastagem degradada (AgDev) aplicando as regras R1–R6 e devolve o parecer SEGUE, RECUSADA ou REVISÃO HUMANA com motivos, pendências e um card em Markdown. Use quando o usuário enviar uma proposta em JSON (ou os dados de uma proposta) e pedir triagem, parecer, análise ou card.
allowed-tools: Bash(python3 ${CLAUDE_SKILL_DIR}/scripts/triagem.py *) Bash(python ${CLAUDE_SKILL_DIR}/scripts/triagem.py *)
---

# Triagem de proposta

O parecer é decidido **somente pelo script** `scripts/triagem.py`. Seu papel é
preparar a entrada, rodar o script e apresentar o resultado. Você nunca decide,
altera ou "corrige" o parecer, nem completa dados que não foram informados.

## Quando usar

- O usuário anexa ou cola uma proposta em JSON (uma ou uma lista) e pede triagem.
- O usuário descreve uma proposta em texto e quer saber se ela segue.

Não use para dúvidas gerais sobre as regras (responda a partir de `REGRAS.md`)
nem para decisão de crédito: esta triagem antecede o comitê, não o substitui.

## Como usar

1. **Monte o JSON** com os 7 campos, exatamente com estes nomes:
   `id`, `area_degradada_ha`, `area_matricula_ha`, `area_car_ha`,
   `alerta_desmatamento`, `situacao_car`, `situacao_cadastral`.
   - Áreas em hectares, como número (`1200`, não `"1.200"`).
   - `alerta_desmatamento`: `null` (sem alerta), uma data ou uma lista de datas,
     em `DD/MM/AAAA` ou `AAAA-MM-DD`.
   - Se o usuário descreveu a proposta em texto, **não invente** campos que ele
     não informou: deixe o campo de fora. O script vai apontar o que falta (R6).
     Mostre ao usuário o JSON que você montou.

2. **Rode o script.** Se o usuário deu um arquivo, passe o caminho; se colou o
   conteúdo, envie pela entrada padrão:

   ```bash
   python3 ${CLAUDE_SKILL_DIR}/scripts/triagem.py proposta.json

   python3 ${CLAUDE_SKILL_DIR}/scripts/triagem.py - <<'EOF'
   {"id": "P-001", "area_degradada_ha": 850, ...}
   EOF
   ```

   No Windows, use `python` no lugar de `python3`. Se `${CLAUDE_SKILL_DIR}` não
   existir no seu ambiente, o script fica em `scripts/triagem.py`, nesta pasta.
   Para o resultado estruturado (integrações), acrescente `--formato json`.

3. **Apresente o card exatamente como o script devolveu**, sem reescrever
   motivos, sem mudar a ordem e sem tirar o rodapé com a versão das regras.
   Depois do card, você pode acrescentar no máximo uma ou duas frases
   explicando em linguagem simples o que o analista deve fazer agora.

4. **Se o script falhar** (código de saída 2), mostre a mensagem de erro, diga
   o que precisa ser corrigido na entrada e **não dê parecer nenhum**.

## O que nunca fazer

- Dar um parecer sem rodar o script, ou um parecer diferente do que ele deu.
- Converter "Pendente de regularização" em "Regular", arredondar áreas ou
  "corrigir" datas por conta própria. Valores estranhos são justamente o que a
  revisão humana precisa ver.
- Omitir motivos. A RECUSADA prevalece sobre a REVISÃO HUMANA, mas todos os
  motivos aparecem no card.

## Referência

- `REGRAS.md`: as regras R1–R6 em linguagem simples, com as premissas adotadas.
- `exemplos/`: as cinco propostas do enunciado (`P-001.json` a `P-005.json`) e
  todas juntas em `todas.json`.
