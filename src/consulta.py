import duckdb, json

con = duckdb.connect("data/conatusride.duckdb")
linhas = con.execute("""
    SELECT data::DATE::VARCHAR d, nome, round(distancia_km,1) km,
           round(tempo_movimento_s/60) min, round(velocidade_media_kmh,1) v,
           ganho_elevacao_m el, tipo, porte, piso, cidade_nova
    FROM vw_pedais WHERE ano = 2026 ORDER BY data
""").fetchall()
print(json.dumps(linhas, ensure_ascii=False, default=str))