import duckdb

con = duckdb.connect("data/conatusride.duckdb")

print(con.execute("""
    WITH top AS (
      SELECT ano, arquivo, nome, distancia_km,
             row_number() OVER (PARTITION BY ano ORDER BY distancia_km DESC) r
      FROM pedais
    ),
    seq AS (
      SELECT t.ano, t.nome, t.arquivo, c.cidade, c.uf,
             min(c.pontos) OVER () AS x
      FROM top t JOIN cidades c USING (arquivo)
      WHERE t.r <= 5
    )
    SELECT ano, nome, string_agg(cidade || '/' || uf, ' > ') percurso
    FROM (SELECT DISTINCT ano, nome, cidade, uf FROM seq)
    GROUP BY 1,2 ORDER BY 1
""").df().to_csv(index=False))