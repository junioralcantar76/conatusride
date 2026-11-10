"""
conatusride — atualização incremental pela API do Strava.

Busca os pedais posteriores ao último que está na base, baixa o traçado de cada
um e grava nas mesmas tabelas que a exportação alimenta.

Substitui o ciclo de reexportar tudo: a exportação refaz 974 arquivos para
acrescentar 5, e o tracos.py sozinho leva 15 minutos nisso. Aqui são segundos.

Depois de rodar, siga com:
    python src/classificar.py
    python src/gerar_site.py

A exportação continua sendo o caminho para a carga inicial e para recuperar a
base do zero. Esta via é só para o dia a dia.

Precisa de data/strava_token.json, criado uma vez na autorização.

Uso:
    python src/atualizar.py
"""

from pathlib import Path
import json
import math
import time

import duckdb
import pandas as pd
import requests

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "conatusride.duckdb"
TOKEN = RAIZ / "data" / "strava_token.json"

BASE = "https://www.strava.com"
API = BASE + "/api/v3"
FORTALEZA = (-3.7319, -38.5267)

# Mesmo corte do importar.py: acima disto a elevação é erro de altímetro.
MAX_M_POR_KM = 30

# Um ponto por minuto, como o tracos.py faz com os arquivos da exportação.
INTERVALO_S = 60

# Minutos dentro de um município para a cidade contar na rota.
MIN_PERMANENCIA = 5


# ---------------------------------------------------------------- token


def carregar_token() -> dict:
    if not TOKEN.exists():
        raise FileNotFoundError(
            f"Não encontrei {TOKEN}.\n"
            "A autorização inicial precisa ser refeita."
        )
    return json.loads(TOKEN.read_text(encoding="utf-8"))


def token_valido() -> str:
    """Devolve um access token válido, renovando se tiver expirado.

    O access token dura 6 horas; o refresh token não expira. Renovar na hora
    do uso evita ter de lembrar quando foi a última vez.
    """
    t = carregar_token()

    # 60 s de folga: o token pode vencer entre a conferência e a chamada.
    if t["expires_at"] > time.time() + 60:
        return t["access_token"]

    print("renovando token...")
    r = requests.post(f"{BASE}/oauth/token", data={
        "client_id": t["client_id"],
        "client_secret": t["client_secret"],
        "refresh_token": t["refresh_token"],
        "grant_type": "refresh_token",
    })
    r.raise_for_status()
    novo = r.json()

    t.update({
        "access_token": novo["access_token"],
        "refresh_token": novo["refresh_token"],
        "expires_at": novo["expires_at"],
    })
    TOKEN.write_text(json.dumps(t, indent=2), encoding="utf-8")
    return t["access_token"]


def pedir(caminho: str, token: str, **params):
    r = requests.get(f"{API}{caminho}",
                     headers={"Authorization": "Bearer " + token},
                     params=params)
    if r.status_code == 429:
        raise RuntimeError(
            "limite da API atingido (100 a cada 15 min). Tente mais tarde."
        )
    r.raise_for_status()
    return r.json()


# ---------------------------------------------------------------- busca


def ultima_data(con) -> int:
    """Timestamp do último pedal na base, para pedir só o que veio depois."""
    linha = con.execute("SELECT max(data) FROM pedais").fetchone()[0]
    if linha is None:
        raise RuntimeError(
            "A base está vazia. Faça a carga inicial com src/importar.py."
        )
    return int(pd.Timestamp(linha).timestamp())


def buscar_novas(token: str, depois: int) -> list:
    """Atividades posteriores a `depois`, página a página."""
    novas, pagina = [], 1
    while True:
        lote = pedir("/athlete/activities", token,
                     after=depois, per_page=50, page=pagina)
        if not lote:
            break
        novas.extend(lote)
        if len(lote) < 50:
            break
        pagina += 1
    # Só pedaladas: a base é sobre isso, e um dia pode entrar outro esporte.
    return [a for a in novas if a.get("type") == "Ride"]


