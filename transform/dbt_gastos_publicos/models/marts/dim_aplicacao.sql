{{
    config(
        materialized="table"
    )
}}

with aplicacoes_distintas as (

    -- A aplicação fixa chega como código e descrição no mesmo campo.
    select distinct
        ds_cd_aplicacao_fixo

    from {{ ref('stg_receitas') }}

),

aplicacoes_separadas as (

    select
        ds_cd_aplicacao_fixo,

        -- Extrai o código localizado antes do primeiro separador.
        nullif(
            trim(
                split_part(
                    ds_cd_aplicacao_fixo,
                    ' - ',
                    1
                )
            ),
            ''
        ) as cd_aplicacao,

        -- Remove apenas o código e o primeiro separador, preservando
        -- eventuais hífens existentes dentro da descrição.
        nullif(
            trim(
                regexp_replace(
                    ds_cd_aplicacao_fixo,
                    '^[^-]+ - ',
                    ''
                )
            ),
            ''
        ) as nm_aplicacao

    from aplicacoes_distintas

),

dimensao_final as (

    select
        -- O texto original funciona como chave de negócio porque representa
        -- a classificação completa disponibilizada pela API.
        md5(ds_cd_aplicacao_fixo) as aplicacao_sk,
        cd_aplicacao,
        nm_aplicacao,
        ds_cd_aplicacao_fixo

    from aplicacoes_separadas

)

select
    aplicacao_sk,
    cd_aplicacao,
    nm_aplicacao,
    ds_cd_aplicacao_fixo

from dimensao_final
