import duckdb
con = duckdb.connect("data/conatusride.duckdb")
print(con.execute("""
    SELECT data::DATE d, nome, round(distancia_km,1) km, exploracao
    FROM vw_pedais WHERE tipo='evento' ORDER BY data
""").df().to_string(index=False))