# Gastos Públicos Municipais

Projeto de engenharia de dados para ingestão, transformação e análise de receitas e despesas municipais disponibilizadas pela API de Transparência do Tribunal de Contas do Estado de São Paulo, TCE-SP.

O projeto utiliza o município de Salto/SP como escopo inicial e foi desenvolvido com finalidade de aprendizado e portfólio, aplicando práticas atuais de engenharia de dados.

## Objetivos

- Construir um pipeline de dados completo e reproduzível.
- Aplicar arquitetura medalhão com camadas Bronze, Silver e Gold.
- Implementar carga histórica e atualização incremental.
- Aplicar testes automatizados e controles de qualidade.
- Criar uma estrutura preparada para múltiplos municípios.
- Disponibilizar dados analíticos para consumo no Power BI.
- Documentar decisões técnicas e boas práticas de engenharia de dados.

## Arquitetura planejada

```text
API TCE-SP
    |
    v
Bronze
JSON bruto, imutável e particionado
    |
    v
Silver
Dados limpos e tipados com dbt
    |
    v
Gold
Modelo dimensional para análise
    |
    v
Power BI
```

## Status atual

As camadas Bronze e Silver estão implementadas e validadas para o município de Salto/SP.

### Camada Bronze

Principais recursos concluídos:

- ingestão mensal de despesas e receitas da API do TCE-SP;
- armazenamento de respostas JSON brutas e imutáveis;
- particionamento por dataset, município, exercício e mês;
- criação de snapshots com timestamp UTC;
- escrita atômica dos arquivos;
- manifesto de execução com metadados, hash SHA-256 e status;
- retry com backoff exponencial para falhas temporárias;
- suporte ao cabeçalho HTTP `Retry-After`;
- CLI para extrações mensais;
- planejamento e execução de backfill histórico;
- continuidade do lote após falhas individuais;
- dry-run para inspeção do plano de backfill;
- testes automatizados sem acesso real à API durante a suíte.

O backfill de janeiro de 2020 a setembro de 2026 foi concluído:

- 162 extrações processadas;
- 158 extrações com dados;
- 4 respostas vazias válidas;
- nenhuma falha.

As respostas vazias correspondem às receitas e despesas de agosto e setembro de 2026. Elas foram preservadas como arquivos JSON contendo uma lista vazia e registradas no manifesto com o status `empty`.

A Bronze possui 88 arquivos físicos por dataset. Algumas partições de 2026 possuem mais de um snapshot devido a reexecuções. Os arquivos anteriores são preservados para auditoria, mas apenas o snapshot mais recente de cada partição mensal é enviado para a Silver.

### Camada Silver

A camada Silver utiliza dbt Core, DuckDB e DuckLake para selecionar, limpar, tipar, testar e materializar os dados da Bronze.

Modelos implementados:

- `stg_despesas`;
- `stg_receitas`.

Volumes materializados:

- 300.149 registros de despesas;
- 14.354 registros de receitas;
- 81 snapshots mensais selecionados por dataset.

Transformações implementadas:

- seleção do snapshot mais recente de cada partição mensal;
- conversão do nome do mês para número inteiro;
- conversão de datas do formato `DD/MM/AAAA` para `DATE`;
- conversão de valores monetários brasileiros para `DECIMAL(18,2)`;
- normalização de strings vazias de subalínea para `NULL`;
- preservação do arquivo Bronze de origem para rastreabilidade;
- desativação do particionamento Hive automático durante a leitura dos JSON;
- preservação de valores financeiros positivos, negativos e iguais a zero.

A inspeção histórica identificou o evento de despesa `Reforço`, que foi incluído nos valores aceitos pelo contrato da Silver.

As receitas possuem 56 grupos de registros com atributos idênticos dentro do mesmo exercício, correspondentes a 70 linhas adicionais. Como a API não fornece chave transacional ou data de arrecadação que permita distinguir duplicidades técnicas de lançamentos legítimos, nenhuma linha é removida automaticamente.

Qualidade e validação:

- 27 testes Python aprovados;
- 23 testes genéricos do dbt;
- 2 testes SQL personalizados;
- 25 testes dbt aprovados;
- `dbt build` concluído com 27 recursos aprovados;
- nenhuma falha, aviso ou recurso ignorado na última validação.

As tabelas atuais estão materializadas no catálogo DuckLake:

```text
gastos_publicos.silver.stg_despesas
gastos_publicos.silver.stg_receitas

```
## Fonte e escopo dos dados

Os dados são obtidos pela API de Transparência do Tribunal de Contas do Estado de São Paulo, TCE-SP.

