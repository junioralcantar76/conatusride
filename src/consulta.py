import duckdb

con = duckdb.connect("data/conatusride.duckdb")
print(con.execute("""
    WITH r AS (
      SELECT v.ano, v.tipo, v.data::DATE d, v.nome,
             round(v.distancia_km,1) km, v.ganho_elevacao_m elev,
             round(v.velocidade_media_kmh,1) vel, v.arquivo,
             row_number() OVER (PARTITION BY v.ano, v.tipo
                                ORDER BY v.distancia_km DESC) n
      FROM vw_pedais v
      WHERE v.tipo IN ('evento','exploracao','local_longo')
    )
    SELECT r.ano, r.tipo, r.d, r.nome, r.km, r.elev, r.vel,
           (SELECT string_agg(c.cidade, ' > ' ORDER BY c.entrada)
              FROM cidades c WHERE c.arquivo = r.arquivo) percurso
    FROM r WHERE n <= 6 ORDER BY ano, tipo, km DESC
""").df().to_csv(index=False))