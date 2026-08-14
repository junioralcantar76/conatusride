"""
conatusride — importação da exportação do Strava.

Lê data/raw/activities.csv, normaliza e carrega em data/conatusride.duckdb,
tabela `pedais`.

A tabela é recriada a cada execução: a fonte é um arquivo único e completo,
então recriar é mais simples e seguro do que mesclar registros.

Uso:
    python src/importar.py
"""

from pathlib import Path
import re

import duckdb
import pandas as pd

# ---------------------------------------------------------------- caminhos

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "data" / "raw" / "activities.csv"
BANCO = RAIZ / "data" / "conatusride.duckdb"

ANO_INICIAL = 2021

# ---------------------------------------------------------------- colunas
# origem -> destino. Sufixo indica a unidade.

COLUNAS = {
    # identificação
    "ID da atividade": "id",
    "Nome da atividade": "nome",
    "Nome do arquivo": "arquivo",
    "Bicicleta": "bicicleta_id",
    # tempo (segundos)
    "Tempo decorrido": "tempo_total_s",
    "Tempo de movimentação": "tempo_movimento_s",
    # distância (metros)
    "Distância.1": "distancia_m",
    "Distância na terra": "distancia_terra_m",
    # velocidade (m/s)
    "Velocidade média": "velocidade_media_ms",
    "Velocidade máx.": "velocidade_max_ms",
    "Velocidade média (tempo decorrido)": "velocidade_media_total_ms",
    # elevação (metros) e inclinação (%)
    "Ganho de elevação": "ganho_elevacao_m",
    "Perda de elevação": "perda_elevacao_m",
    "Elevação mínima": "elevacao_min_m",
    "Elevação máxima": "elevacao_max_m",
    "Inclinação média": "inclinacao_media_pct",
    "Inclinação máxima": "inclinacao_max_pct",
    # esforço
    "Média de watts": "watts_medio",  # estimativa do Strava, não medição
    "Calorias": "calorias",
    "Frequência cardíaca média": "fc_media",  # só 6 pedais com sensor
    "Frequência cardíaca máxima": "fc_max",
    # clima
    "Condição climática": "clima_condicao_cod",
    "Temperatura atmosférica": "temperatura_c",
    "Temperatura aparente": "temperatura_aparente_c",
    "Ponto de orvalho": "ponto_orvalho_c",
    "Umidade": "umidade",
    "Pressão atmosférica": "pressao_hpa",
    "Velocidade do vento": "vento_ms",
    "Rajada de vento": "rajada_ms",
    "Direção do vento": "vento_direcao_graus",
    "Intensidade da precipitação": "precipitacao_intensidade",
    "Probabilidade de precipitação": "precipitacao_probabilidade",
    "Tipo de precipitação": "precipitacao_tipo_cod",
    "Nebulosidade": "nebulosidade",
    "Visibilidade": "visibilidade_m",
    "Índice UV": "indice_uv",
    "Hora do nascer do sol": "nascer_sol_unix",
    "Hora do pôr do sol": "por_sol_unix",
    "Fase da lua": "fase_lua",
    # mídia
    "Mídia": "midia",
}

# Colunas onde o Strava grava 0 para "sem sensor". Viram nulo.
ZERO_E_NULO = ["fc_media", "fc_max"]

# ---------------------------------------------------------------- datas

MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

PADRAO_DATA = re.compile(
    r"(\d{1,2}) de (\w{3})\.? de (\d{4}),?\s+(\d{1,2}):(\d{2}):(\d{2})"
)


def converter_data(texto):
    """Converte '8 de ago. de 2026, 07:59:26' em Timestamp.

    O formato do Strava em português não é reconhecido pelo parser padrão
    do pandas, que erra em mais da metade dos registros.
    """
    if not isinstance(texto, str):
        return pd.NaT
    m = PADRAO_DATA.match(texto.strip())
    if not m:
        return pd.NaT
    dia, mes, ano, hora, minuto, segundo = m.groups()
    numero_mes = MESES.get(mes.lower()[:3])
    if numero_mes is None:
        return pd.NaT
    return pd.Timestamp(
        int(ano), numero_mes, int(dia), int(hora), int(minuto), int(segundo)
    )


# ---------------------------------------------------------------- etapas


def ler_csv(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Não encontrei {caminho}.\n"
            "Extraia a exportação do Strava dentro de data/raw/."
        )
    return pd.read_csv(caminho)


def normalizar(bruto: pd.DataFrame) -> pd.DataFrame:
    faltando = [c for c in COLUNAS if c not in bruto.columns]
    if faltando:
        raise ValueError(f"Colunas ausentes no CSV: {faltando}")

    df = bruto[list(COLUNAS)].rename(columns=COLUNAS).copy()

    df["data"] = bruto["Data da atividade"].map(converter_data)
    sem_data = df["data"].isna().sum()
    if sem_data:
        print(f"  aviso: {sem_data} registro(s) com data ilegível, descartados")
        df = df[df["data"].notna()]

    for coluna in ZERO_E_NULO:
        df.loc[df[coluna] == 0, coluna] = pd.NA

    # Derivadas de conveniência: km/h e km poupam conversão em toda consulta.
    df["distancia_km"] = df["distancia_m"] / 1000
    df["velocidade_media_kmh"] = df["velocidade_media_ms"] * 3.6
    df["velocidade_max_kmh"] = df["velocidade_max_ms"] * 3.6
    df["ano"] = df["data"].dt.year
    df["mes"] = df["data"].dt.to_period("M").astype(str)

    df["id"] = df["id"].astype("int64")
    df["bicicleta_id"] = df["bicicleta_id"].astype("Int64")

    ordem = ["id", "data", "ano", "mes", "nome"] + [
        c for c in df.columns if c not in ("id", "data", "ano", "mes", "nome")
    ]
    return df[ordem].sort_values("data").reset_index(drop=True)


def filtrar(df: pd.DataFrame) -> pd.DataFrame:
    """Recorte 2021 em diante.

    Há um registro isolado de 2018, com três anos de lacuna depois dele.
    Mantê-lo distorceria qualquer análise temporal.
    """
    antes = len(df)
    df = df[df["ano"] >= ANO_INICIAL]
    descartados = antes - len(df)
    if descartados:
        print(f"  {descartados} pedal(is) anterior(es) a {ANO_INICIAL} descartado(s)")
    return df.reset_index(drop=True)


def gravar(df: pd.DataFrame, banco: Path) -> None:
    banco.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(banco)) as con:
        con.execute("DROP TABLE IF EXISTS pedais")
        con.execute("CREATE TABLE pedais AS SELECT * FROM df")
        con.execute("CREATE UNIQUE INDEX idx_pedais_id ON pedais (id)")


def resumir(banco: Path) -> None:
    with duckdb.connect(str(banco)) as con:
        total, km, elev, inicio, fim = con.execute("""
            SELECT count(*),
                   round(sum(distancia_km)),
                   round(sum(ganho_elevacao_m)),
                   min(data)::DATE,
                   max(data)::DATE
            FROM pedais
        """).fetchone()
    print(f"\n{total} pedais | {km:,.0f} km | {elev:,.0f} m de elevação")
    print(f"de {inicio} a {fim}")


def main() -> None:
    print("Lendo CSV...")
    bruto = ler_csv(CSV)
    print(f"  {len(bruto)} linhas, {len(bruto.columns)} colunas")

    print("Normalizando...")
    df = normalizar(bruto)

    print("Filtrando...")
    df = filtrar(df)

    print(f"Gravando em {BANCO.name}...")
    gravar(df, BANCO)

    resumir(BANCO)


if __name__ == "__main__":
    main()
