"""
conatusride — classificação dos pedais.

Grava a tabela `classificacao` e cria a view `vw_pedais`, que junta tudo de
`pedais` com os pontos de partida e chegada e os três campos de classificação.

Três dimensões independentes, cada uma medindo uma coisa só:

    porte   curto, medio, longo      — o tamanho
    piso    estrada, misto, trilha   — o terreno
    tipo    exploracao, rotina       — se teve cidade inédita

A versão anterior usava rotina, treino, evento e viagem num campo só, e elas se
sobrepunham: uma viagem pode conter um evento, e treino é uma rotina com outra
intenção. Separar em dimensões resolve isso.

Ordem: importar.py -> pontos_partida.py -> tracos.py -> metas.py ->
       classificar.py -> gerar_site.py

Uso:
    python src/classificar.py
"""

from pathlib import Path
import unicodedata

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "conatusride.duckdb"

# ---------------------------------------------------------------- regras
#
# tipo
#   exploracao   o pedal atravessou ao menos uma cidade onde eu nunca havia
#                pedalado antes daquela data
#   rotina       todas as cidades do percurso eu já conhecia
#
# A marca é do pedal, não da cidade. Em agosto de 2026 saí de Ipaumirim rumo a
# Triunfo: Ipaumirim e Baixio eu já conhecia, Triunfo e Umari não — então o
# pedal é exploração. O do dia seguinte, se ficar só em Ipaumirim e Baixio, é
# rotina. Voltar a um lugar não é explorar de novo.
#
# Passagem de raspão não conta. Em "Ceará - Paraíba" cruzei São João do Rio do
# Peixe em um minuto, na estrada entre Santa Helena e Bom Jesus — entrei no
# território, mas não conheci nada. Só conta como cidade explorada quando houve
# permanência: mais de MIN_PERMANENCIA minutos.
#
# Limitação conhecida: a malha do IBGE só tem municípios. Olho d'Água é distrito
# de Ipaumirim, então um pedal até lá aparece como se eu tivesse ficado em
# Ipaumirim. Exploração de distrito não é detectável com este dado.
#
# A primeira vez de Fortaleza, em junho de 2021, marca exploração. Tecnicamente
# é o esperado — é o marco inicial do histórico.
#
# porte — o tamanho, com o propósito de cada faixa:
#   curto   até 40 km — pedal rápido, treino, deslocamento
#   medio   41 a 75 km — pedal regular
#   longo   acima de 75 km — pedal de resistência
# Independe do tipo: Pindoretama e volta dá 100 km e é rotina de porte longo.
#
# piso — o terreno. Ver a seção de marcação abaixo.
#
# exploracao — o pedal atravessou ao menos uma cidade onde eu nunca tinha
# pedalado até aquela data. Não é sobre rota nova nem sobre distância, é sobre
# estar fora da rotina: uma trilha na região metropolitana conta.

# Minutos dentro de um município para contar como cidade explorada. Amostramos
# um ponto por minuto, então 5 pontos são 5 minutos. A 20 km/h isso é quase 2 km
# — atravessar a cidade, não raspar a borda. Com corte menor, uma cidade pequena
# cortada pela rodovia contaria como explorada mesmo passando direto.
MIN_PERMANENCIA = 5

KM_MEDIO = 40
KM_LONGO = 75


def chave(nome: str) -> str:
    """Minúsculo e sem acento, para comparar nome de cidade."""
    puro = unicodedata.normalize("NFKD", nome or "")
    return "".join(c for c in puro if not unicodedata.combining(c)).lower().strip()


# ---------------------------------------------------------------- piso
#
# O dado do Strava não serve para isto. A coluna `distancia_terra_m` marca 1%
# na Trilha Apuiarés, que foi quase toda em terra, e 0% no Posto Arizona, que é
# asfalto puro — as estradas dessas regiões não constam como não pavimentadas
# no mapa deles. Dois pedais do mesmo bloco de férias aparecem com 0% e 47%.
#
# Então a marcação é do ciclista, e vem pelo nome do pedal:
#
#   trilha   maior parte da rota fora do asfalto: terra, calçamento ou
#            singletrack. Pode atravessar cidade no caminho.
#   misto    alterna terra e asfalto, sem predominância clara.
#   estrada  predominância de asfalto ou rodovia. É o padrão — a esmagadora
#            maioria dos pedais.
#
# De 2026 em diante os nomes trazem "trilha" ou "misto" e a regra resolve
# sozinha. Para trás, os casos foram levantados um a um, ano a ano, e estão nas
# listas de exceção abaixo.

