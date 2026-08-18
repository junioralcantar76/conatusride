import duckdb

con = duckdb.connect("data/conatusride.duckdb")
print(con.execute("""
    SELECT cidade, uf, max(pontos) maior_permanencia, count(*) vezes
    FROM cidades GROUP BY 1,2 HAVING max(pontos) <= 5 ORDER BY 3
""").df().to_string(index=False))