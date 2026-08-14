"""
conatusride — view de consulta com as classificações.

Cria `vw_pedais` no banco: tudo de `pedais`, mais o ponto de partida e os campos
`tipo` e `porte`.

É view, não tabela, porque `tipo` depende de `pontos_partida`, gerada por outro
script. Coluna gravada ficaria desatualizada sempre que um dos dois rodasse
sozinho; a view calcula na hora e a regra fica escrita num lugar só.

Ordem: importar.py -> pontos_partida.py -> classificar.py

Uso:
    python src/classificar.py
"""

from pathlib import Path

import duckdb

RAIZ = Path(__file__).resolve().parent.parent
BANCO = RAIZ / "data" / "conatusride.duckdb"

# ---------------------------------------------------------------- regras
#
# tipo — natureza do pedal, definida por onde começou e em que fase.
#   exploracao   ponto de partida a 300+ km de Fortaleza. Férias no interior,
#                rota nova, terra e asfalto alternados.
#   evento       50 a 300 km. Trilhas em cidades do interior, quase sempre
#                eventos festivos com data marcada.
#   treino       2026 em diante, até 20 km. Bloco matinal curto e rápido que
#                substituiu o pedal noturno urbano. Antes de 2026 um pedal
#                curto não era treino: era passeio ou pedal noturno de grupo.
#   local_*      Fortaleza e região, separados por distância.
#
# porte — esforço percebido, escala do próprio ciclista.
#   É régua de 2026 aplicada ao passado: mostra o crescimento, já que 2021 não
#   tem nenhum médio ou longão.

VIEW = """
CREATE OR REPLACE VIEW vw_pedais AS
SELECT
    p.*,
    t.lat,
    t.lon,
    t.km_de_fortaleza,

    CASE
        WHEN t.km_de_fortaleza >= 300           THEN 'exploracao'
        WHEN t.km_de_fortaleza >= 50            THEN 'evento'
        WHEN p.ano >= 2026 AND p.distancia_km <= 20 THEN 'treino'
        WHEN p.distancia_km >= 45               THEN 'local_longo'
        WHEN p.distancia_km >= 25               THEN 'local_medio'
        ELSE                                         'local_curto'
    END AS tipo,

    CASE
        WHEN p.distancia_km > 79  THEN 'longao'
        WHEN p.distancia_km >= 50 THEN 'medio'
        ELSE                           'curto'
    END AS porte,

    hour(p.data) >= 19 AS noturno

FROM pedais p
LEFT JOIN pontos_partida t USING (arquivo)
"""


def main() -> None:
    if not BANCO.exists():
        raise FileNotFoundError(
            f"Não encontrei {BANCO}. Rode src/importar.py primeiro."
        )

    with duckdb.connect(str(BANCO)) as con:
        tabelas = {t[0] for t in con.execute("SHOW TABLES").fetchall()}
        if "pontos_partida" not in tabelas:
            raise RuntimeError(
                "Tabela pontos_partida não existe. "
                "Rode src/pontos_partida.py antes."
            )

        con.execute(VIEW)

        sem_ponto = con.execute(
            "SELECT count(*) FROM vw_pedais WHERE km_de_fortaleza IS NULL"
        ).fetchone()[0]
        if sem_ponto:
            print(f"aviso: {sem_ponto} pedal(is) sem ponto de partida")

        print("vw_pedais criada.\n")

        print(con.execute("""
            SELECT tipo,
                   count(*) AS pedais,
                   round(avg(distancia_km), 1) AS km,
                   round(avg(velocidade_media_kmh), 1) AS kmh,
                   round(avg(ganho_elevacao_m / distancia_km), 1) AS m_por_km,
                   sum(noturno::INT) AS noturnos,
                   min(ano) AS de,
                   max(ano) AS ate
            FROM vw_pedais
            GROUP BY 1 ORDER BY pedais DESC
        """).df().to_string(index=False))

        print()
        print(con.execute("""
            SELECT ano,
                   sum((porte = 'curto')::INT)  AS curto,
                   sum((porte = 'medio')::INT)  AS medio,
                   sum((porte = 'longao')::INT) AS longao,
                   count(*) AS total
            FROM vw_pedais
            GROUP BY 1 ORDER BY ano
        """).df().to_string(index=False))


if __name__ == "__main__":
    main()
