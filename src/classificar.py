"""
conatusride — classificação dos pedais.

Grava a tabela `classificacao` e cria a view `vw_pedais`, que junta tudo de
`pedais` com os pontos de partida e chegada e os três campos de classificação.

Três campos independentes, porque um pedal pode ser evento *e* exploração ao
mesmo tempo (Guaramiranga, 2023) — uma gaveta só não comporta isso.

    tipo         rotina, treino, evento, viagem
    porte        curto, medio, longo
    exploracao   sim ou não

Ordem: importar.py -> pontos_partida.py -> tracos.py -> metas.py ->
       classificar.py -> gerar_site.py

Uso:
    python src/classificar.py
"""

from pathlib import Path
import csv
import unicodedata

import duckdb
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "conatusride.duckdb"
EVENTOS = RAIZ / "docs" / "eventos.csv"

# ---------------------------------------------------------------- regras
#
# tipo
#   rotina   dentro da região de rotina (lista abaixo)
#   treino   na região de rotina, até 20 km, de 2026 em diante. Antes disso um
#            pedal curto não era treino: era passeio ou pedal noturno de grupo.
#   viagem   fora da região, dois ou mais dias de pedal no mesmo período, com
#            base no lugar (Ubajara, dois dias seguidos; férias em Ipaumirim).
#            Tolera até 3 dias de folga dentro do bloco — em férias há dias de
#            descanso no meio, e um corte rígido jogava esses pedais soltos para
#            evento.
#   evento   fora da região em dia isolado, ou marcado à mão em docs/eventos.csv
#
# Evento não se define por geografia — existe trilha em Caucaia, dentro da
# região de rotina. O que separa evento de rotina é ter data marcada e
# organização, e isso o dado do Strava não sabe. Por isso a marcação manual tem
# a última palavra.
#
# Dentro ou fora é decidido pelas cidades atravessadas: basta uma das pontas
# estar na região. Quem sai de Beberibe e volta para casa fez um pedal de
# rotina, não um evento — e quem sai de Fortaleza rumo a Chorozinho também.
#
# porte — o mesmo tamanho, aplicado a qualquer pedal. Uma escala só, para os
# campos nunca se contradizerem. Pindoretama e volta dá 100 km e é rotina de
# porte longo.
#
# exploracao — o pedal atravessou ao menos uma cidade onde eu nunca tinha
# pedalado até aquela data. Não é sobre rota nova nem sobre distância, é sobre
# estar fora da rotina: uma trilha na região metropolitana conta.

# A região que eu rodo como rotina. Não é a Região Metropolitana legal: a lei
# inclui Paracuru, Paraipaba, Trairi e São Luís do Curu, que ficam no litoral
# oeste a mais de 100 km — ir até lá é pedal de viagem, não rotina. Saíram
# também Chorozinho, Pacajus, Horizonte, Guaiúba, Itaitinga, Pacatuba e
# Cascavel, pelo mesmo motivo.
REGIAO_ROTINA = {
    "fortaleza", "caucaia", "maracanau", "maranguape",
    "aquiraz", "eusebio", "pindoretama",
}

ANO_TREINO = 2026
KM_TREINO = 20
FOLGA_VIAGEM = 3
KM_MEDIO = 50
KM_LONGO = 75


def chave(nome: str) -> str:
    """Minúsculo e sem acento, para comparar nome de cidade."""
    puro = unicodedata.normalize("NFKD", nome or "")
    return "".join(c for c in puro if not unicodedata.combining(c)).lower().strip()


def porte(km: float) -> str:
    if km >= KM_LONGO:
        return "longo"
    if km >= KM_MEDIO:
        return "medio"
    return "curto"


def ler_eventos() -> set:
    """Datas marcadas à mão como evento.

    docs/eventos.csv, colunas evento,cidade_local,data — data em AAAA-MM-DD.
    """
    if not EVENTOS.exists():
        return set()
    with EVENTOS.open(encoding="utf-8") as f:
        return {
            linha["data"].strip()
            for linha in csv.DictReader(f)
            if linha.get("data", "").strip()
        }


