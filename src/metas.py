"""
conatusride — importação das metas do Strava.

Lê data/raw/goals.csv e grava a tabela `metas_ano`: a meta anual vigente no
fim de cada ano, junto do realizado.

O arquivo não traz uma meta por ano: traz cada vez que a meta foi alterada,
com data de início e fim — 25 alterações anuais ao todo, 12 só em 2022. Guardar
esse vaivém não interessa; o que fica é a meta que valia em 31/12, ou a atual
no caso do ano corrente.

As metas aqui são registro histórico, não cobrança. Servem para lembrar o que
se pretendia em cada fase, não para medir o que falta.

Uso:
    python src/metas.py
"""

from pathlib import Path
import re

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
CSV = RAIZ / "data" / "raw" / "goals.csv"
BANCO = RAIZ / "data" / "conatusride.duckdb"

MESES = {
    "jan": 1, "fev": 2, "mar": 3, "abr": 4, "mai": 5, "jun": 6,
    "jul": 7, "ago": 8, "set": 9, "out": 10, "nov": 11, "dez": 12,
}

PADRAO_DATA = re.compile(
    r"(\d{1,2}) de (\w{3})\.? de (\d{4}),?\s+(\d{1,2}):(\d{2}):(\d{2})"
)


def converter_data(texto):
    """Mesmo formato brasileiro por extenso do activities.csv."""
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


def carregar(caminho: Path) -> pd.DataFrame:
    if not caminho.exists():
        raise FileNotFoundError(
            f"Não encontrei {caminho}.\n"
            "Extraia a exportação do Strava dentro de data/raw/."
        )

    bruto = pd.read_csv(caminho)

    df = pd.DataFrame({
        "periodo": bruto["Período"],
        "meta_km": bruto["Meta"] / 1000,
        "inicio": bruto["Data de início"].map(converter_data),
        "fim": bruto["Data de término"].map(converter_data),
    })

    # Meta zerada é apagamento, não objetivo.
    df = df[df["meta_km"] > 0]

    return df.sort_values("inicio").reset_index(drop=True)


def meta_vigente(anuais: pd.DataFrame, ano: int):
    """Meta que valia no fim do ano.

    Intervalo em aberto (sem data de término) é a meta atual.
    """
    corte = pd.Timestamp(ano, 12, 31, 23, 59, 59)
    valendo = anuais[
        (anuais["inicio"] <= corte)
        & (anuais["fim"].isna() | (anuais["fim"] > corte))
    ]
    if valendo.empty:
        return None
    return float(valendo.iloc[-1]["meta_km"])


def main() -> None:
    df = carregar(CSV)
    anuais = df[df["periodo"] == "Ano"]

    print(f"{len(df)} metas: {dict(df['periodo'].value_counts())}")

    with duckdb.connect(str(BANCO)) as con:
        con.execute("DROP TABLE IF EXISTS metas_historico")

        realizado = con.execute("""
            SELECT ano, round(sum(distancia_km)) AS km
            FROM pedais GROUP BY 1 ORDER BY 1
        """).df()

        realizado["meta_km"] = realizado["ano"].map(
            lambda a: meta_vigente(anuais, a)
        )
        realizado["pct"] = (
            100 * realizado["km"] / realizado["meta_km"]
        ).round(1)
        con.execute("DROP TABLE IF EXISTS metas_ano")
        con.execute("CREATE TABLE metas_ano AS SELECT * FROM realizado")

        print("\nmeta anual x realizado:")
        print(con.execute("""
            SELECT ano, meta_km AS meta, km AS realizado, pct
            FROM metas_ano ORDER BY ano
        """).df().to_string(index=False))


if __name__ == "__main__":
    main()
