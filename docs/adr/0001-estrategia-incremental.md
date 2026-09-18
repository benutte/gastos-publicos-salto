# ADR 0001: Estratégia incremental do pipeline

## Status

Aceita.

## Contexto

A API de Transparência do TCE-SP exige uma requisição para cada combinação de dataset, município, exercício e mês.

A camada Bronze preserva respostas JSON como snapshots imutáveis. Uma mesma partição mensal pode possuir vários snapshots gerados por reexecuções.

A Silver seleciona somente o snapshot mais recente de cada partição mensal. A Gold é reconstruída a partir das tabelas Silver.

O manifesto de ingestão registra informações suficientes para uma futura estratégia baseada em watermark:

- dataset;
- município;
- exercício;
- mês;
- status da ingestão;
- quantidade de registros;
- hash SHA-256;
- horário de conclusão;
- caminho do snapshot;
- informações de erro.

O pipeline dbt atual processa:

- 300.149 registros de despesas;
- 14.354 registros de receitas;
- 12 modelos;
- 109 testes de qualidade.

A última execução completa do `dbt build` terminou em aproximadamente cinco segundos.

## Decisão

A estratégia inicial será dividida por camada.

### Bronze

A ingestão continuará incremental.

As execuções recorrentes devem solicitar somente os períodos necessários, priorizando:

- meses do exercício corrente;
- exercício anterior quando configurado;
- períodos solicitados explicitamente para reprocessamento.

Cada execução cria um novo snapshot e não sobrescreve arquivos existentes.

### Silver

Os modelos Silver continuarão materializados como tabelas completas.

Em cada execução, eles:

1. localizam os snapshots Bronze;
2. selecionam o snapshot mais recente de cada partição;
3. aplicam limpeza e tipagem;
4. substituem integralmente as tabelas Silver;
5. executam os testes de qualidade.

### Gold

Dimensões e fatos continuarão materializadas como tabelas completas.

Em cada execução, elas são reconstruídas a partir da Silver e submetidas a testes de:

- obrigatoriedade;
- unicidade;
- integridade referencial;
- valores aceitos;
- reconciliação financeira.

## Justificativa

A reconstrução completa é adequada ao volume atual porque:

- o processamento completo termina em poucos segundos;
- reduz a quantidade de estado operacional;
- evita watermarks inconsistentes;
- simplifica reprocessamentos;
- facilita a recuperação após falhas;
- mantém o pipeline determinístico;
- reduz o risco de registros antigos permanecerem após um snapshot vazio;
- permite validar todo o histórico em cada execução.

Um modelo incremental prematuro criaria complexidade para tratar:

- substituição integral de partições mensais;
- snapshots vazios que devem remover dados anteriores;
- alterações retroativas na API;
- sincronização entre Silver e Gold;
- falhas parciais;
- watermarks por dataset e município;
- execução de testes sobre períodos alterados e históricos.

## Consequências

### Positivas

- operação mais simples;
- reconstrução determinística;
- menor risco de inconsistência;
- recuperação fácil por meio de nova execução;
- testes completos em todas as cargas;
- desenvolvimento mais didático e auditável.

### Negativas

- todos os registros são processados novamente após cada ingestão;
- o custo de execução crescerá com a inclusão de novos municípios;
- a estratégia precisará ser reavaliada quando o volume aumentar.

## Critérios para reavaliação

A materialização incremental deverá ser reavaliada quando ocorrer uma ou mais das seguintes condições:

- inclusão de vários municípios;
- crescimento significativo do histórico;
- aumento relevante no tempo de execução;
- execução completa superior à janela operacional disponível;
- custo de leitura ou armazenamento tornar-se relevante;
- necessidade de atualizações mais frequentes;
- migração do pipeline para infraestrutura remota.

## Estratégia incremental futura

Quando necessária, a Silver deverá utilizar substituição por partição, e não apenas append.

A unidade de substituição será:

```text
dataset + município + exercício + mês
```
