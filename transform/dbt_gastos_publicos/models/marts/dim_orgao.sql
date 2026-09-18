{{
    config(
        materialized="table"
    )
}}

with orgaos_origem as (

    -- Reunimos os órgãos encontrados nos dois datasets para construir uma
    -- dimensão conformada, compartilhada pelas duas tabelas fato.
    select distinct
        municipio,
        orgao

    from {{ ref('stg_despesas') }}

    union

    select distinct
        municipio,
        orgao

    from {{ ref('stg_receitas') }}

),

orgaos_com_chaves as (

    select
        -- A chave inclui município e órgão porque nomes iguais podem existir
        -- em municípios diferentes quando o projeto for expandido.
        md5(
            concat_ws(
                '||',
                municipio,
                orgao
            )
        ) as orgao_sk,

        md5(municipio) as municipio_sk,
        municipio,
        orgao as nm_orgao

    from orgaos_origem

)

select
    orgao_sk,
    municipio_sk,
    municipio,
    nm_orgao

from orgaos_com_chaves
