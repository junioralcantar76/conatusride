# Painel — escopo

Definido em conjunto, agosto de 2026. Substitui a estrutura anterior de páginas
narrativas (uma por ano, com fase e frase em destaque).

## Por que mudou

As primeiras páginas foram construídas como **narrativa**: pouca informação por
tela, texto grande, uma história contada em ordem. Ficaram bonitas e não eram o
que eu uso.

O que eu quero é **instrumento**: filtrar, cruzar, comparar, consultar. Densidade
de informação e comparação lado a lado, como no BI que eu mantinha antes.

Os dois podem coexistir, mas o instrumento vem primeiro — é o que se usa no dia
a dia. O texto das fases entra depois, como camada de contexto sobre os números.

## Os seis blocos

### 1. Visão geral do ano

Dez indicadores:

- Km pedalados
- Número de atividades
- Horas sobre a bike
- Elevação acumulada
- Velocidade média
- Maior pedalada
- Maior ganho de elevação
- Média de km por atividade
- Dias pedalados (distinto de atividades: dois pedais no mesmo dia contam 1 dia)
- Sequência de pedaladas

Os mesmos indicadores devem responder ao recorte escolhido — ano, mês ou semana.

### 2. Evolução mensal

Tabela, não gráfico:

| Mês | Km | Pedais | Horas | Elevação |
|---|---|---|---|---|
| Janeiro | 320 km | 8 | 14h | 3.200 m |

### 3. Histórico completo

Uma linha por atividade, com todos os campos: data, distância, tempo,
velocidade, elevação, frequência cardíaca, potência, localização, nome.

Filtros combináveis. Exemplos:

- 2026 → agosto → acima de 50 km
- todas as pedaladas acima de 100 km

### 4. Recordes pessoais

Calculados automaticamente:

- Maior distância
- Maior velocidade média
- Maior elevação
- Maior tempo pedalando
- Maior distância em um mês
- Maior distância em um ano
- Maior número de atividades
- Melhor sequência de dias
- Pedal mais longo de todos os tempos

### 5. Comparação entre anos

Deve responder: estou pedalando mais este ano? Qual foi meu melhor ano? Em qual
mês normalmente pedalo mais? Minha distância média está aumentando?

### 6. Mapa da história

Todas as rotas já feitas, com seleção por ano ou todos os anos. Visualizar
literalmente onde já pedalei.

## Ordem de construção

1. **Histórico filtrável** — é a fundação. Com os dados no navegador e os
   filtros funcionando, os demais blocos são consultas sobre a mesma base.
2. Visão do ano — os dez indicadores, respondendo ao filtro
3. Evolução mensal
4. Recordes
5. Comparação entre anos
6. Mapa — por último, é o mais pesado

## Consequência técnica

Filtro combinável exige os dados **no navegador**, não apenas o resultado
pré-calculado. Os 961 pedais vão embutidos no HTML e a página recalcula na hora.
São cerca de 60 KB — irrelevante.

Isso muda a arquitetura anterior, em que cada página trazia números já somados.

## Ressalvas conhecidas

- **Modalidade** é uma só — o Strava classificou as 961 atividades como
  "Pedalada", sem distinção. O que faz sentido no lugar é classificar o **piso**:
  estrada, trilha ou misto. Ver abaixo.
- **Frequência cardíaca** existe em apenas 6 pedais: o Strava gravou zero onde
  não havia sensor. Pretendo voltar a usar a cinta, então os campos ficam no
  painel e passam a ter valor nos pedais novos. Os antigos seguem nulos.
- **Potência fica fora do painel.** Os watts estimados continuam na base (956
  pedais), mas não são exibidos. São cálculo do Strava a partir de peso e
  elevação, não medição. Nota: medidor de cadência não resolve isso — cadência
  é rotação por minuto, potência exige medidor de potência, outro equipamento.
  Para acompanhar esforço, a cinta cardíaca informa mais.
- **Sequência** ainda não está definida — dias seguidos ou semanas seguidas com
  pelo menos um pedal. A segunda é mais fiel ao padrão real, já que raramente
  pedalo dois dias seguidos.

## Piso: estrada, trilha ou misto — a implementar

O dado já existe: a coluna `distancia_terra_m` do Strava, presente em 881 dos
961 pedais.

Cuidado conhecido: há um piso de 13 a 15% de "terra" em quase tudo, inclusive em
pedal urbano — é ciclovia e via não pavimentada da cidade sendo classificada
assim. O número absoluto não vale; o contraste sim.

Faixas de partida, a calibrar contra pedais conhecidos:

| Piso | % de terra |
|---|---|
| estrada | até ~15% |
| misto | 15 a 50% |
| trilha | acima de ~50% |

Referências reais: Trilha Trairi 50%, Ceará–Paraíba 41%, Jurema–Baixio 36%,
Triunfo 29%, treinos urbanos e Casa Caiada 13 a 15%.

## Página inicial

Aprovada em protótipo, e mantida: ano corrente, km do ano em destaque, quatro
números de apoio, gráfico mensal com o mês atual destacado e os meses futuros
apagados. Clicar num mês abre o detalhe.

Meta, turno, tipos e cidades saíram dela — vão para as páginas específicas.

## Estado em 17/08

**Feito** — protótipo da página inicial (ano corrente) aprovado; protótipo do
histórico filtrável aprovado; classificação em três campos aplicada.

**A fazer** — `src/gerar_site.py` ainda usa os tipos antigos (`pedal_curto`,
`pedal_medio`, `pedal_longo`) e vai quebrar com a classificação nova. Precisa
ser atualizado antes de gerar o site.

**Ajuste pedido** — no histórico, mostrar o tempo como `4h41` em vez de minutos.

**A definir juntos** — quais campos de classificação ficam. Foram acrescentados
mais campos e regras do que o combinado. Ver decisão 19.

## Em aberto

- Comparação de anos na página inicial: entra ou fica só no bloco 5? Comparar km
  ou elevação? Agosto de 2026 tem 278 km e 2.376 m — fraco em distância, o mais
  duro do ano em terreno.
- Onde entram as fases e o texto de contexto.
- Recorte de semana: navegar a partir da atual ou escolher numa lista.

## Registro

Esta é uma construção. Se algo não funcionar, muda — e o histórico das decisões
fica aqui.