def buscar_traco(token: str, id_atividade: int):
    """Pontos do traçado, amostrados por minuto.

    `latlng` vem ponto a ponto e `time` traz o segundo de cada um, então dá
    para amostrar pelo tempo real em vez de contar pontos — a taxa de gravação
    varia entre aparelhos.
    """
    try:
        fluxos = pedir(f"/activities/{id_atividade}/streams", token,
                       keys="latlng,time", key_by_type="true")
    except requests.HTTPError:
        return []

    coords = (fluxos.get("latlng") or {}).get("data") or []
    tempos = (fluxos.get("time") or {}).get("data") or []
    if not coords:
        return []

    saida, ultimo = [], None
    for i, (lat, lon) in enumerate(coords):
        if abs(lat) < 1 and abs(lon) < 1:
            continue
        s = tempos[i] if i < len(tempos) else i
        if ultimo is None or s - ultimo >= INTERVALO_S:
            saida.append((lat, lon))
            ultimo = s
    return saida


# ---------------------------------------------------------------- conversão


def distancia_km(origem, destino) -> float:
    lat1, lon1 = origem
    lat2, lon2 = destino
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat / 2) ** 2
         + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2))
         * math.sin(dlon / 2) ** 2)
    return 2 * 6371.0 * math.asin(math.sqrt(a))


def converter(a: dict) -> dict:
    """Atividade da API no formato da tabela `pedais`.

    A API não traz clima, inclinação nem distância em terra — esses campos
    ficam nulos nos pedais vindos por aqui. O resto bate com a exportação.
    """
    data = pd.Timestamp(a["start_date_local"].replace("Z", ""))
    distancia_m = float(a.get("distance") or 0)
    km = distancia_m / 1000
    ganho = a.get("total_elevation_gain")

    if ganho is not None and km > 1 and ganho > km * MAX_M_POR_KM:
        print(f"  elevação implausível: {a['name']} — "
              f"{ganho:.0f} m em {km:.1f} km, descartada")
        ganho = None

    media = float(a.get("average_speed") or 0)
    maxima = float(a.get("max_speed") or 0)
    decorrido = a.get("elapsed_time") or 0

    return {
        "id": int(a["id"]),
        "data": data,
        "ano": data.year,
        "mes": data.strftime("%Y-%m"),
        "nome": (a.get("name") or "").strip(),
        # Sem arquivo em disco: a origem é a API. O nome mantém o formato de
        # chave usado pelas tabelas de traçado e cidades.
        "arquivo": f"api/{a['id']}",
        "bicicleta_id": None,
        "tempo_total_s": decorrido,
        "tempo_movimento_s": a.get("moving_time"),
        "distancia_m": distancia_m,
        "distancia_terra_m": None,
        "velocidade_media_ms": media,
        "velocidade_max_ms": maxima,
        "velocidade_media_total_ms": distancia_m / decorrido if decorrido else None,
        "ganho_elevacao_m": ganho,
        "perda_elevacao_m": None,
        "elevacao_min_m": a.get("elev_low"),
        "elevacao_max_m": a.get("elev_high"),
        "inclinacao_media_pct": None,
        "inclinacao_max_pct": None,
        "watts_medio": a.get("average_watts"),
        "calorias": a.get("kilojoules"),
        "fc_media": a.get("average_heartrate"),
        "fc_max": a.get("max_heartrate"),
        "distancia_km": km,
        "velocidade_media_kmh": media * 3.6,
        "velocidade_max_kmh": maxima * 3.6,
    }


# ---------------------------------------------------------------- gravação


