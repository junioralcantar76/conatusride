"""
conatusride — contornos para o mapa.

Extrai da malha do IBGE os contornos dos 27 estados e dos municípios dos
estados onde já pedalei, simplifica e grava em data/contornos.json.

Simplificar é o que torna o mapa viável: a malha original do IBGE tem detalhe
de metros, bom para cartografia e desnecessário para um mapa que cabe numa
tela. A tolerância abaixo reduz o arquivo em mais de 90% sem diferença visível.

O arquivo fica em data/ (fora do Git, como o resto) porque é derivado: quem
clonar o repositório roda este script e o reproduz.

Depende de geobr, que baixa a malha e guarda em cache — só a primeira execução
precisa de internet.

Uso:
    python src/contornos.py
"""

from pathlib import Path
import json

import duckdb
from shapely.geometry import mapping

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "conatusride.duckdb"
SAIDA = RAIZ / "data" / "contornos.json"

# Graus. 0.02 ≈ 2 km: some o detalhe de praia e rio, o formato fica igual.
# Estados aceitam mais simplificação que municípios porque são desenhados
# menores na tela.
TOL_ESTADO = 0.08
TOL_MUNICIPIO = 0.003

# Casas decimais nas coordenadas. 4 ≈ 11 m, mais que suficiente, e corta
# metade do arquivo.
CASAS = 3


def arredondar(geo, casas=CASAS):
    """Percorre a geometria arredondando toda coordenada."""
    if isinstance(geo, (list, tuple)):
        if geo and isinstance(geo[0], (int, float)):
            return [round(float(x), casas) for x in geo]
        return [arredondar(x, casas) for x in geo]
    return geo


def simplificar(gdf, tolerancia):
    """Simplifica preservando a topologia de cada polígono isolado.

    `preserve_topology=True` evita que ilhas e penínsulas finas desapareçam
    ou que o polígono se feche sobre si mesmo.
    """
    gdf = gdf.copy()
    gdf["geometry"] = gdf.geometry.simplify(tolerancia, preserve_topology=True)
    return gdf


def feicoes(gdf, campos: dict) -> list:
    """Converte para uma lista de feições GeoJSON enxutas."""
    saida = []
    for _, linha in gdf.iterrows():
        if linha.geometry is None or linha.geometry.is_empty:
            continue
        geometria = mapping(linha.geometry)
        saida.append({
            **{destino: linha[origem] for origem, destino in campos.items()},
            "g": arredondar(geometria["coordinates"]),
            "t": 1 if geometria["type"] == "Polygon" else 2,
        })
    return saida


def cidades_visitadas(banco: Path) -> dict:
    """Quantos pedais passaram por cada cidade, e a data da primeira vez."""
    if not banco.exists():
        return {}
    with duckdb.connect(str(banco), read_only=True) as con:
        try:
            linhas = con.execute("""
                SELECT c.cidade, c.uf,
                       count(DISTINCT c.arquivo) AS pedais,
                       min(p.data)::DATE::VARCHAR AS primeira
                FROM cidades c JOIN pedais p USING (arquivo)
                WHERE c.pontos > 5
                GROUP BY 1, 2
            """).fetchall()
        except duckdb.Error:
            return {}
    return {
        f"{cidade}|{uf}": {"n": int(n), "desde": desde}
        for cidade, uf, n, desde in linhas
    }


def main() -> None:
    import geobr

    visitadas = cidades_visitadas(BANCO)
    ufs = sorted({chave.split("|")[1] for chave in visitadas})
    print(f"{len(visitadas)} cidades visitadas em {len(ufs)} estado(s): "
          f"{', '.join(ufs) if ufs else '—'}")

    print("lendo malha dos estados...")
    estados = geobr.read_state(year=2020)[["abbrev_state", "name_state", "geometry"]]
    estados = simplificar(estados, TOL_ESTADO)

    print("lendo malha dos municípios...")
    municipios = geobr.read_municipality(year=2022)
    municipios = municipios[municipios["abbrev_state"].isin(ufs)]
    municipios = municipios[["name_muni", "abbrev_state", "geometry"]]
    municipios = simplificar(municipios, TOL_MUNICIPIO)
    print(f"  {len(municipios)} municípios nos estados visitados")

    dados = {
        "estados": feicoes(estados, {"abbrev_state": "uf",
                                     "name_state": "nome"}),
        "municipios": feicoes(municipios, {"name_muni": "nome",
                                           "abbrev_state": "uf"}),
        "visitadas": visitadas,
    }

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(
        json.dumps(dados, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    kb = SAIDA.stat().st_size / 1024
    print(f"\n{len(dados['estados'])} estados, "
          f"{len(dados['municipios'])} municípios")
    print(f"data/contornos.json — {kb:.0f} KB")


if __name__ == "__main__":
    main()
