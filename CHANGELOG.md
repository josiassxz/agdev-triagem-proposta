# Changelog das regras

O formato segue o [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/) e as versões seguem o
[versionamento semântico](https://semver.org/lang/pt-BR/), aplicado às regras:

- **maior** (2.0.0): algum caso já existente muda de parecer;
- **menor** (1.1.0): nova regra ou novo valor aceito, sem mudar pareceres antigos;
- **correção** (1.0.1): texto de motivo, pendência ou correção de erro sem mudar a regra.

A versão vale para `VERSAO_REGRAS` em `regras.py` e aparece no rodapé de todo card.

## [1.0.0] — 2026-10-14

### Adicionado
- Regras R1 a R6 e precedência RECUSADA > REVISÃO HUMANA > SEGUE, com todos os motivos listados.
- Card em Markdown com título, parecer, motivos, pendências e regras não avaliadas.
- Saída em JSON para integrações.

### Definido no esclarecimento da AgDev (e-mail de 13/10/2026)
- R2: data de corte em **01/01/2020** (o enunciado original dizia 01/01/2021); o próprio dia não recusa.
- R2: `alerta_desmatamento` aceita nulo, uma data ou uma lista.
- R3: normalização de maiúsculas e espaços; valor fora da lista → REVISÃO HUMANA citando o valor.
- R6: os 7 campos do formato sugerido são obrigatórios; `alerta_desmatamento: null` é válido.