URL base:

```text
https://transparencia.tce.sp.gov.br/api/json
```

Endpoints utilizados:

```text
/municipios
/despesas/{municipio}/{exercicio}/{mes}
/receitas/{municipio}/{exercicio}/{mes}
```

A API exige uma requisição separada para cada combinação de dataset, município, exercício e mês.

Escopo atual:

- município: Salto/SP;
- identificador utilizado pela API: `salto`;
- período histórico: janeiro de 2020 até o exercício corrente;
- datasets: despesas e receitas municipais;
- granularidade da extração: mensal.

A estrutura foi preparada para permitir a inclusão futura de outros municípios sem alterar o fluxo principal de ingestão.

## Dados de despesas

Campos confirmados na resposta da API:

- `orgao`;
- `mes`;
- `evento`;
- `nr_empenho`;
- `id_fornecedor`;
- `nm_fornecedor`;
- `dt_emissao_despesa`;
- `vl_despesa`.

Valores conhecidos do campo `evento`:

- `Anulação`;
- `Empenhado`;
- `Valor Liquidado`;
- `Valor Pago`.

## Dados de receitas

Campos confirmados na resposta da API:

- `orgao`;
- `mes`;
- `ds_fonte_recurso`;
- `ds_cd_aplicacao_fixo`;
- `ds_alinea`;
- `ds_subalinea`;
- `vl_arrecadacao`.

## Stack técnica

### Implementada na camada Bronze

- Python 3.12;
- HTTPX;
- PyYAML;
- pytest;
- Git;
- GitHub;
- WSL2.

### Planejada para as próximas camadas

- DuckDB;
- DuckLake;
- dbt Core;
- Apache Airflow;
- Docker;
- Power BI;
- OpenRouter.

## Ambiente de desenvolvimento

O projeto foi desenvolvido inicialmente no seguinte ambiente:

- Windows com WSL2;
- Ubuntu 24.04 LTS;
- Python 3.12;
- ambiente virtual Python em `.venv`;
- Docker Desktop instalado;
- código armazenado no sistema de arquivos Linux do WSL.

Diretório utilizado no ambiente de desenvolvimento:

```text
/home/phili/projects/gastos-publicos-salto
```

Manter o projeto no sistema de arquivos Linux, em vez de utilizar `/mnt/c`, reduz problemas de desempenho e permissões ao trabalhar com ferramentas executadas dentro do WSL.

## Estrutura do projeto

```text
gastos-publicos-salto/
├── config/
│   ├── data_contracts/
│   └── ingestion.yml
├── src/
│   ├── __init__.py
│   └── ingestion/
│       ├── __init__.py
│       └── tce_sp/
│           ├── __init__.py
│           ├── __main__.py
│           ├── api_client.py
│           ├── backfill.py
│           ├── batch.py
│           ├── config.py
│           ├── extractor.py
│           ├── manifest.py
│           ├── planner.py
│           └── storage.py
├── tests/
│   ├── test_api_client.py
│   ├── test_batch.py
│   ├── test_extractor.py
│   └── test_planner.py
├── .gitignore
├── pyproject.toml
├── requirements.txt
└── README.md
```

O diretório `data/` é criado localmente durante as execuções e não é versionado no Git.

## Organização da camada Bronze

A camada Bronze preserva as respostas recebidas da API sem aplicar transformações de negócio.

Os arquivos são armazenados utilizando particionamento por:

- dataset;
- município;
- exercício;
- mês.

Estrutura de armazenamento:

```text
data/bronze/tce_sp/{dataset}/municipio={municipio}/exercicio={ano}/mes={mes}/
```

Exemplo:

```text
data/bronze/tce_sp/despesas/municipio=salto/exercicio=2026/mes=01/
```

Os nomes dos arquivos incluem:

- dataset;
- município;
- exercício;
- mês;
- timestamp UTC da extração.

Exemplo:

```text
despesas_salto_2026_01_20260917T154048Z.json
```

Por padrão, uma nova execução cria um novo snapshot. Arquivos já existentes não são sobrescritos.

## Escrita atômica

A gravação dos arquivos Bronze utiliza escrita atômica.

O processo ocorre em duas etapas:

1. o conteúdo é gravado em um arquivo temporário com extensão `.tmp`;
2. após a conclusão da escrita, o arquivo é renomeado para `.json`.

Essa abordagem reduz o risco de arquivos parcialmente gravados caso a execução seja interrompida.

## Manifesto de ingestão

Cada tentativa de extração é registrada no arquivo:

```text
data/metadata/ingestion_manifest.jsonl
```

