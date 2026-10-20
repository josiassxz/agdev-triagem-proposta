"""Motor de regras da triagem de propostas (R1 a R6).

Todo o julgamento acontece aqui, em código determinístico. O modelo (Claude)
só chama este código e apresenta o resultado; ele nunca decide o parecer.

Para mudar uma regra, altere apenas a seção PARÂMETROS abaixo, ajuste os
testes e registre a mudança no CHANGELOG.md (ver DESIGN.md).
"""

from __future__ import annotations  # permite usar "str | None" nas anotações no Python 3.10

from dataclasses import dataclass, field  # classes de dados (Ocorrencia, Resultado)
from datetime import date, datetime       # datas dos alertas de desmatamento (R2)
from decimal import Decimal               # contas de área exatas, sem erro de ponto flutuante
from enum import Enum                     # os três pareceres possíveis
from typing import Any

# ---------------------------------------------------------------------------
# PARÂMETROS DAS REGRAS (único lugar a editar quando o comitê mudar algo)
# ---------------------------------------------------------------------------
VERSAO_REGRAS = "2.0.0"

AREA_MINIMA_HA = Decimal("150")                # R1: mínimo inclusivo
DATA_CORTE_ALERTA = date(2020, 1, 1)           # R2: alerta *depois* desta data recusa
TOLERANCIA_DIVERGENCIA_AREA = Decimal("0.05")  # R5: 5% da área da matrícula

CAR_SEGUE = frozenset({"ativo"})                     # R3
CAR_REVISAO = frozenset({"pendente"})                # R3
CAR_RECUSA = frozenset({"cancelado", "suspenso"})    # R3
SITUACAO_CADASTRAL_SEGUE = frozenset({"regular"})    # R4

CAMPOS_OBRIGATORIOS = (                        # R6
    "id",
    "area_degradada_ha",
    "area_matricula_ha",
    "area_car_ha",
    "alerta_desmatamento",
    "situacao_car",
    "situacao_cadastral",
)
# Campos em que `null` é um valor válido (e não "ausente").
CAMPOS_ACEITAM_NULO = frozenset({"alerta_desmatamento"})

FORMATOS_DATA = ("%d/%m/%Y", "%Y-%m-%d")      # R2: DD/MM/AAAA ou AAAA-MM-DD


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------
class Parecer(str, Enum):
    """Os três resultados possíveis da triagem. O valor é o texto mostrado no card."""

    SEGUE = "SEGUE"
    REVISAO_HUMANA = "REVISÃO HUMANA"
    RECUSADA = "RECUSADA"


# Ordem de precedência: o pior efeito encontrado define o parecer.
_GRAVIDADE = {Parecer.SEGUE: 0, Parecer.REVISAO_HUMANA: 1, Parecer.RECUSADA: 2}


@dataclass(frozen=True)
class Ocorrencia:
    """Uma regra que falhou: o motivo (o que aconteceu) e a pendência (o que fazer)."""

    regra: str        # "R1" a "R6"
    efeito: Parecer   # REVISAO_HUMANA ou RECUSADA (uma regra que passa não gera ocorrência)
    motivo: str       # explicação com os números que levaram à falha
    pendencia: str    # ação concreta para o analista resolver

    def to_dict(self) -> dict[str, str]:
        """Versão em dicionário, usada na saída --formato json."""
        return {
            "regra": self.regra,
            "efeito": self.efeito.value,
            "motivo": self.motivo,
            "pendencia": self.pendencia,
        }


@dataclass
class Resultado:
    """Tudo o que a triagem de uma proposta produz. É o que card.py transforma em Markdown."""

    id: str | None                    # id da proposta (None se veio ausente ou vazio)
    parecer: Parecer                  # parecer final (o efeito mais grave encontrado)
    ocorrencias: list[Ocorrencia]     # todas as regras que falharam, em ordem R1..R6
    pendencias: list[str]             # lista de ações, já montada para o card
    nao_avaliadas: list[str] = field(default_factory=list)  # regras puladas por falta de dado
    versao_regras: str = VERSAO_REGRAS  # vai no rodapé do card, para auditoria

    @property
    def motivos(self) -> list[str]:
        """Motivos em texto simples: ["R1: área degradada de ...", ...]."""
        return [f"{o.regra}: {o.motivo}" for o in self.ocorrencias]

    def to_dict(self) -> dict[str, Any]:
        """Versão em dicionário, usada na saída --formato json."""
        return {
            "id": self.id,
            "parecer": self.parecer.value,
            "motivos": [o.to_dict() for o in self.ocorrencias],
            "pendencias": list(self.pendencias),
            "regras_nao_avaliadas": list(self.nao_avaliadas),
            "versao_regras": self.versao_regras,
        }


