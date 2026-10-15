# DESIGN

**Princípio:** o código decide, o modelo conversa e a pessoa julga o que é ambíguo. As regras ficam
em `regras.py`, testadas; o Claude só monta a entrada, roda o script e mostra o card. O mesmo JSON
dá sempre o mesmo parecer, e cada parecer cita a versão das regras usada.

## 1. Onde entra a revisão humana, e por quê

A máquina só **recusa** sozinha diante de fato objetivo (área abaixo do mínimo, alerta após o corte,
CAR cancelado ou suspenso) e só deixa **seguir** quando todas as regras rodaram e passaram. Todo o
resto vai para uma pessoa: CAR pendente, CPF/CNPJ fora de "Regular", divergência de área acima de 5%,
campo ausente, valor inválido ou desconhecido. **Na dúvida, nunca SEGUE.** Regra que não rodou por
falta de dado ou valor inválido aparece no card, para ninguém confundir "passou" com "não foi verificado".

## 2. Dados reais (SICAR, PRODES, Receita Federal)

Um módulo de **coleta**, separado das regras, preencheria o mesmo JSON; o motor não muda.

- **SICAR:** situação e área do CAR. *Riscos:* dado desatualizado, mais de um CAR por imóvel,
  sobreposição, e a dúvida entre área total e líquida.
- **Desmatamento:** PRODES é anual; para alertas datados, DETER ou MapBiomas Alerta, cruzados com o
  perímetro do CAR. *Riscos:* data de detecção ≠ data do desmatamento, falso positivo de borda.
- **Receita Federal:** API oficial paga, com limite de chamadas e LGPD. CPF e CNPJ têm status
  diferentes: eu incluiria `tipo_documento` e trataria CNPJ "Ativa" como "Regular"; "Suspensa" e
  "Inapta" iriam para revisão; "Baixada" e "Nula" só virariam recusa por decisão do comitê.
- **Sempre:** fonte fora do ar ou resposta ambígua vira REVISÃO HUMANA. Cada consulta guarda data,
  fonte e resposta bruta, para auditar o parecer depois.

## 3. Quando o comitê muda uma regra

Aconteceu no próprio teste: a data de corte da R2 passou de 2021 para 2020.

1. **Pull request** alterando só os parâmetros no topo de `regras.py`, com os testes do novo
   comportamento (ex.: "alerta em 15/06/2020 agora recusa").
2. O CI roda a suíte; um segundo revisor aprova; quem pediu a mudança confere o `REGRAS.md`.
3. Sobe `VERSAO_REGRAS` (maior se um caso antigo muda de parecer), registra no `CHANGELOG.md`, cria a tag.
4. O time recebe por `git pull` (skill de projeto) ou por um marketplace interno de plugins. Como
   todo card mostra a versão, sabe-se qual regra valeu para cada proposta.

## 4. Como um analista não técnico passa a usar e a confiar

- **Uso:** anexa ou cola a proposta e pede "faça a triagem". Sem terminal.
- **Transparência:** cada motivo traz os números ("diferença de 100 ha = 11,11%, limite 45 ha"),
  conferíveis na calculadora, e o `REGRAS.md` explica tudo sem código.
- **Implantação gradual:** algumas semanas em paralelo, skill e analista triando as mesmas propostas;
  cada divergência é discutida e vira teste. Discordou depois? Vira exemplo ou nova versão da regra.

## 5. Como usei IA

## 5. Como usei IA

Utilizei o Claude como apoio durante todo o desenvolvimento, desde a análise do enunciado até a implementação, os testes e a documentação. É uma abordagem que já utilizo no dia a dia, principalmente em projetos que envolvem integrações, automações e IA.

Comecei utilizando o Claude para questionar as regras do enunciado e identificar situações que não estavam claras. Foi dessa análise que surgiram as perguntas encaminhadas à AgDev. Preferi esclarecer essas questões antes de implementar algo baseado em suposições.

Na implementação, usei o Claude para gerar a estrutura inicial, o código e os testes. A partir daí, fui revisando as regras individualmente, ajustando a lógica e conferindo se os resultados faziam sentido. Não tratei o código gerado como algo pronto.

Um caso interessante foi a **regra R5**, em que identificamos um possível problema de precisão com números de ponto flutuante. Explorei esse cenário com o Claude, revisei o cálculo e validei o comportamento esperado.

Também fiz testes por mutação, alterando propositalmente limites e condições das regras para verificar se os testes realmente identificavam os erros. Acho esse ponto importante porque ter uma suíte passando não significa necessariamente que ela esteja testando corretamente o negócio.

Usei a IA também para estruturar a documentação, mas conferi se tudo correspondia ao que foi implementado.

No geral, **o Claude acelerou bastante o trabalho, principalmente na geração de código e na exploração de cenários que poderiam passar despercebidos**. Mas a interpretação das regras, as decisões técnicas e a validação final ficaram comigo. É assim que costumo trabalhar com IA: aproveitando a velocidade da ferramenta, sem abrir mão de entender e validar o que estou entregando.