# "trilha" no nome descreve um trecho, não o pedal: 70 km de rotina de domingo
# com um pedaço curto de trilha no meio.
NAO_E_TRILHA = {"2022-09-18"}

# Trilha sem a palavra no nome.
E_TRILHA = {"2022-10-15"}  # Terra na veia

# Levantados ano a ano com o ciclista. 2021 ficou de fora (só pedais urbanos
# curtos) e 2023 não teve nenhum.
E_MISTO = {
    "2022-06-16",  # Feriado Corpus Christi
    "2022-09-18",  # Aventura: Cofeco, trilha do mangue, Mangabeira
    "2024-04-20",  # Cachoeiras do pinga
    "2024-10-02",  # Santa Helena
    "2024-10-03",  # Olho d'água
    "2024-09-20",  # Bom Jesus
    "2025-08-07",  # Baixio - São Vicente
    "2025-08-08",  # Bom Jesus
    "2025-08-10",  # Serrote / Trapiá
    "2025-08-11",  # Santa Helena PB
    "2025-08-12",  # Olho d'água
    "2025-08-18",  # Jurema - Baixio (via Br 116)
    "2025-08-19",  # Bom Jesus - PB / Serrote
    "2025-08-24",  # Santa Helena - Bom Jesus
    "2026-08-01",  # Ceará - Paraíba
    "2026-08-03",  # Bom Jesus - Br 116
    "2026-08-04",  # Jurema - Baixio
    "2026-08-06",  # Bom Jesus - Cachoeira dos Índios - Br116
    "2026-08-08",  # Triunfo Pb
}


def piso(nome: str, dia: str) -> str:
    texto = chave(nome)
    if dia in E_TRILHA:
        return "trilha"
    if "trilha" in texto and dia not in NAO_E_TRILHA:
        return "trilha"
    if "misto" in texto or dia in E_MISTO:
        return "misto"
    return "estrada"


def porte(km: float) -> str:
    if km >= KM_LONGO:
        return "longo"
    if km >= KM_MEDIO:
        return "medio"
    return "curto"


def classificar(pedais: pd.DataFrame, cidades: pd.DataFrame) -> pd.DataFrame:
    """Percorre os pedais em ordem cronológica marcando as estreias."""
    pedais = pedais.sort_values("data").reset_index(drop=True)

    # Cidades de cada pedal, na ordem de passagem, com quanto tempo em cada uma.
    por_arquivo = {}
    for arquivo, grupo in cidades.sort_values("entrada").groupby("arquivo"):
        por_arquivo[arquivo] = list(zip(grupo["cidade"], grupo["pontos"]))

    conhecidas = set()
    linhas = []

    for _, p in pedais.iterrows():
        visitadas = por_arquivo.get(p["arquivo"], [])

        # Só conta como estar na cidade quando houve permanência.
        com_parada = [
            (nome, chave(nome)) for nome, minutos in visitadas
            if minutos > MIN_PERMANENCIA
        ]

        novas = [nome for nome, k in com_parada if k not in conhecidas]
        conhecidas.update(k for _, k in com_parada)

        dia = pd.Timestamp(p["data"]).strftime("%Y-%m-%d")
        linhas.append({
            "id": p["id"],
            "tipo": "exploracao" if novas else "rotina",
            "porte": porte(p["distancia_km"]),
            "piso": piso(p["nome"], dia),
            "cidade_nova": ", ".join(novas) if novas else None,
        })

    return pd.DataFrame(linhas)


