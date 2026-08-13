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