O manifesto utiliza o formato JSON Lines, com um objeto JSON por linha.

Cada registro pode conter:

- identificador da execução;
- status;
- dataset;
- município;
- exercício;
- mês;
- URL de origem;
- quantidade de registros;
- tamanho do arquivo;
- hash SHA-256;
- início da execução em UTC;
- término da execução em UTC;
- caminho do arquivo criado;
- tipo do erro;
- mensagem do erro.

Status possíveis:

- `success`: resposta válida com registros;
- `empty`: resposta válida sem registros;
- `failed`: falha durante a extração ou gravação.

Quando ocorre uma falha, ela é registrada no manifesto e propagada para o chamador.

Uma extração com falha não cria um arquivo Bronze definitivo.

## Resiliência das requisições

O cliente HTTP possui mecanismos de resiliência para erros temporários.

Status HTTP que podem gerar uma nova tentativa:

- `429`;
- `500`;
- `502`;
- `503`;
- `504`.

A configuração atual utiliza:

- até 4 novas tentativas;
- backoff exponencial;
- suporte ao cabeçalho `Retry-After`;
- timeout separado para conexão e leitura.

Com `max_retries: 4` e `backoff_factor: 2`, os intervalos padrão são:

```text
2, 4, 8 e 16 segundos
```

Quando a resposta contém o cabeçalho `Retry-After`, o tempo informado pelo servidor pode ser utilizado antes da próxima tentativa.

## Configuração

As configurações da ingestão ficam centralizadas no arquivo:

```text
config/ingestion.yml
```

Configuração atual:

```yaml
api:
  base_url: "https://transparencia.tce.sp.gov.br/api/json"
  connect_timeout_seconds: 10
  read_timeout_seconds: 120
  max_retries: 4
  backoff_factor: 2

ingestion:
  municipality: "salto"
  historical_start_year: 2020
  refresh_previous_year: true
  save_empty_responses: true

storage:
  bronze_path: "data/bronze"
  manifest_path: "data/metadata/ingestion_manifest.jsonl"
```

A centralização das configurações evita valores fixos espalhados pelo código e facilita a inclusão futura de outros ambientes e municípios.

## Instalação

Clone o repositório:

```bash
git clone URL_DO_REPOSITORIO
cd gastos-publicos-salto
```

Crie o ambiente virtual:

```bash
python3 -m venv .venv
```

Ative o ambiente virtual:

```bash
source .venv/bin/activate
```

Instale as dependências:

```bash
pip install -r requirements.txt
```

## Execução mensal

Para executar uma extração mensal de despesas:

```bash
python -m src.ingestion.tce_sp \
  --dataset despesas \
  --year 2026 \
  --month 1
```

Para executar uma extração mensal de receitas:

```bash
python -m src.ingestion.tce_sp \
  --dataset receitas \
  --year 2026 \
  --month 1
```

Parâmetros disponíveis:

- `--dataset`: dataset que será extraído;
- `--year`: exercício da extração;
- `--month`: mês da extração;
- `--municipality`: município desejado;
- `--config`: caminho alternativo para o arquivo de configuração.

Os parâmetros `--dataset`, `--year` e `--month` são obrigatórios.

Quando `--municipality` não é informado, o município configurado em `config/ingestion.yml` é utilizado.

## Backfill histórico

O comando de backfill permite executar múltiplos períodos e datasets de forma sequencial.

Exemplo de planejamento sem realizar requisições:

```bash
python -m src.ingestion.tce_sp.backfill \
  --start-year 2020 \
  --dry-run
```

A opção `--dry-run` apresenta o plano de execução sem acessar a API e sem criar arquivos Bronze.

O processamento sequencial foi escolhido para evitar sobrecarregar a API pública do TCE-SP.

Durante a execução:

- cada combinação de dataset e período é processada individualmente;
- falhas são registradas no manifesto;
- uma falha individual não interrompe imediatamente todo o lote;
- um resumo é exibido ao final;
- o processo termina com código diferente de zero se houver alguma falha.

O backfill histórico completo já foi executado. Ele não deve ser repetido desnecessariamente.

## Atualização incremental

O projeto diferencia dois cenários:

### Carga histórica

A primeira execução processa os dados desde janeiro de 2020 até o período corrente.

### Execuções recorrentes

As execuções seguintes devem processar somente os períodos necessários para atualização.

A estratégia planejada considera:

- atualização dos meses do exercício corrente;
- possibilidade de atualizar novamente o exercício anterior;
- preservação de novos snapshots na camada Bronze;
- uso do manifesto para auditoria e controle das execuções.

