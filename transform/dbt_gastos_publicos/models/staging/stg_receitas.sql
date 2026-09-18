{{
    config(
        materialized="table"
    )
}}

with arquivos_bronze as (

    -- glob() identifica todos os arquivos, inclusive snapshots vazios.
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
        'data/bronze/tce_sp/receitas/'
        'municipio=*/exercicio=*/mes=*/*.json'
    )

),

snapshots_mais_recentes as (

    -- O timestamp UTC no nome permite selecionar o snapshot mais recente
    -- com MAX dentro de cada partição mensal.
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

    -- Todos os campos são lidos como texto para que as conversões ocorram
    -- explicitamente e sejam controladas pelo modelo Silver.
    select
        orgao,
        mes,
        ds_fonte_recurso,
        ds_cd_aplicacao_fixo,
        ds_alinea,
        ds_subalinea,
        vl_arrecadacao,
        filename as arquivo_origem

    from read_json(
        'data/bronze/tce_sp/receitas/'
        'municipio=*/exercicio=*/mes=*/*.json',
        format = 'array',
        columns = {
            'orgao': 'varchar',
            'mes': 'varchar',
            'ds_fonte_recurso': 'varchar',
            'ds_cd_aplicacao_fixo': 'varchar',
            'ds_alinea': 'varchar',
            'ds_subalinea': 'varchar',
            'vl_arrecadacao': 'varchar'
        },
        filename = true,
        hive_partitioning = false
    )

),

snapshots_selecionados as (

    -- O relacionamento pelo caminho completo elimina snapshots antigos.
    select
        arquivos.municipio,
        arquivos.exercicio,
        arquivos.mes_particao,
        dados.orgao,
        dados.mes as mes_nome,
        dados.ds_fonte_recurso,
        dados.ds_cd_aplicacao_fixo,
        dados.ds_alinea,
        dados.ds_subalinea,
        dados.vl_arrecadacao,
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
        trim(ds_fonte_recurso) as ds_fonte_recurso,
        trim(ds_cd_aplicacao_fixo) as ds_cd_aplicacao_fixo,
        trim(ds_alinea) as ds_alinea,

        -- Strings vazias são convertidas para NULL porque a inspeção real
        -- confirmou que a subalínea é opcional na fonte.
        nullif(
            trim(ds_subalinea),
            ''
        ) as ds_subalinea,

        {{ brazilian_decimal("vl_arrecadacao") }} as vl_arrecadacao,
        arquivo_origem

    from snapshots_selecionados

)

select
    municipio,
    exercicio,
    mes,
    orgao,
    ds_fonte_recurso,
    ds_cd_aplicacao_fixo,
    ds_alinea,
    ds_subalinea,
    vl_arrecadacao,
    arquivo_origem

from dados_tipados
