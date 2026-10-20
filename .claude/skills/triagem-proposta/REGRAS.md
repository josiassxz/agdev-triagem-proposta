# Regras da triagem — versão 2.0.0

> Regras fictícias do teste prático da AgDev. Não representam a política de crédito.

## Como o parecer é decidido

Todas as regras são verificadas, sempre. Depois, vale o resultado mais grave:

1. Se **alguma** regra recusa → **RECUSADA**
2. Senão, se **alguma** regra pede revisão → **REVISÃO HUMANA**
3. Senão → **SEGUE**

Todos os motivos aparecem no card, inclusive os que não decidiram o parecer.

## As regras

| Regra | O que é verificado | Resultado se não passar |
|---|---|---|
| **R1** | Área de pastagem degradada de **pelo menos** 150 ha (150 ha exatos passa) | RECUSADA |
| **R2** | Nenhum alerta de desmatamento **depois de** 01/01/2020 (um alerta no próprio dia 01/01/2020 não recusa) | RECUSADA |
| **R3** | Situação do CAR "Ativo" | "Pendente" → REVISÃO HUMANA · "Cancelado" ou "Suspenso" → RECUSADA · outro valor → REVISÃO HUMANA |
| **R4** | Situação cadastral do CPF/CNPJ "Regular" | REVISÃO HUMANA |
| **R5** | Diferença entre a área da matrícula e a do CAR **até** 5% da área da matrícula (5% exatos passa) | REVISÃO HUMANA |
| **R6** | Os 7 campos obrigatórios estão presentes | REVISÃO HUMANA, dizendo qual campo falta |

## Motivos e pendências

- **Motivo** é a regra que falhou, com os números que levaram a isso.
- **Pendência** é a ação concreta para resolver. Proposta que **segue** não tem pendências.
- Na **recusa**, a primeira pendência é comunicar a recusa ao proponente. Os itens de
  revisão humana continuam listados, marcados "Se a proposta for reapresentada".

## Premissas adotadas

Pontos confirmados pela AgDev no e-mail de 13/10/2026:

| Situação | Tratamento |
|---|---|
| Data de corte da R2 | 01/01/2020 (o enunciado dizia 2021). O próprio dia não recusa. |
| Vários alertas | Aceita `null`, uma data ou uma lista. Basta um alerta posterior ao corte para recusar. Lista vazia = sem alerta. |
| Maiúsculas e espaços | Ignorados: `" ATIVO "` vale como "Ativo". |
| Situação do CAR fora da lista | REVISÃO HUMANA, citando o valor recebido. |
| Campos obrigatórios | Os 7 do formato sugerido. |
| `alerta_desmatamento: null` | Significa "sem alerta" (válido). Já o campo **ausente** cai na R6. |

Decisões tomadas por nós, enquanto aguardamos confirmação (todas conservadoras:
na dúvida, a proposta vai para uma pessoa, nunca segue sozinha):

| Situação | Tratamento | Por quê |
|---|---|---|
| Outros campos com `null` ou texto vazio | Contam como ausentes (R6) | Um dado vazio não pode ser verificado. |
| Formato da data | Aceita `DD/MM/AAAA` e `AAAA-MM-DD`; data ilegível ou com hora (`2023-03-15T10:00`) → REVISÃO HUMANA | A tabela usa um formato e sistemas costumam usar o outro; aceitar hora fica para a integração real. |
| Área zero, negativa, texto (`"1.200"`) ou não numérica | REVISÃO HUMANA ("valor inválido") | `"1.200"` pode ser 1,2 ou 1.200 ha: adivinhar é pior que perguntar. |
| Campo ausente de que uma regra depende | A regra fica "não avaliada" e aparece em seção própria do card; com valor inválido, ela aparece como motivo dizendo que não pôde ser avaliada | Sem a área degradada, não dá para recusar por R1; quem decide é a pessoa. |
| Data de alerta ilegível junto com uma válida posterior ao corte | RECUSADA (pela válida), e a ilegível também é listada | Uma data ruim não pode esconder um alerta real. |
| Comparações de área | Feitas em decimal exato, não em ponto flutuante | Evita que 5% exatos virem "5,0000001%" e acionem a R5 por erro de arredondamento. |
| Campos extras no JSON | Ignorados | Não atrapalham a triagem. |
| `id` numérico (`7`) | Aceito e mostrado como texto | Não há motivo para barrar. |
