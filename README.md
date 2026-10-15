# triagem-proposta

Skill do Claude que faz a **triagem de propostas** de recuperação de pastagem degradada
antes do comitê de crédito. Recebe a proposta em JSON, aplica as regras R1–R6 **em código**
e devolve o parecer — **SEGUE**, **RECUSADA** ou **REVISÃO HUMANA** — com todos os motivos,
as pendências e um card em Markdown pronto para virar tarefa.

> Teste prático AgDev · Josias Silva Siqueira · regras fictícias, versão 1.0.0

```text
proposta.json ──► Claude (skill) ──► scripts/triagem.py ──► parecer + motivos + pendências + card
                  monta a entrada     decide o parecer       apresentado sem alterações
```

O modelo nunca decide: ele prepara a entrada, chama o script e mostra o resultado.

## Rodar em 5 minutos

Requisito: **Python 3.10 ou mais novo**. Não há dependências para rodar a triagem.

```bash
git clone <url-do-repositório> triagem-proposta
cd triagem-proposta

# 1. Triagem dos 5 exemplos do enunciado
python3 .claude/skills/triagem-proposta/scripts/triagem.py .claude/skills/triagem-proposta/exemplos/todas.json

# 2. Testes automatizados (só os testes precisam do pytest; instale antes de rodar)
python3 -m pip install -r requirements-dev.txt   # instala o pytest
python3 -m pytest                                 # 117 testes, menos de 1 s
```

No Windows, troque `python3` por `python`.

### Usar como skill no Claude Code

A skill já está em `.claude/skills/`, então basta abrir o Claude Code **na pasta do repositório**:

```bash
claude
> faça a triagem da proposta .claude/skills/triagem-proposta/exemplos/P-004.json
```

Também dá para colar o JSON direto na conversa ou chamar `/triagem-proposta`.
Para usar em qualquer projeto, copie a pasta para a sua área pessoal:

```bash
cp -r .claude/skills/triagem-proposta ~/.claude/skills/
```

### Usar no Claude Desktop

Compacte a pasta `.claude/skills/triagem-proposta` em `.zip` (sem pastas `__pycache__`) e envie pela área de
Skills nas configurações do app (passo a passo na [central de ajuda](https://support.claude.com)).
A execução de código precisa estar habilitada.

### Linha de comando

A partir de `.claude/skills/triagem-proposta/`:

```bash
python3 scripts/triagem.py proposta.json                 # card em Markdown
python3 scripts/triagem.py proposta.json --formato json  # resultado estruturado
cat proposta.json | python3 scripts/triagem.py -         # lê da entrada padrão
python3 scripts/triagem.py --versao                      # versão das regras
```

O arquivo pode ter uma proposta ou uma lista. Saída `0` = triagem feita (qualquer parecer);
saída `2` = entrada inválida (arquivo inexistente ou fora de UTF-8, JSON malformado, lista vazia ou
item que não é objeto), com mensagem de erro e sem parecer.

## Resultado dos exemplos do enunciado

| ID | Parecer | Motivos |
|---|---|---|
| P-001 | 🟢 SEGUE | — (diferença de 10 ha, limite de 60 ha) |
| P-002 | 🔴 RECUSADA | R1: 60 ha, abaixo de 100 ha |
| P-003 | 🟡 REVISÃO HUMANA | R5: diferença de 100 ha = 11,11% da matrícula (limite 45 ha) |
| P-004 | 🔴 RECUSADA | R2: alerta em 15/03/2023 · R3: CAR "Pendente" |
| P-005 | 🟡 REVISÃO HUMANA | R4: "Pendente de regularização" · R6: falta `area_matricula_ha` (R5 não avaliada) |

Exemplo de card (P-004):

```markdown
## Triagem P-004 — RECUSADA

**Parecer:** 🔴 RECUSADA

**Motivos**

- **R2** (recusa): alerta de desmatamento em 15/03/2023, posterior a 01/01/2020.
- **R3** (revisão humana): situação do CAR "Pendente".

**Pendências**

- [ ] Comunicar a recusa ao proponente, citando os motivos acima.
- [ ] Se a proposta for reapresentada: verificar no SICAR o motivo da pendência do CAR e solicitar a regularização ao proponente.

---
_Triagem automática · regras v1.0.0 · não substitui a análise do comitê de crédito._
```

## Testes

117 testes em `tests/`, rodando no GitHub Actions a cada push (Python 3.10 a 3.13). Cobrem:

- os 5 exemplos do enunciado, com o resultado esperado definido por nós;
- cada regra com caso positivo, negativo e de borda: 100 ha exatos, diferença de **exatamente 5%**
  (e 5,001%), alerta no próprio dia do corte e no dia seguinte, lista de alertas, normalização de texto;
- campo ausente × campo nulo, valores inválidos, precedência RECUSADA > REVISÃO, acúmulo de motivos;
- uma armadilha de ponto flutuante real (102,1 ha × 107,205 ha), que daria falso positivo sem `Decimal`;
- a linha de comando: saída em Markdown e JSON, lote, entrada padrão, BOM do Windows e erros de entrada.

Os limites também foram conferidos por mutação: trocar `>` por `>=` em R1, R2 ou R5, voltar a data
de corte para 2021 ou calcular os 5% sobre o CAR faz a suíte falhar.

## Estrutura

```text
.claude/skills/triagem-proposta/
├── SKILL.md              # quando e como o Claude usa a skill
├── REGRAS.md             # regras em linguagem simples + premissas adotadas
├── scripts/
│   ├── regras.py         # motor R1–R6 (parâmetros no topo do arquivo)
│   ├── card.py           # card em Markdown
│   └── triagem.py        # linha de comando
└── exemplos/             # P-001 a P-005 e todas.json
tests/                    # pytest
DESIGN.md                 # decisões de desenho (1 página)
PERGUNTAS.md              # respostas às perguntas técnicas da seção 8
CHANGELOG.md              # histórico das versões das regras
```

## Documentos

- [DESIGN.md](DESIGN.md) — revisão humana, dados reais, mudança de regras, adoção pelos analistas e uso de IA.
- [REGRAS.md](.claude/skills/triagem-proposta/REGRAS.md) — as regras e todas as premissas para casos ambíguos.
- [PERGUNTAS.md](PERGUNTAS.md) — perguntas técnicas adicionais.
