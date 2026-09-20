{{
    config(
        materialized="table"
    )
}}

with receitas_com_chaves_dimensionais as (

    select
        municipio.municipio_sk,
        orgao.orgao_sk,
        receitas.exercicio * 100 + receitas.mes as tempo_sk,
        fonte.fonte_recurso_sk,
        aplicacao.aplicacao_sk,
        alinea.alinea_sk,

        -- Receitas sem subalínea são relacionadas ao membro especial -1,
        -- evitando uma chave estrangeira nula na tabela fato.
        coalesce(
            subalinea.subalinea_sk,
            '-1'
        ) as subalinea_sk,

        receitas.exercicio,
        receitas.mes,
        receitas.vl_arrecadacao,

        -- Os atributos originais são preservados para rastreabilidade e
        -- investigação de possíveis mudanças nas classificações da fonte.
        receitas.orgao as nm_orgao_origem,
        receitas.ds_fonte_recurso,
        receitas.ds_cd_aplicacao_fixo,
        receitas.ds_alinea,
        receitas.ds_subalinea,
        receitas.arquivo_origem

    from {{ ref('stg_receitas') }} as receitas

    inner join {{ ref('dim_municipio') }} as municipio
        on receitas.municipio = municipio.municipio

    inner join {{ ref('dim_orgao') }} as orgao
        on receitas.municipio = orgao.municipio
        and receitas.orgao = orgao.nm_orgao

    inner join {{ ref('dim_fonte_recurso') }} as fonte
        on receitas.ds_fonte_recurso = fonte.ds_fonte_recurso

    inner join {{ ref('dim_aplicacao') }} as aplicacao
        on receitas.ds_cd_aplicacao_fixo
           = aplicacao.ds_cd_aplicacao_fixo

    inner join {{ ref('dim_alinea') }} as alinea
        on receitas.ds_alinea = alinea.ds_alinea

    left join {{ ref('dim_subalinea') }} as subalinea
        on receitas.ds_subalinea = subalinea.ds_subalinea

),

receitas_com_impressao_digital as (

    select
        *,

        -- A impressão digital identifica o conteúdo financeiro da receita,
        -- mas pode se repetir porque a fonte possui ocorrências idênticas.
        md5(
            concat_ws(
                '||',
                municipio_sk,
                orgao_sk,
                cast(tempo_sk as varchar),
                fonte_recurso_sk,
                aplicacao_sk,
                alinea_sk,
                subalinea_sk,
                cast(vl_arrecadacao as varchar)
            )
        ) as receita_fingerprint

    from receitas_com_chaves_dimensionais

),

receitas_com_ocorrencia as (

    select
        *,

        -- O sequencial distingue ocorrências idênticas sem eliminar linhas.
        -- Ele é uma identificação técnica e não representa uma chave
        -- transacional disponibilizada pela API.
        row_number() over (
            partition by receita_fingerprint
            order by arquivo_origem
        ) as nr_ocorrencia

    from receitas_com_impressao_digital

),

dimensao_final as (

    select
        -- A chave técnica combina a impressão digital com o número da
        -- ocorrência, permitindo unicidade mesmo quando há linhas idênticas.
        md5(
            concat_ws(
                '||',
                receita_fingerprint,
                cast(nr_ocorrencia as varchar)
            )
        ) as receita_sk,

        receita_fingerprint,
        nr_ocorrencia,
        municipio_sk,
        orgao_sk,
        tempo_sk,
        fonte_recurso_sk,
        aplicacao_sk,
        alinea_sk,
        subalinea_sk,
        exercicio,
        mes,
        vl_arrecadacao,
        nm_orgao_origem,
        ds_fonte_recurso,
        ds_cd_aplicacao_fixo,
        ds_alinea,
        ds_subalinea

    from receitas_com_ocorrencia

)

select
    receita_sk,
    receita_fingerprint,
    nr_ocorrencia,
    municipio_sk,
    orgao_sk,
    tempo_sk,
    fonte_recurso_sk,
    aplicacao_sk,
    alinea_sk,
    subalinea_sk,
    exercicio,
    mes,
    vl_arrecadacao,
    nm_orgao_origem,
    ds_fonte_recurso,
    ds_cd_aplicacao_fixo,
    ds_alinea,
    ds_subalinea

from dimensao_final
