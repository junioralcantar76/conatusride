# Registro de decisões

Cada decisão com a razão. Ordem cronológica.

---

## 1. Exportação primeiro, API depois

**Decisão** — A v1 usa apenas a exportação do Strava. A API entra na v2, para
buscar os pedais posteriores à última carga.

**Razão** — A exportação entrega 100% do histórico sem OAuth, sem token
expirando e sem limite de requisição. Misturar autenticação com a carga inicial
gastaria tempo brigando com o OAuth em vez de olhar os dados.

**Consequência** — O modelo de dados já nasce preparado para a API: identificador
estável por pedal e camada de normalização separada da leitura do arquivo, para
que as duas fontes desemboquem no mesmo formato.

---

## 2. DuckDB como armazenamento analítico

**Decisão** — DuckDB.

**Razão** — É feito para consulta analítica sobre histórico, que é exatamente o
uso aqui. Não exige servidor: um arquivo e um `pip install`. Lê CSV e Parquet
direto, o que encaixa com a carga vinda de arquivos.

**Alternativas descartadas** — SQLite (voltado a transação, não análise);
arquivos soltos com pandas (perde SQL).

**Trade-off** — Menos conhecido que SQLite, logo menos material pronto quando
travar.

---

## 3. Python

**Decisão** — Python.

**Razão** — DuckDB, pandas e leitura de GPX são maduros nesse ecossistema.

---

## 4. Dados fora do Git

**Decisão** — Repositório público com o código. Exportação e banco ignorados
pelo Git.

**Razão** — Os pedais contêm coordenadas GPS de locais frequentes. Publicá-las
expõe endereços.

---

## 5. Duas camadas de dado

**Decisão** — `raw` guarda a exportação como veio, intocada. A camada analítica
guarda o dado normalizado.

**Razão** — Se uma regra de normalização mudar, dá para reprocessar tudo a
partir do bruto, sem depender de nova exportação.

---

## 6. Recorte temporal a partir de 2021

**Decisão** — Só entram pedais de 2021 em diante.

**Razão** — Há um único registro de 2018, com quase três anos de lacuna depois
dele. Mantê-lo distorceria qualquer análise temporal. O histórico contínuo
começa em junho de 2021.

---

## 7. Clima incluído no escopo

**Decisão** — Os campos de clima entram na base, embora não estivessem previstos.

**Razão** — Estão preenchidos em 887 dos 961 pedais e não custam nada para
carregar. Se surgir uma pergunta sobre eles, o dado já está lá.

---

## 8. Aproveitar toda coluna com dado

**Decisão** — Entra tudo que estiver preenchido; sai o que estiver 100% vazio.

**Razão** — Evita reprocessar quando surgir uma curiosidade nova. As colunas
vazias são de outros esportes (natação, escalada, musculação) e não se aplicam.

**Ressalva** — "Preenchido" não é o mesmo que "com dado". O Strava grava zero
onde não havia sensor: as 318 cadências e 314 das 320 frequências cardíacas são
zeros. Cadência foi descartada; FC ficou, com valor real em apenas 6 pedais.

---

## 9. Nomes de coluna em minúsculo com unidade no sufixo

**Decisão** — `distancia_m`, `velocidade_media_kmh`, `ganho_elevacao_m`.

**Razão** — Os nomes originais têm acento, espaço e ponto (`Velocidade máx.`,
`Distância.1`), o que atrapalha em SQL. E o CSV traz colunas duplicadas em
unidades diferentes — `Distância` em km com vírgula, `Distância.1` em metros.
O sufixo elimina a ambiguidade.

---

## 10. Recriar a tabela a cada importação

**Decisão** — O script apaga e recria a tabela `pedais` toda vez que roda.

**Razão** — A fonte é um arquivo único e completo. Recriar é mais simples e mais
seguro do que mesclar registros, e garante idempotência sem lógica extra.

**Revisar quando** — A API entrar na v2. Aí passa a haver carga incremental e
essa estratégia não serve mais.

---

## 11. O projeto acompanha desempenho, mas não é sobre otimizá-lo

**Decisão** — As perguntas do projeto são sobre enxergar o conjunto e ligar os
números ao contexto de vida, não sobre maximizar métricas de treino.

**Razão** — Nunca houve pedal para competir. As médias incluem paradas para
comer, hidratar e resolver problemas mecânicos, e pedalar em grupo muda o ritmo.
Tratar essas médias como indicador de forma levaria a conclusões erradas.

**Consequência** — Existe um documento de fases (`fases.md`) registrando o
contexto ano a ano. É ele que dá sentido às variações nos dados.
