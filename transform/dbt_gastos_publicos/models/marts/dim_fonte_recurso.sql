{{
    config(
        materialized="table"
    )
}}

with fontes_distintas as (

    -- A fonte de recurso chega como código e descrição no mesmo campo.
    -- A dimensão terá uma linha para cada valor distinto observado.
    select distinct
        ds_fonte_recurso

    from {{ ref('stg_receitas') }}

),

fontes_separadas as (

    select
        ds_fonte_recurso,

        -- O código corresponde ao conteúdo anterior ao primeiro separador.
        nullif(
            trim(
                split_part(
                    ds_fonte_recurso,
                    ' - ',
                    1
                )
            ),
            ''
        ) as cd_fonte_recurso,

        -- A expressão remove somente o código e o primeiro separador.
        -- Isso preserva outros hífens que possam existir na descrição.
        nullif(
            trim(
                regexp_replace(
                    ds_fonte_recurso,
                    '^[^-]+ - ',
                    ''
                )
            ),
            ''
        ) as nm_fonte_recurso

    from fontes_distintas

),

dimensao_final as (

    select
        -- O valor original é usado como chave de negócio porque representa
        -- exatamente a classificação disponibilizada pela API.
        md5(ds_fonte_recurso) as fonte_recurso_sk,
        cd_fonte_recurso,
        nm_fonte_recurso,
        ds_fonte_recurso

    from fontes_separadas

)

select
    fonte_recurso_sk,
    cd_fonte_recurso,
    nm_fonte_recurso,
    ds_fonte_recurso

from dimensao_final
