## 31. Ids de 64 bits do Strava — pendente até junho de 2027

**O aviso** — Comunicado da equipe de API do Strava, novembro de 2026: depois de
**1º de junho de 2027**, os identificadores de atividades e atletas podem vir
como inteiros de 64 bits. Passam a devolver também um campo `id_str`, com o
mesmo valor em texto, e recomendam usá-lo.

**Situação do projeto** — Quase tudo já aguenta:

- Python não tem limite de tamanho para inteiros.
- No DuckDB a coluna `id` é BIGINT, que é exatamente 64 bits.
- Os ids de hoje já têm 11 dígitos (o pedal de outubro de 2026 é
  `20930238790`), ou seja, já passaram de 32 bits há tempos e nada quebrou.

**O ponto frágil** — `importar.py`. Se a coluna de id vier com algum valor
vazio no CSV, o pandas lê a coluna inteira como decimal, e aí ids acima de 16
dígitos perdem precisão: viram outro número, sem erro nenhum. Hoje não acontece
porque nunca falta id, mas é falha silenciosa.

**A correção, quando for feita** — ler a coluna de id como texto
(`dtype={"ID da atividade": "string"}`) e converter para inteiro depois. No
`atualizar.py`, usar `id_str` quando o campo existir, com `int(a["id"])` como
reserva.

**Cuidado futuro** — Se algum dia o id for embutido nas páginas, o JavaScript só
guarda inteiros com segurança até 16 dígitos. Hoje as telas não usam o id, então
não há problema.

**Prazo** — Fazer até maio de 2027. Decidido em 17/11/2026 adiar, já que não há
urgência e a correção é pequena.
