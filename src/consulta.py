import duckdb

con = duckdb.connect("data/conatusride.duckdb")
print(con.execute("""
    WITH c AS (
      SELECT *, CASE
          WHEN distancia_km > 79 THEN 'longao'
          WHEN distancia_km >= 50 THEN 'medio'
          ELSE 'curto'
        END AS porte
      FROM pedais
    )
    SELECT ano,
           sum(CASE WHEN porte='curto'  THEN 1 ELSE 0 END) curto,
           sum(CASE WHEN porte='medio'  THEN 1 ELSE 0 END) medio,
           sum(CASE WHEN porte='longao' THEN 1 ELSE 0 END) longao,
           count(*) total
    FROM c GROUP BY 1 ORDER BY 1
""").df().to_string())