A automação e o agendamento dessa estratégia serão implementados posteriormente com Apache Airflow.

## Testes automatizados

Para executar a suíte de testes:

```bash
pytest -q
```

Último resultado validado:

```text
13 passed
```

Os testes cobrem:

- rejeição de dataset inválido;
- rejeição de mês inválido;
- rejeição de intervalo de anos inválido;
- planejamento de exercício completo;
- planejamento de exercício parcial;
- processamento de múltiplos datasets;
- processamento de múltiplos períodos;
- continuidade do lote após falha;
- retry após resposta HTTP temporária;
- sucesso depois de uma nova tentativa;
- erro depois do esgotamento das tentativas;
- registro de falha no manifesto;
- garantia de que uma falha não cria arquivo Bronze.

Os testes de comunicação HTTP utilizam `monkeypatch` e não realizam requisições reais à API.

## Controle de versão

O código-fonte, os testes e as configurações são versionados com Git.

Os dados extraídos não são incluídos no repositório.

Itens locais ignorados pelo Git incluem:

- ambiente virtual;
- caches do Python;
- caches do pytest;
- arquivos de dados;
- metadados gerados pelas execuções;
- arquivos temporários.

Essa separação mantém o repositório leve e evita a publicação de grandes volumes de dados operacionais.

## Decisões técnicas

### Preservação do dado bruto

A camada Bronze mantém o conteúdo recebido da API para garantir rastreabilidade e permitir que transformações futuras sejam refeitas sem uma nova extração.

### Snapshots imutáveis

As execuções não sobrescrevem arquivos existentes. Cada nova extração cria um snapshot identificado por timestamp UTC.

### Particionamento mensal

O particionamento acompanha a granularidade da API, que exige uma requisição para cada mês.

### Execução sequencial

As extrações são realizadas sequencialmente para reduzir a pressão sobre a API pública.

### Manifesto em JSON Lines

O formato JSON Lines permite acrescentar novos registros sem reescrever o arquivo inteiro e facilita processamento posterior.

### Hash SHA-256

O hash permite verificar a integridade dos arquivos e pode ser utilizado futuramente para detectar alterações ou duplicidade de conteúdo.

### Configuração externa

Parâmetros operacionais ficam em YAML para que mudanças de município, caminhos, timeouts e política de retry não exijam alterações no código.

### Testes sem acesso à rede

A suíte automatizada substitui as chamadas HTTP reais por respostas controladas, tornando os testes rápidos, determinísticos e independentes da disponibilidade da API.

## Próximas etapas

As próximas etapas planejadas são:

1. concluir a documentação da camada Bronze;
2. revisar a configuração e os contratos de dados;
3. adicionar testes complementares da camada Bronze, quando necessários;
4. criar o catálogo local com DuckDB e DuckLake;
5. iniciar a camada Silver;
6. configurar o projeto dbt Core;
7. criar modelos `stg_` para despesas e receitas;
8. tipar, limpar e padronizar os dados;
9. implementar testes de qualidade com dbt;
10. criar a camada Gold com modelo dimensional;
11. criar fatos e dimensões analíticas;
12. configurar a orquestração com Apache Airflow e Docker;
13. conectar os modelos analíticos ao Power BI;
14. preparar a documentação final para apresentação no GitHub.

## Modelagem planejada

A camada Gold deverá utilizar modelagem dimensional.

Modelos previstos:

- `fct_despesas`;
- `fct_receitas`;
- `dim_municipio`;
- `dim_fornecedor`;
- `dim_tempo`;
- dimensões adicionais identificadas durante a análise dos dados.

A definição final das chaves, granularidades e relacionamentos será realizada depois da exploração e padronização da camada Silver.

## Expansão futura

Depois da validação completa do pipeline para Salto/SP, a estrutura poderá ser expandida para:

- outros municípios do Estado de São Paulo;
- processamento configurável de listas de municípios;
- ingestão de todos os municípios disponibilizados pela API;
- execução em servidor dedicado;
- agendamento recorrente;
- monitoramento operacional;
- enriquecimentos e geração de insights com modelos de IA.

## Finalidade

Este projeto tem finalidade educacional e de portfólio.

O objetivo principal não é apenas analisar gastos públicos municipais, mas demonstrar conhecimentos práticos em:

- ingestão de dados;
- integração com APIs;
- programação em Python;
- arquitetura medalhão;
- armazenamento de dados;
- modelagem dimensional;
- transformação com dbt;
- testes de qualidade;
- resiliência de pipelines;
- observabilidade;
- orquestração;
- versionamento;
- documentação técnica;
- visualização de dados.