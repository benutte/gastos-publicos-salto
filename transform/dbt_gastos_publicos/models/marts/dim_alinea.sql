{{
    config(
        materialized="table"
    )
}}

with alineas_distintas as (

    -- A alínea chega como código e descrição no mesmo campo.
    select distinct
        ds_alinea

    from {{ ref('stg_receitas') }}

),

alineas_separadas as (

    select
        ds_alinea,

        -- Extrai o código localizado antes do primeiro separador.
        nullif(
            trim(
                split_part(
                    ds_alinea,
                    ' - ',
                    1
                )
            ),
            ''
        ) as cd_alinea,

        -- Remove apenas o código e o primeiro separador, preservando
        -- eventuais hífens existentes dentro da descrição.
        nullif(
            trim(
                regexp_replace(
                    ds_alinea,
                    '^[^-]+ - ',
                    ''
                )
            ),
            ''
        ) as nm_alinea

    from alineas_distintas

),

dimensao_final as (

    select
        -- O texto completo é usado para gerar uma chave estável e evitar
        -- assumir que o código isolado seja globalmente único.
        md5(ds_alinea) as alinea_sk,
        cd_alinea,
        nm_alinea,
        ds_alinea

    from alineas_separadas

)

select
    alinea_sk,
    cd_alinea,
    nm_alinea,
    ds_alinea

from dimensao_final
