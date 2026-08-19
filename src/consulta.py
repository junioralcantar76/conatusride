import duckdb, json

con = duckdb.connect("data/conatusride.duckdb")
linhas = con.execute("""
    SELECT p.data::DATE::VARCHAR d, p.nome, round(p.distancia_km,1) km,
           round(p.tempo_movimento_s/60) min, round(p.velocidade_media_kmh,1) v,
           p.ganho_elevacao_m el, p.tipo, p.porte, p.piso,
           (SELECT string_agg(c.cidade, ' > ' ORDER BY c.entrada)
              FROM cidades c WHERE c.arquivo = p.arquivo AND c.pontos > 5) rota
    FROM vw_pedais p
    WHERE p.ano = 2026 AND month(p.data) = 8
    ORDER BY p.data
""").fetchall()
print(json.dumps(linhas, ensure_ascii=False, default=str))