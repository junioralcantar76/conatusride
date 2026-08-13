# Visão do projeto

## Contexto

Pedalo e acompanho minha evolução pelo Strava há tempo. O app cumpre bem seu
papel, mas os dados que ele guarda permitem extrair mais do que sua interface
entrega.

## Objetivo

Reunir meu histórico de pedais num ambiente próprio, onde eu possa analisar a
evolução ao longo do tempo e fazer minhas próprias perguntas.

## Perguntas

A definir, a partir da exploração dos dados disponíveis na exportação.

## Escopo — v1

**Dentro**

- Apenas pedais
- Por atividade: local/trajeto, distância, tempo, data e horário, elevação,
  velocidade

**Fora**

- Comparação com outras pessoas
- Streams segundo a segundo
- Automação de coleta

## Critério de sucesso

Todos os pedais numa base própria, com distância, tempo, elevação e locais
visíveis num único lugar ao longo dos meses.

## Requisitos

### Fonte de dados

Carga inicial pela exportação do Strava. A API entra na v2, apenas para os
pedais novos.

### Funcionais

- Inventariar o conteúdo da exportação (arquivos, campos, unidades)
- Importar a exportação
- Normalizar os campos para formato próprio
- Armazenar sem duplicar
- Consultar por período
- Visualizar — a definir após o inventário

### Não funcionais

- Roda local, sem servidor
- Dados privados, fora do repositório
- Código versionado em Git
- Reimportação sem duplicar
- Dado bruto preservado, nunca sobrescrito
- Modelo preparado para receber a API na v2

## Roadmap — v1

1. Repositório inicial: estrutura, README, `.gitignore`
2. Solicitar a exportação no Strava
3. Inventariar o conteúdo
4. Importar e normalizar para o DuckDB
5. Definir as perguntas, a partir do que existe
6. Visualização
