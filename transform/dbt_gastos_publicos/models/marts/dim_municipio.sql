{{
    config(
        materialized="table"
    )
}}

with municipios_origem as (

    -- A dimensão é compartilhada pelas duas fatos. Por isso, reunimos os
    -- municípios encontrados tanto em despesas quanto em receitas.
    select distinct
        municipio

    from {{ ref('stg_despesas') }}

    union

    select distinct
        municipio

    from {{ ref('stg_receitas') }}

),

municipios_enriquecidos as (

    select
        municipio,

        -- O hash da chave de negócio produz uma chave substituta estável.
        md5(municipio) as municipio_sk,

        -- O projeto atual possui somente Salto. A estrutura CASE torna
        -- explícito o enriquecimento local e permite ampliar o mapeamento
        -- quando outros municípios forem adicionados.
        case
            when municipio = 'salto' then 'Salto'
            else municipio
        end as nm_municipio,

        case
            when municipio = 'salto' then 'SP'
            else null
        end as uf

    from municipios_origem

)

select
    municipio_sk,
    municipio,
    nm_municipio,
    uf

from municipios_enriquecidos
