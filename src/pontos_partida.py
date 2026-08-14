"""
conatusride — extração do ponto de partida de cada pedal.

Lê os arquivos de traçado em data/raw/activities/ e grava a coordenada inicial
de cada um em data/conatusride.duckdb, tabela `pontos_partida`.

O activities.csv não traz coordenada nenhuma. A origem geográfica só existe nos
arquivos de traçado, e é ela que permite separar pedal urbano de evento, viagem
ou férias sem depender do nome que foi dado à atividade.

Lê apenas o ponto inicial, não o traçado completo — a análise de streams fica
para a v2.

Formatos suportados: .fit.gz, .fit, .gpx, .gpx.gz, .tcx, .tcx.gz

Uso:
    python src/pontos_partida.py
"""

from pathlib import Path
from xml.etree import ElementTree
import gzip
import io
import math
import re

import duckdb
import pandas as pd

# ---------------------------------------------------------------- caminhos

RAIZ = Path(__file__).resolve().parent.parent
ATIVIDADES = RAIZ / "data" / "raw" / "activities"
BANCO = RAIZ / "data" / "conatusride.duckdb"

# Referência para medir o quanto um pedal começou longe de casa.
FORTALEZA = (-3.7319, -38.5267)

# O FIT guarda coordenada em semicírculos: 2^31 semicírculos = 180 graus.
SEMICIRCULO = 180 / 2**31


# ---------------------------------------------------------------- leitura


def abrir(caminho: Path) -> bytes:
    """Devolve o conteúdo, descomprimindo se for .gz."""
    if caminho.suffix == ".gz":
        with gzip.open(caminho, "rb") as f:
            return f.read()
    return caminho.read_bytes()


def valida(lat, lon) -> bool:
    """Rejeita coordenada ausente ou zerada.

    Cerca de 36% dos FIT gravam start_position como zero em vez de omitir o
    campo. Zero é uma coordenada válida em tese — fica no Golfo da Guiné — mas
    aqui só pode ser falha de gravação, e aceitá-la joga o pedal a 4.300 km de
    Fortaleza.
    """
    if lat is None or lon is None:
        return False
    return not (abs(lat) < 1 and abs(lon) < 1)


def ponto_fit(dados: bytes):
    """Ponto inicial de um arquivo FIT.

    A mensagem `session` traz start_position no resumo, o que evita varrer o
    traçado inteiro. Quando esse campo vem ausente ou zerado, cai para o
    primeiro `record` com posição.
    """
    from fitparse import FitFile

    fit = FitFile(io.BytesIO(dados))

    for sessao in fit.get_messages("session"):
        valores = sessao.get_values()
        lat = valores.get("start_position_lat")
        lon = valores.get("start_position_long")
        if valida(lat, lon):
            return lat * SEMICIRCULO, lon * SEMICIRCULO

    for registro in fit.get_messages("record"):
        valores = registro.get_values()
        lat = valores.get("position_lat")
        lon = valores.get("position_long")
        if valida(lat, lon):
            return lat * SEMICIRCULO, lon * SEMICIRCULO

    return None


def ponto_xml(dados: bytes):
    """Ponto inicial de um GPX ou TCX.

    GPX guarda a coordenada como atributo de <trkpt lat= lon=>; TCX, como
    elementos <LatitudeDegrees> e <LongitudeDegrees>. Os namespaces variam
    entre versões, então a busca ignora o prefixo.
    """
    raiz = ElementTree.fromstring(dados)

    for elemento in raiz.iter():
        tag = elemento.tag.rsplit("}", 1)[-1]
        if tag in ("trkpt", "wpt", "rtept"):
            lat = elemento.get("lat")
            lon = elemento.get("lon")
            if lat and lon and valida(float(lat), float(lon)):
                return float(lat), float(lon)
        if tag == "Position":
            lat = lon = None
            for filho in elemento:
                nome = filho.tag.rsplit("}", 1)[-1]
                if nome == "LatitudeDegrees":
                    lat = float(filho.text)
                elif nome == "LongitudeDegrees":
                    lon = float(filho.text)
            if valida(lat, lon):
                return lat, lon

    return None


def extrair(caminho: Path):
    nome = caminho.name.lower()
    dados = abrir(caminho)
    if ".fit" in nome:
        return ponto_fit(dados)
    if ".gpx" in nome or ".tcx" in nome:
        return ponto_xml(dados)
    return None


# ---------------------------------------------------------------- distância


def distancia_km(origem, destino) -> float:
    """Distância em linha reta entre duas coordenadas (haversine)."""
    lat1, lon1 = origem
    lat2, lon2 = destino
    raio = 6371.0

    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2) ** 2
    )
    return 2 * raio * math.asin(math.sqrt(a))


# ---------------------------------------------------------------- principal


def main() -> None:
    if not ATIVIDADES.is_dir():
        raise FileNotFoundError(
            f"Não encontrei {ATIVIDADES}.\n"
            "Extraia a exportação do Strava dentro de data/raw/."
        )

    arquivos = sorted(p for p in ATIVIDADES.iterdir() if p.is_file())
    print(f"{len(arquivos)} arquivos em {ATIVIDADES.name}/")

    linhas = []
    falhas = []

    for i, caminho in enumerate(arquivos, 1):
        if i % 100 == 0:
            print(f"  {i}/{len(arquivos)}")
        try:
            ponto = extrair(caminho)
        except Exception as erro:
            falhas.append((caminho.name, f"{type(erro).__name__}: {erro}"))
            continue
        if ponto is None:
            falhas.append((caminho.name, "sem coordenada"))
            continue

        lat, lon = ponto
        linhas.append(
            {
                # Como está gravado na coluna `arquivo` da tabela pedais.
                "arquivo": f"activities/{caminho.name}",
                "lat": lat,
                "lon": lon,
                "km_de_fortaleza": round(distancia_km(FORTALEZA, (lat, lon)), 1),
            }
        )

    df = pd.DataFrame(linhas)
    print(f"\n{len(df)} pontos extraídos, {len(falhas)} sem coordenada")

    if falhas:
        print("\nprimeiras falhas:")
        for nome, motivo in falhas[:5]:
            print(f"  {nome}: {motivo}")

    with duckdb.connect(str(BANCO)) as con:
        con.execute("DROP TABLE IF EXISTS pontos_partida")
        con.execute("CREATE TABLE pontos_partida AS SELECT * FROM df")

        casados = con.execute("""
            SELECT count(*) FROM pedais p
            JOIN pontos_partida t USING (arquivo)
        """).fetchone()[0]
        print(f"{casados} pedais casaram com um ponto de partida")

        print("\ndistância do ponto de partida até Fortaleza:")
        print(
            con.execute("""
                SELECT CASE
                         WHEN km_de_fortaleza < 50  THEN 'a  ate 50 km'
                         WHEN km_de_fortaleza < 150 THEN 'b  50-150 km'
                         WHEN km_de_fortaleza < 300 THEN 'c  150-300 km'
                         ELSE                            'd  300+ km'
                       END AS faixa,
                       count(*) AS pedais
                FROM pedais p JOIN pontos_partida t USING (arquivo)
                GROUP BY 1 ORDER BY 1
            """).df().to_string(index=False)
        )


if __name__ == "__main__":
    main()
