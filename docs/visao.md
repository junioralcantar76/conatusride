# Visão do projeto

## Contexto

Pedalo e acompanho minha evolução pelo Strava há tempo. O app cumpre bem seu
papel, mas os dados que ele guarda permitem extrair mais do que sua interface
entrega.

## Objetivo

Reunir meu histórico de pedais num ambiente próprio, onde eu possa analisar a
evolução ao longo do tempo e fazer minhas próprias perguntas.

## Propósito

O projeto acompanha desempenho — se houve evolução, se houve queda — mas o
número não é cobrança. Ele serve para **ligar o que aconteceu nos dados ao que
estava acontecendo na vida**. Uma queda de frequência em 2026 só significa algo
quando se sabe que foi o ano em que voltei a estudar à noite.

Nunca houve pedal para competir. Sempre pedais com amigos, com contratempos no
caminho — pneu furado, corrente quebrada, parada para comer e hidratar. Isso
está dentro das médias e não deve ser lido como perda de forma.

Busco qualidade e prazer em pedalar. Evoluir, sim; virar quase profissional,
não.

Ver [fases.md](fases.md) para o contexto ano a ano.

## Perguntas

1. Como meus pedais mudaram ao longo dos anos — distância, frequência, ritmo?
2. Onde eu pedalo, e como isso mudou?
3. Quanto acumulei — km, elevação, horas?
4. Quais foram os pedais marcantes?

Em aberto — a exploração continua e novas perguntas podem entrar.

## Escopo — v1

**Dentro**

- Apenas pedais, de 2021 em diante
- Dados de resumo por atividade: distância, tempo, velocidade, elevação,
  inclinação, calorias, watts estimados, nome do trajeto
- Dados de clima (presentes em 887 pedais)

**Fora**

- Comparação com outras pessoas
- Streams segundo a segundo (arquivos GPX/FIT)
- Automação de coleta

## Critério de sucesso

Todos os pedais numa base própria, com distância, tempo, elevação e locais
visíveis num único lugar ao longo dos meses.

## Requisitos

### Fonte de dados

Carga inicial pela exportação do Strava. A API entra na v2, apenas para os
pedais novos.

### Funcionais

- Inventariar o conteúdo da exportação — **concluído**
- Importar a exportação — **concluído**
- Normalizar os campos para formato próprio — **concluído**
- Armazenar sem duplicar — **concluído**
- Consultar por período
- Visualizar

### Não funcionais

- Roda local, sem servidor
- Dados privados, fora do repositório
- Código versionado em Git
- Reimportação sem duplicar
- Dado bruto preservado, nunca sobrescrito
- Modelo preparado para receber a API na v2

## Roadmap — v1

1. ~~Repositório inicial~~ — concluído
2. ~~Solicitar a exportação no Strava~~ — concluído
3. ~~Inventariar o conteúdo~~ — concluído
4. ~~Importar e normalizar para o DuckDB~~ — concluído
5. Definir as perguntas — em andamento; exploração continua
6. Visualização

## Base atual

961 pedais, de junho de 2021 a agosto de 2026.
Cerca de 29.700 km e 155.400 m de ganho de elevação.
