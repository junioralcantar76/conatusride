"""
conatusride — traçados amostrados e cidades atravessadas.

Lê os arquivos em data/raw/activities/, amostra um ponto por minuto de cada
traçado e cruza esses pontos com a malha municipal do IBGE.

Grava duas tabelas:

    tracos      um ponto por minuto de cada pedal (lat, lon, ordem)
    cidades     uma linha por pedal e cidade atravessada

O ponto de partida (pontos_partida.py) diz de onde saí. Isto diz por onde passei
— num pedal de 80 km atravesso vários municípios, e só o primeiro apareceria na
outra tabela.

Um ponto por minuto é suficiente: a 20 km/h isso são 333 metros, e nenhum
município é atravessado em menos que isso. Reduz de ~3 milhões de pontos para
~100 mil sem perder cidade nenhuma.

A malha do IBGE é baixada pela biblioteca geobr na primeira execução e fica em
cache. Só essa etapa precisa de internet.

Uso:
    python src/tracos.py
"""

from pathlib import Path
from xml.etree import ElementTree
import gzip
import io

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
ATIVIDADES = RAIZ / "data" / "raw" / "activities"
BANCO = RAIZ / "data" / "conatusride.duckdb"

INTERVALO_S = 60
SEMICIRCULO = 180 / 2**31


def valida(lat, lon) -> bool:
    """Rejeita coordenada ausente ou zerada (ver decisão 13)."""
    if lat is None or lon is None:
        return False
    return not (abs(lat) < 1 and abs(lon) < 1)


def abrir(caminho: Path) -> bytes:
    if caminho.suffix == ".gz":
        with gzip.open(caminho, "rb") as f:
            return f.read()
    return caminho.read_bytes()


def pontos_fit(dados: bytes):
    from fitparse import FitFile

    fit = FitFile(io.BytesIO(dados))
    saida = []
    ultimo = None

    for registro in fit.get_messages("record"):
        v = registro.get_values()
        lat, lon, ts = (
            v.get("position_lat"),
            v.get("position_long"),
            v.get("timestamp"),
        )
        if not valida(lat, lon) or ts is None:
            continue
        if ultimo is None or (ts - ultimo).total_seconds() >= INTERVALO_S:
            saida.append((lat * SEMICIRCULO, lon * SEMICIRCULO))
            ultimo = ts

    return saida


def pontos_xml(dados: bytes):
    """GPX e TCX.

    Nem todo arquivo tem tempo em cada ponto, e a taxa de gravação varia. Em vez
    de depender do timestamp, amostra um ponto a cada N — com gravação típica de
    1 Hz, um a cada 60 equivale a um por minuto.
    """
    raiz = ElementTree.fromstring(dados)
    todos = []

    for elemento in raiz.iter():
        tag = elemento.tag.rsplit("}", 1)[-1]

        if tag in ("trkpt", "wpt", "rtept"):
            lat, lon = elemento.get("lat"), elemento.get("lon")
            if lat and lon and valida(float(lat), float(lon)):
                todos.append((float(lat), float(lon)))

        elif tag == "Position":
            lat = lon = None
            for filho in elemento:
                nome = filho.tag.rsplit("}", 1)[-1]
                if nome == "LatitudeDegrees":
                    lat = float(filho.text)
                elif nome == "LongitudeDegrees":
                    lon = float(filho.text)
            if valida(lat, lon):
                todos.append((lat, lon))

    return todos[::INTERVALO_S] or todos[:1]


def extrair(caminho: Path):
    nome = caminho.name.lower()
    dados = abrir(caminho)
    if ".fit" in nome:
        return pontos_fit(dados)
    if ".gpx" in nome or ".tcx" in nome:
        return pontos_xml(dados)
    return []