# ---------------------------------------------------------------------------
# Normalização e validação de valores
# ---------------------------------------------------------------------------
def _normalizar_texto(valor: str) -> str:
    """'  ATIVO ' -> 'ativo'; colapsa espaços internos."""
    return " ".join(valor.split()).casefold()


def _area(valor: Any) -> Decimal | None:
    """Área válida = número (int/float) finito e maior que zero. Texto não é aceito."""
    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        return None
    numero = Decimal(str(valor))  # str() evita o erro binário do float (0.1 -> 0.1)
    if not numero.is_finite() or numero <= 0:
        return None
    return numero


def _data(valor: Any) -> date | None:
    """Converte texto em data, tentando cada formato aceito. Devolve None se não for legível."""
    if not isinstance(valor, str):
        return None
    texto = valor.strip()
    for formato in FORMATOS_DATA:
        try:
            return datetime.strptime(texto, formato).date()
        except ValueError:
            continue
    return None


def _fmt_ha(valor: Decimal) -> str:
    """Decimal('1200') -> '1.200 ha'; Decimal('16.665') -> '16,665 ha'."""
    texto = format(valor.normalize(), "f")
    inteiro, _, fracao = texto.partition(".")
    inteiro = f"{int(inteiro):,}".replace(",", ".")
    return f"{inteiro},{fracao} ha" if fracao else f"{inteiro} ha"


def _fmt_data(valor: date) -> str:
    """date(2023, 3, 15) -> '15/03/2023'."""
    return valor.strftime("%d/%m/%Y")


def _campo_ausente(proposta: dict[str, Any], campo: str) -> bool:
    """Ausente = chave que não existe, null (exceto em alerta_desmatamento) ou texto vazio."""
    if campo not in proposta:
        return True
    valor = proposta[campo]
    if valor is None:
        return campo not in CAMPOS_ACEITAM_NULO
    if isinstance(valor, str) and not valor.strip():
        return True
    return False


# ---------------------------------------------------------------------------
# Regras
# ---------------------------------------------------------------------------
# Cada regra recebe a proposta e devolve uma lista de ocorrências:
# lista vazia = a regra passou.

def _r1_area_minima(p: dict[str, Any]) -> list[Ocorrencia]:
    """R1: área degradada abaixo de 150 ha recusa. Valor inválido vai para revisão."""
    area = _area(p["area_degradada_ha"])
    if area is None:
        return [Ocorrencia(
            "R1", Parecer.REVISAO_HUMANA,
            f"valor inválido para area_degradada_ha ({p['area_degradada_ha']!r}); "
            "a regra não pôde ser avaliada.",
            "Corrigir a área de pastagem degradada (número em hectares, maior que zero).",
        )]
    if area < AREA_MINIMA_HA:
        return [Ocorrencia(
            "R1", Parecer.RECUSADA,
            f"área degradada de {_fmt_ha(area)}, abaixo do mínimo de {_fmt_ha(AREA_MINIMA_HA)}.",
            "Nenhuma ação de saneamento: a área não atende ao mínimo do programa.",
        )]
    return []


def _r2_alerta_desmatamento(p: dict[str, Any]) -> list[Ocorrencia]:
    """R2: alerta de desmatamento depois de 01/01/2020 recusa.

    Aceita null (sem alerta), uma data ou uma lista de datas.
    """
    # 1. Transforma qualquer formato aceito em uma lista de alertas.
    bruto = p["alerta_desmatamento"]
    if bruto is None:
        alertas: list[Any] = []
    elif isinstance(bruto, str):
        alertas = [bruto]
    elif isinstance(bruto, list):
        alertas = bruto
    else:
        return [Ocorrencia(
            "R2", Parecer.REVISAO_HUMANA,
            f"formato inválido para alerta_desmatamento ({bruto!r}); "
            "esperado nulo, uma data ou uma lista de datas.",
            "Conferir os alertas de desmatamento do imóvel na fonte oficial.",
        )]

    # 2. Separa os alertas posteriores ao corte e as datas ilegíveis.
    #    Alertas até a data de corte (inclusive) são ignorados.
    posteriores: list[date] = []
    invalidos: list[Any] = []
    for alerta in alertas:
        data_alerta = _data(alerta)
        if data_alerta is None:
            invalidos.append(alerta)
        elif data_alerta > DATA_CORTE_ALERTA:
            posteriores.append(data_alerta)

    # 3. Gera as ocorrências. As duas podem sair juntas: uma data ilegível
    #    não esconde um alerta válido.
    ocorrencias: list[Ocorrencia] = []
    if posteriores:
        unicas = sorted(set(posteriores))  # remove datas repetidas e ordena
        datas = ", ".join(_fmt_data(d) for d in unicas)
        plural = "s" if len(unicas) > 1 else ""
        ocorrencias.append(Ocorrencia(
            "R2", Parecer.RECUSADA,
            f"alerta{plural} de desmatamento em {datas}, posterior{'es' if plural else ''} "
            f"a {_fmt_data(DATA_CORTE_ALERTA)}.",
            "Nenhuma ação de saneamento: há desmatamento após a data de corte.",
        ))
    if invalidos:
        valores = ", ".join(repr(v) for v in invalidos)
        ocorrencias.append(Ocorrencia(
            "R2", Parecer.REVISAO_HUMANA,
            f"data de alerta ilegível ({valores}); formatos aceitos: DD/MM/AAAA ou AAAA-MM-DD.",
            "Conferir a data do(s) alerta(s) de desmatamento na fonte oficial.",
        ))
    return ocorrencias