def classificar(pedais: pd.DataFrame, cidades: pd.DataFrame,
                marcados: set) -> pd.DataFrame:
    pedais = pedais.sort_values("data").reset_index(drop=True)

    por_arquivo = {}
    for arquivo, grupo in cidades.sort_values("entrada").groupby("arquivo"):
        por_arquivo[arquivo] = list(grupo["cidade"])

    vistas = set()
    linhas = []

    for _, p in pedais.iterrows():
        lista = por_arquivo.get(p["arquivo"], [])
        chaves = [chave(c) for c in lista]

        if chaves:
            dentro = chaves[0] in REGIAO_ROTINA or chaves[-1] in REGIAO_ROTINA
        else:
            # Sem cidade identificada, cai para a distância até Fortaleza.
            km = p["km_de_casa"]
            dentro = pd.isna(km) or km < 50

        novas = [c for c in chaves if c not in vistas]
        nomes_novos = [lista[chaves.index(c)] for c in novas]
        vistas.update(chaves)

        linhas.append({
            "id": p["id"],
            "data": p["data"],
            "dentro_regiao": bool(dentro),
            "exploracao": bool(novas),
            "cidade_nova": ", ".join(nomes_novos) if novas else None,
            "porte": porte(p["distancia_km"]),
            "_ano": int(p["ano"]),
            "_km": float(p["distancia_km"]),
            "_dia": pd.Timestamp(p["data"]).date(),
        })

    df = pd.DataFrame(linhas)

    # Fora da RMF: dias consecutivos viram viagem; dia isolado, evento.
    dias_fora = sorted(set(df.loc[~df["dentro_regiao"], "_dia"]))
    em_viagem, bloco = set(), []
    for dia in dias_fora:
        if bloco and (dia - bloco[-1]).days <= FOLGA_VIAGEM:
            bloco.append(dia)
        else:
            if len(bloco) >= 2:
                em_viagem.update(bloco)
            bloco = [dia]
    if len(bloco) >= 2:
        em_viagem.update(bloco)

    def tipo(linha):
        if linha["data"].strftime("%Y-%m-%d") in marcados:
            return "evento"
        if not linha["dentro_regiao"]:
            return "viagem" if linha["_dia"] in em_viagem else "evento"
        if linha["_ano"] >= ANO_TREINO and linha["_km"] <= KM_TREINO:
            return "treino"
        return "rotina"

    df["tipo"] = df.apply(tipo, axis=1)
    return df[["id", "tipo", "porte", "exploracao", "cidade_nova", "dentro_regiao"]]


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
       c.tipo, c.porte, c.exploracao, c.cidade_nova, c.dentro_regiao,
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
            SELECT p.id, p.arquivo, p.data, p.ano, p.distancia_km,
                   least(t.km_de_fortaleza, f.km_fim_fortaleza) AS km_de_casa
            FROM pedais p
            LEFT JOIN pontos_partida t USING (arquivo)
            LEFT JOIN vw_chegada f USING (arquivo)
        """).df()
        cidades = con.execute(
            "SELECT arquivo, cidade, entrada FROM cidades"
        ).df()

        marcados = ler_eventos()
        if marcados:
            print(f"{len(marcados)} evento(s) marcado(s) em docs/eventos.csv")
        else:
            print("docs/eventos.csv ainda não existe — evento sai só da regra")

        resultado = classificar(pedais, cidades, marcados)

        con.execute("DROP TABLE IF EXISTS classificacao")
        con.execute("CREATE TABLE classificacao AS SELECT * FROM resultado")
        con.execute(VIEW_PEDAIS)

        print("\nvw_pedais criada.\n")
        print(con.execute("""
            SELECT tipo, count(*) AS pedais,
                   round(avg(distancia_km), 1) AS km,
                   round(avg(velocidade_media_kmh), 1) AS kmh,
                   round(avg(ganho_elevacao_m / distancia_km), 1) AS m_por_km,
                   sum(exploracao::INT) AS com_cidade_nova,
                   min(ano) AS de, max(ano) AS ate
            FROM vw_pedais GROUP BY 1 ORDER BY pedais DESC
        """).df().to_string(index=False))

        print()
        print(con.execute("""
            SELECT ano,
                   sum((tipo = 'rotina')::INT) AS rotina,
                   sum((tipo = 'treino')::INT) AS treino,
                   sum((tipo = 'evento')::INT) AS evento,
                   sum((tipo = 'viagem')::INT) AS viagem,
                   sum((porte = 'curto')::INT) AS curto,
                   sum((porte = 'medio')::INT) AS medio,
                   sum((porte = 'longo')::INT) AS longo,
                   sum(exploracao::INT)        AS exploracao
            FROM vw_pedais GROUP BY 1 ORDER BY ano
        """).df().to_string(index=False))


if __name__ == "__main__":
    main()