VIEW_CHEGADA = """
CREATE OR REPLACE VIEW vw_chegada AS
WITH ultimo AS (SELECT arquivo, max(ordem) AS fim FROM tracos GROUP BY 1)
SELECT t.arquivo, t.lat AS lat_fim, t.lon AS lon_fim,
       round(2 * 6371 * asin(sqrt(
           pow(sin(radians(t.lat - (-3.7319)) / 2), 2)
           + cos(radians(-3.7319)) * cos(radians(t.lat))
           * pow(sin(radians(t.lon - (-38.5267)) / 2), 2))), 1) AS km_fim_fortaleza
FROM tracos t JOIN ultimo u ON t.arquivo = u.arquivo AND t.ordem = u.fim
"""

VIEW_PEDAIS = """
CREATE OR REPLACE VIEW vw_pedais AS
SELECT p.*, t.lat, t.lon, t.km_de_fortaleza, f.km_fim_fortaleza,
       least(t.km_de_fortaleza, f.km_fim_fortaleza) AS km_de_casa,
       c.tipo, c.porte, c.piso, c.cidade_nova,
       hour(p.data) >= 19 AS noturno
FROM pedais p
LEFT JOIN pontos_partida t USING (arquivo)
LEFT JOIN vw_chegada f USING (arquivo)
LEFT JOIN classificacao c USING (id)
"""


def main() -> None:
    if not BANCO.exists():
        raise FileNotFoundError(f"Não encontrei {BANCO}. Rode src/importar.py.")

    with duckdb.connect(str(BANCO)) as con:
        tabelas = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
        for exigida, script in (("pontos_partida", "pontos_partida.py"),
                                ("tracos", "tracos.py"),
                                ("cidades", "tracos.py")):
            if exigida not in tabelas:
                raise RuntimeError(
                    f"Tabela {exigida} não existe. Rode src/{script} antes."
                )

        con.execute(VIEW_CHEGADA)

        pedais = con.execute("""
            SELECT p.id, p.arquivo, p.data, p.ano, p.nome, p.distancia_km,
                   least(t.km_de_fortaleza, f.km_fim_fortaleza) AS km_de_casa
            FROM pedais p
            LEFT JOIN pontos_partida t USING (arquivo)
            LEFT JOIN vw_chegada f USING (arquivo)
        """).df()
        cidades = con.execute(
            "SELECT arquivo, cidade, entrada, pontos FROM cidades"
        ).df()

        resultado = classificar(pedais, cidades)

        con.execute("DROP TABLE IF EXISTS classificacao")
        con.execute("CREATE TABLE classificacao AS SELECT * FROM resultado")
        con.execute(VIEW_PEDAIS)

        print("\nvw_pedais criada.\n")
        print(con.execute("""
            SELECT tipo, count(*) AS pedais,
                   round(avg(distancia_km), 1) AS km,
                   round(avg(velocidade_media_kmh), 1) AS kmh,
                   round(avg(ganho_elevacao_m / distancia_km), 1) AS m_por_km,
                   min(ano) AS de, max(ano) AS ate
            FROM vw_pedais GROUP BY 1 ORDER BY pedais DESC
        """).df().to_string(index=False))

        print()
        print(con.execute("""
            SELECT piso, count(*) AS pedais,
                   round(avg(distancia_km), 1) AS km,
                   round(avg(velocidade_media_kmh), 1) AS kmh,
                   round(avg(ganho_elevacao_m / distancia_km), 1) AS m_por_km
            FROM vw_pedais GROUP BY 1 ORDER BY pedais DESC
        """).df().to_string(index=False))

        print()
        print(con.execute("""
            SELECT ano,
                   sum((tipo = 'exploracao')::INT) AS exploracao,
                   sum((porte = 'curto')::INT)  AS curto,
                   sum((porte = 'medio')::INT)  AS medio,
                   sum((porte = 'longo')::INT)  AS longo,
                   sum((piso = 'misto')::INT)   AS misto,
                   sum((piso = 'trilha')::INT)  AS trilha
            FROM vw_pedais GROUP BY 1 ORDER BY ano
        """).df().to_string(index=False))


if __name__ == "__main__":
    main()