def _r3_situacao_car(p: dict[str, Any]) -> list[Ocorrencia]:
    """R3: Ativo passa; Pendente vai para revisão; Cancelado/Suspenso recusa; outro valor, revisão."""
    bruto = p["situacao_car"]
    valor = _normalizar_texto(bruto) if isinstance(bruto, str) else None
    if valor in CAR_SEGUE:
        return []
    if valor in CAR_RECUSA:
        return [Ocorrencia(
            "R3", Parecer.RECUSADA,
            f"situação do CAR \"{bruto.strip()}\".",
            "Nenhuma ação de saneamento: CAR cancelado ou suspenso.",
        )]
    if valor in CAR_REVISAO:
        return [Ocorrencia(
            "R3", Parecer.REVISAO_HUMANA,
            f"situação do CAR \"{bruto.strip()}\".",
            "Verificar no SICAR o motivo da pendência do CAR e solicitar a regularização ao proponente.",
        )]
    return [Ocorrencia(
        "R3", Parecer.REVISAO_HUMANA,
        f"situação do CAR não reconhecida: {bruto!r} "
        "(esperado Ativo, Pendente, Cancelado ou Suspenso).",
        "Confirmar a situação do CAR diretamente no SICAR.",
    )]


def _r4_situacao_cadastral(p: dict[str, Any]) -> list[Ocorrencia]:
    """R4: só CPF/CNPJ "Regular" passa; qualquer outra situação vai para revisão."""
    bruto = p["situacao_cadastral"]
    valor = _normalizar_texto(bruto) if isinstance(bruto, str) else None
    if valor in SITUACAO_CADASTRAL_SEGUE:
        return []
    descricao = f"\"{bruto.strip()}\"" if isinstance(bruto, str) else repr(bruto)
    return [Ocorrencia(
        "R4", Parecer.REVISAO_HUMANA,
        f"situação cadastral {descricao} (somente \"Regular\" segue).",
        "Consultar a situação do CPF/CNPJ na Receita Federal e pedir a regularização ao proponente.",
    )]


def _r5_divergencia_area(p: dict[str, Any]) -> list[Ocorrencia]:
    """R5: diferença entre matrícula e CAR acima de 5% da matrícula vai para revisão."""
    matricula = _area(p["area_matricula_ha"])
    car = _area(p["area_car_ha"])
    # Se alguma das áreas for inválida, não dá para comparar: aponta qual e para.
    ocorrencias: list[Ocorrencia] = []
    for campo, valor in (("area_matricula_ha", matricula), ("area_car_ha", car)):
        if valor is None:
            ocorrencias.append(Ocorrencia(
                "R5", Parecer.REVISAO_HUMANA,
                f"valor inválido para {campo} ({p[campo]!r}); a regra não pôde ser avaliada.",
                f"Corrigir {campo} (número em hectares, maior que zero).",
            ))
    if ocorrencias:
        return ocorrencias

    diferenca = abs(matricula - car)                  # tanto faz qual é maior
    limite = matricula * TOLERANCIA_DIVERGENCIA_AREA  # 5% calculado sobre a matrícula
    if diferenca > limite:  # exatamente no limite NÃO aciona ("maior que")
        percentual = _percentual_acima_do_limite(diferenca, matricula)
        return [Ocorrencia(
            "R5", Parecer.REVISAO_HUMANA,
            f"diferença de {_fmt_ha(diferenca)} entre matrícula ({_fmt_ha(matricula)}) e CAR "
            f"({_fmt_ha(car)}) = {str(percentual).replace('.', ',')}% da matrícula, "
            f"acima do limite de {_fmt_ha(limite)} "
            f"({TOLERANCIA_DIVERGENCIA_AREA * 100:.0f}%).",
            "Conferir a matrícula e o perímetro do CAR e pedir retificação de um dos dois.",
        )]
    return []


