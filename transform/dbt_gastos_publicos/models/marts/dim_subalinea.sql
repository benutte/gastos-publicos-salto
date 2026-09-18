{{
    config(
        materialized="table"
    )
}}

with subalineas_distintas as (

    -- Apenas valores preenchidos originam membros regulares da dimensão.
    -- Registros sem subalínea serão relacionados ao membro especial -1.
    select distinct
        ds_subalinea

    from {{ ref('stg_receitas') }}

    where ds_subalinea is not null

),

subalineas_separadas as (

    select
        ds_subalinea,

        -- Extrai o código localizado antes do primeiro separador.
        nullif(
            trim(
                split_part(
                    ds_subalinea,
                    ' - ',
                    1
                )
            ),
            ''
        ) as cd_subalinea,

        -- Remove somente o código e o primeiro separador, preservando
        -- eventuais hífens existentes na descrição.
        nullif(
            trim(
                regexp_replace(
                    ds_subalinea,
                    '^[^-]+ - ',
                    ''
                )
            ),
            ''
        ) as nm_subalinea

    from subalineas_distintas

),

membros_regulares as (

    select
        -- O prefixo evita qualquer possibilidade de colisão conceitual com
        -- a chave especial usada para representar valores não informados.
        md5(
            concat(
                'SUBALINEA||',
                ds_subalinea
            )
        ) as subalinea_sk,

        cd_subalinea,
        nm_subalinea,
        ds_subalinea,
        false as is_nao_informada

    from subalineas_separadas

),

membro_nao_informado as (

    -- O membro especial mantém a integridade referencial das receitas cuja
    -- subalínea não foi preenchida pela fonte.
    select
        '-1' as subalinea_sk,
        cast(null as varchar) as cd_subalinea,
        'Não informada' as nm_subalinea,
        'Não informada' as ds_subalinea,
        true as is_nao_informada

),

dimensao_final as (

    select
        subalinea_sk,
        cd_subalinea,
        nm_subalinea,
        ds_subalinea,
        is_nao_informada

    from membros_regulares

    union all

    select
        subalinea_sk,
        cd_subalinea,
        nm_subalinea,
        ds_subalinea,
        is_nao_informada

    from membro_nao_informado

)

select
    subalinea_sk,
    cd_subalinea,
    nm_subalinea,
    ds_subalinea,
    is_nao_informada

from dimensao_final
