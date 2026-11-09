## 23. Elevação implausível vira nulo

**Decisão** — No `importar.py`, ganho de elevação acima de **30 m por km** é
descartado (vira nulo). O pedal continua na base com distância, tempo e o resto.

**Razão** — O altímetro barométrico descalibra e inventa centenas de metros. O
caso que denunciou o problema foi "Lago - BR116" (11/12/2023): 2.902 m em 29 km,
ou 100 m/km. Os outros dois pedais na mesma rota, com a mesma distância, deram
98 e 156 m. Ele estava aparecendo como recorde de elevação do histórico.

**Por que 30** — O pedal mais íngreme legítimo é a Trilha da Banana em Baturité,
com 15,6 m/km. O corte dá o dobro de margem, cabe um evento de montanha futuro e
fica muito longe do erro.

**Por que nulo e não corrigido** — Sem outra medida do mesmo trajeto não há como
saber o valor certo, e estimar seria pior do que assumir a falta.

**Por que regra e não correção manual** — A regra pegou três casos em 974
pedais, e só um tinha sido notado. Os outros dois — "Rio Mar Papicu"
(05/09/2022, 14,4 km) e "Cambeba" (03/10/2022, 25,5 km) — são pedais urbanos
curtos em Fortaleza, que é plano; passavam despercebidos e distorciam os totais
do ano. Correção manual só encontra o que chama atenção.

**Efeito** — O total de 2023 caiu de 52.315 para 49.394 m de elevação.

**Não editar `data/raw/`** — A exportação fica intocada (decisão 5). Correções
vão no código ou, se um dia forem necessárias caso a caso, num arquivo em
`docs/` — que sobrevive a uma nova exportação.