def _percentual_acima_do_limite(diferenca: Decimal, base: Decimal) -> Decimal:
    """Percentual com casas suficientes para não exibir '5,00%' quando passou do limite."""
    bruto = diferenca / base * 100
    limite = TOLERANCIA_DIVERGENCIA_AREA * 100
    for casas in ("0.01", "0.0001", "0.000001"):
        arredondado = bruto.quantize(Decimal(casas))
        if arredondado > limite:
            return arredondado
    return arredondado


# Cada regra declara de quais campos depende; se faltar algum, ela não roda.
_REGRAS = (
    ("R1", ("area_degradada_ha",), _r1_area_minima),
    ("R2", ("alerta_desmatamento",), _r2_alerta_desmatamento),
    ("R3", ("situacao_car",), _r3_situacao_car),
    ("R4", ("situacao_cadastral",), _r4_situacao_cadastral),
    ("R5", ("area_matricula_ha", "area_car_ha"), _r5_divergencia_area),
)

# Textos usados nas pendências de uma proposta RECUSADA (ver _pendencias).
PENDENCIA_RECUSA = "Comunicar a recusa ao proponente, citando os motivos acima."
PREFIXO_PENDENCIA_EM_RECUSA = "Se a proposta for reapresentada: "


# ---------------------------------------------------------------------------
# Ponto de entrada
# ---------------------------------------------------------------------------
def avaliar(proposta: dict[str, Any]) -> Resultado:
    """Aplica R1–R6 e devolve o parecer com TODOS os motivos (não para na primeira falha)."""
    if not isinstance(proposta, dict):
        raise TypeError("a proposta deve ser um objeto JSON (dicionário)")

    # 1. R6: uma ocorrência de revisão para cada campo obrigatório ausente.
    ausentes = [c for c in CAMPOS_OBRIGATORIOS if _campo_ausente(proposta, c)]
    ocorrencias: list[Ocorrencia] = [
        Ocorrencia(
            "R6", Parecer.REVISAO_HUMANA,
            f"campo obrigatório ausente: {campo}.",
            f"Obter o dado \"{campo}\" com o proponente ou na fonte oficial.",
        )
        for campo in ausentes
    ]

    # 2. R1 a R5: roda todas as regras, sem parar na primeira falha. A regra
    #    que depende de um campo ausente é pulada e listada como "não avaliada".
    nao_avaliadas: list[str] = []
    for regra, dependencias, funcao in _REGRAS:
        faltando = [c for c in dependencias if c in ausentes]
        if faltando:
            nao_avaliadas.append(f"{regra} (falta {', '.join(faltando)})")
            continue
        ocorrencias.extend(funcao(proposta))

    ocorrencias.sort(key=lambda o: o.regra)  # ordem estável R1..R6

    # 3. O parecer é o efeito mais grave: RECUSADA > REVISÃO HUMANA > SEGUE.
    #    Sem nenhuma ocorrência, a proposta SEGUE.
    parecer = max(
        (o.efeito for o in ocorrencias), key=_GRAVIDADE.__getitem__, default=Parecer.SEGUE
    )

    # 4. Lista de ações para o analista.
    pendencias = _pendencias(parecer, ocorrencias)

    # 5. Normaliza o id: número vira texto; ausente ou vazio vira None.
    id_bruto = proposta.get("id")
    if isinstance(id_bruto, (int, float)) and not isinstance(id_bruto, bool):
        id_bruto = str(id_bruto)
    id_proposta = id_bruto.strip() if isinstance(id_bruto, str) and id_bruto.strip() else None
    return Resultado(id_proposta, parecer, ocorrencias, pendencias, nao_avaliadas)


def _pendencias(parecer: Parecer, ocorrencias: list[Ocorrencia]) -> list[str]:
    """Pendências = ações concretas. SEGUE não tem pendências.

    Em RECUSADA, a ação principal é comunicar a recusa; os itens de revisão
    continuam listados (marcados) para o caso de a proposta ser reapresentada.
    """
    if parecer is Parecer.SEGUE:
        return []
    revisao = _sem_repeticao(
        o.pendencia for o in ocorrencias if o.efeito is Parecer.REVISAO_HUMANA
    )
    if parecer is Parecer.RECUSADA:
        return [PENDENCIA_RECUSA] + [
            PREFIXO_PENDENCIA_EM_RECUSA + p[0].lower() + p[1:] for p in revisao
        ]
    return revisao


def _sem_repeticao(itens) -> list[str]:
    """Remove itens repetidos mantendo a ordem original (o dict preserva a ordem de inserção)."""
    vistos: dict[str, None] = {}
    for item in itens:
        vistos.setdefault(item, None)
    return list(vistos)
