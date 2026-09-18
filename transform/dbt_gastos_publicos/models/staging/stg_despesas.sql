{{
    config(
        materialized="table"
    )
}}

with arquivos_bronze as (

    -- glob() lista inclusive arquivos JSON vazios. Isso é importante porque
    -- o snapshot mais recente de uma partição pode representar uma resposta
    -- válida sem registros.
    select
        file as arquivo_origem,
        regexp_extract(
            file,
            'municipio=([^/]+)',
            1
        ) as municipio,
        try_cast(
            regexp_extract(
                file,
                'exercicio=([0-9]{4})',
                1
            ) as integer
        ) as exercicio,
        try_cast(
            regexp_extract(
                file,
                'mes=([0-9]{2})',
                1
            ) as integer
        ) as mes_particao

    from glob(
        'data/bronze/tce_sp/despesas/'
        'municipio=*/exercicio=*/mes=*/*.json'
    )

),

snapshots_mais_recentes as (

    -- O timestamp UTC faz parte do nome do arquivo. Por isso, MAX aplicado
    -- ao caminho seleciona cronologicamente o snapshot mais recente.
    select
        municipio,
        exercicio,
        mes_particao,
        max(arquivo_origem) as arquivo_origem

    from arquivos_bronze

    group by
        municipio,
        exercicio,
        mes_particao

),

dados_bronze as (

    -- A inferência automática é evitada para preservar os valores originais
    -- da API antes da conversão explícita realizada na camada Silver.
    select
        orgao,
        mes,
        evento,
        nr_empenho,
        id_fornecedor,
        nm_fornecedor,
        dt_emissao_despesa,
        vl_despesa,
        filename as arquivo_origem

    from read_json(
        'data/bronze/tce_sp/despesas/'
        'municipio=*/exercicio=*/mes=*/*.json',
        format = 'array',
        columns = {
            'orgao': 'varchar',
            'mes': 'varchar',
            'evento': 'varchar',
            'nr_empenho': 'varchar',
            'id_fornecedor': 'varchar',
            'nm_fornecedor': 'varchar',
            'dt_emissao_despesa': 'varchar',
            'vl_despesa': 'varchar'
        },
        filename = true,
        hive_partitioning = false
    )

),

snapshots_selecionados as (

    -- O INNER JOIN elimina registros pertencentes a snapshots antigos.
    -- Snapshots vazios continuam sendo reconhecidos na seleção de arquivos,
    -- mas naturalmente não produzem linhas na tabela Silver.
    select
        arquivos.municipio,
        arquivos.exercicio,
        arquivos.mes_particao,
        dados.orgao,
        dados.mes as mes_nome,
        dados.evento,
        dados.nr_empenho,
        dados.id_fornecedor,
        dados.nm_fornecedor,
        dados.dt_emissao_despesa,
        dados.vl_despesa,
        dados.arquivo_origem

    from dados_bronze as dados

    inner join snapshots_mais_recentes as arquivos
        on dados.arquivo_origem = arquivos.arquivo_origem

),

dados_tipados as (

    select
        trim(municipio) as municipio,
        exercicio,
        {{ month_number("mes_nome") }} as mes,
        trim(orgao) as orgao,
        trim(evento) as evento,
        trim(nr_empenho) as nr_empenho,
        trim(id_fornecedor) as id_fornecedor,
        trim(nm_fornecedor) as nm_fornecedor,
        cast(
            try_strptime(
                trim(dt_emissao_despesa),
                '%d/%m/%Y'
            ) as date
        ) as dt_emissao_despesa,
        {{ brazilian_decimal("vl_despesa") }} as vl_despesa,
        arquivo_origem

    from snapshots_selecionados

)

select
    municipio,
    exercicio,
    mes,
    orgao,
    evento,
    nr_empenho,
    id_fornecedor,
    nm_fornecedor,
    dt_emissao_despesa,
    vl_despesa,
    arquivo_origem

from dados_tipados