def gravar(con, pedais: list, tracos: list, cidades: pd.DataFrame) -> None:
    """Insere nas tabelas existentes, sem recriar.

    Diferente do importar.py, que refaz a tabela: aqui só se acrescenta, e o
    histórico vindo da exportação fica intocado.
    """
    colunas = [c[0] for c in con.execute("DESCRIBE pedais").fetchall()]
    df = pd.DataFrame(pedais)
    for coluna in colunas:
        if coluna not in df.columns:
            df[coluna] = None
    df = df[colunas]

    con.execute("INSERT INTO pedais SELECT * FROM df")

    if tracos:
        dft = pd.DataFrame(tracos)
        con.execute("INSERT INTO tracos SELECT * FROM dft")

        pontos = (
            dft.groupby("arquivo")
            .agg(lat=("lat", "first"), lon=("lon", "first"))
            .reset_index()
        )
        pontos["km_de_fortaleza"] = pontos.apply(
            lambda r: round(distancia_km(FORTALEZA, (r["lat"], r["lon"])), 1),
            axis=1,
        )
        con.execute("INSERT INTO pontos_partida SELECT * FROM pontos")

    if cidades is not None and len(cidades):
        dfc = cidades
        con.execute("INSERT INTO cidades SELECT * FROM dfc")


def identificar_cidades(tracos: list) -> pd.DataFrame:
    """Cruza os pontos novos com a malha municipal, como o tracos.py faz."""
    if not tracos:
        return pd.DataFrame()

    import geobr
    import geopandas as gpd

    df = pd.DataFrame(tracos)
    print("cruzando com a malha do IBGE...")
    municipios = geobr.read_municipality(year=2022)[
        ["name_muni", "abbrev_state", "geometry"]
    ]

    df["lat_r"] = df["lat"].round(3)
    df["lon_r"] = df["lon"].round(3)
    distintos = df[["lat_r", "lon_r"]].drop_duplicates().reset_index(drop=True)

    pontos = gpd.GeoDataFrame(
        distintos,
        geometry=gpd.points_from_xy(distintos["lon_r"], distintos["lat_r"]),
        crs=municipios.crs,
    )
    achados = gpd.sjoin(pontos, municipios, how="left", predicate="within")[
        ["lat_r", "lon_r", "name_muni", "abbrev_state"]
    ]

    ligado = df.merge(achados, on=["lat_r", "lon_r"], how="left")
    return (
        ligado.dropna(subset=["name_muni"])
        .groupby(["arquivo", "name_muni", "abbrev_state"], as_index=False)
        .agg(pontos=("ordem", "size"), entrada=("ordem", "min"))
        .rename(columns={"name_muni": "cidade", "abbrev_state": "uf"})
        .sort_values(["arquivo", "entrada"])
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------- principal


def main() -> None:
    if not BANCO.exists():
        raise FileNotFoundError(
            f"Não encontrei {BANCO}. Faça a carga inicial com src/importar.py."
        )

    token = token_valido()

    with duckdb.connect(str(BANCO)) as con:
        depois = ultima_data(con)
        ultimo = pd.Timestamp(depois, unit="s")
        print(f"último pedal na base: {ultimo:%d/%m/%Y}")

        atividades = buscar_novas(token, depois)
        if not atividades:
            print("nenhum pedal novo")
            return

        print(f"{len(atividades)} pedal(is) novo(s)\n")

        pedais, tracos = [], []
        for a in sorted(atividades, key=lambda x: x["start_date_local"]):
            registro = converter(a)
            pedais.append(registro)
            print(f"  {registro['data']:%d/%m} {registro['nome']} · "
                  f"{registro['distancia_km']:.1f} km")

            pontos = buscar_traco(token, a["id"])
            for ordem, (lat, lon) in enumerate(pontos):
                tracos.append({
                    "arquivo": registro["arquivo"],
                    "ordem": ordem,
                    "lat": lat,
                    "lon": lon,
                })

        cidades = identificar_cidades(tracos)
        gravar(con, pedais, tracos, cidades)

        total = con.execute("SELECT count(*) FROM pedais").fetchone()[0]
        print(f"\n{total} pedais na base")
        print("agora rode: python src/classificar.py && python src/gerar_site.py")


if __name__ == "__main__":
    main()