def coletar_tracos() -> pd.DataFrame:
    arquivos = sorted(p for p in ATIVIDADES.iterdir() if p.is_file())
    print(f"lendo {len(arquivos)} arquivos (um ponto por minuto)...")

    linhas = []
    falhas = 0

    for i, caminho in enumerate(arquivos, 1):
        if i % 100 == 0:
            print(f"  {i}/{len(arquivos)}")
        try:
            pontos = extrair(caminho)
        except Exception:
            falhas += 1
            continue
        if not pontos:
            falhas += 1
            continue

        arquivo = f"activities/{caminho.name}"
        for ordem, (lat, lon) in enumerate(pontos):
            linhas.append(
                {"arquivo": arquivo, "ordem": ordem, "lat": lat, "lon": lon}
            )

    print(f"{len(linhas):,} pontos de {len(arquivos) - falhas} arquivos")
    if falhas:
        print(f"  {falhas} arquivo(s) sem pontos legíveis")

    return pd.DataFrame(linhas)


def identificar_cidades(tracos: pd.DataFrame) -> pd.DataFrame:
    """Cruza cada ponto com a malha municipal do IBGE.

    Usa apenas coordenadas distintas arredondadas a 3 casas (~110 m). Vários
    pontos caem no mesmo quadrado, sobretudo em pedal urbano, e o teste de
    ponto-em-polígono é a parte cara.
    """
    import geobr
    import geopandas as gpd

    print("\nbaixando malha municipal do IBGE (só na primeira vez)...")
    municipios = geobr.read_municipality(year=2022)
    municipios = municipios[["code_muni", "name_muni", "abbrev_state", "geometry"]]
    print(f"  {len(municipios):,} municípios")

    distintos = (
        tracos.assign(
            lat_r=tracos["lat"].round(3),
            lon_r=tracos["lon"].round(3),
        )[["lat_r", "lon_r"]]
        .drop_duplicates()
        .reset_index(drop=True)
    )
    print(f"cruzando {len(distintos):,} coordenadas distintas...")

    pontos = gpd.GeoDataFrame(
        distintos,
        geometry=gpd.points_from_xy(distintos["lon_r"], distintos["lat_r"]),
        crs=municipios.crs,
    )

    achados = gpd.sjoin(pontos, municipios, how="left", predicate="within")
    achados = achados[["lat_r", "lon_r", "name_muni", "abbrev_state"]]

    fora = achados["name_muni"].isna().sum()
    if fora:
        print(f"  {fora:,} coordenada(s) fora de qualquer município")

    ligado = tracos.assign(
        lat_r=tracos["lat"].round(3),
        lon_r=tracos["lon"].round(3),
    ).merge(achados, on=["lat_r", "lon_r"], how="left")

    cidades = (
        ligado.dropna(subset=["name_muni"])
        .groupby(["arquivo", "name_muni", "abbrev_state"], as_index=False)
        .size()
        .rename(
            columns={
                "name_muni": "cidade",
                "abbrev_state": "uf",
                "size": "pontos",
            }
        )
    )

    return cidades


def main() -> None:
    if not ATIVIDADES.is_dir():
        raise FileNotFoundError(f"Não encontrei {ATIVIDADES}.")

    tracos = coletar_tracos()
    cidades = identificar_cidades(tracos)

    with duckdb.connect(str(BANCO)) as con:
        # DuckDB resolve nomes do escopo Python; os aliases evitam a colisão
        # entre o nome da tabela e o nome do DataFrame.
        df_tracos = tracos
        df_cidades = cidades
        con.execute("DROP TABLE IF EXISTS tracos")
        con.execute("CREATE TABLE tracos AS SELECT * FROM df_tracos")
        con.execute("DROP TABLE IF EXISTS cidades")
        con.execute("CREATE TABLE cidades AS SELECT * FROM df_cidades")

        print("\nestados:")
        print(con.execute("""
            SELECT uf,
                   count(DISTINCT cidade) AS cidades,
                   count(DISTINCT arquivo) AS pedais
            FROM cidades GROUP BY 1 ORDER BY pedais DESC
        """).df().to_string(index=False))

        print("\ncidades mais atravessadas:")
        print(con.execute("""
            SELECT cidade, uf, count(DISTINCT arquivo) AS pedais
            FROM cidades GROUP BY 1, 2 ORDER BY pedais DESC LIMIT 15
        """).df().to_string(index=False))

        total = con.execute(
            "SELECT count(DISTINCT cidade || uf) FROM cidades"
        ).fetchone()[0]
        print(f"\n{total} cidades ao todo")


if __name__ == "__main__":
    main()
