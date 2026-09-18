{{
    config(
        materialized="table"
    )
}}

with fornecedores_classificados as (

    select
        id_fornecedor,
        nm_fornecedor,
        dt_emissao_despesa,

        case
            when id_fornecedor like 'CNPJ -%' then 'CNPJ'
            when id_fornecedor like 'PESSOA FÍSICA -%' then 'PESSOA FÍSICA'
            when id_fornecedor like 'IDENTIFICAÇÃO ESPECIAL%'
                then 'IDENTIFICAÇÃO ESPECIAL'
            when id_fornecedor like 'INSCRIÇÃO GENÉRICA%'
                then 'INSCRIÇÃO GENÉRICA'
            when id_fornecedor like 'INTERNACIONAL%'
                then 'INTERNACIONAL'
            else 'OUTRO'
        end as tipo_fornecedor

    from {{ ref('stg_despesas') }}

),

fornecedores_com_chave as (

    select
        id_fornecedor,
        nm_fornecedor,
        dt_emissao_despesa,
        tipo_fornecedor,

        -- Para pessoa física, o identificador da API não é suficiente para
        -- distinguir pessoas diferentes. Por isso, o nome integra a chave de
        -- negócio apenas nessa categoria.
        case
            when tipo_fornecedor = 'PESSOA FÍSICA'
                then concat_ws(
                    '||',
                    id_fornecedor,
                    nm_fornecedor
                )
            else id_fornecedor
        end as fornecedor_bk

    from fornecedores_classificados

),

ocorrencias_por_nome_e_data as (

    -- A contagem será usada para desempatar nomes diferentes encontrados
    -- na data mais recente de um fornecedor.
    select
        fornecedor_bk,
        id_fornecedor,
        tipo_fornecedor,
        nm_fornecedor,
        dt_emissao_despesa,
        count(*) as quantidade_ocorrencias

    from fornecedores_com_chave

    group by
        fornecedor_bk,
        id_fornecedor,
        tipo_fornecedor,
        nm_fornecedor,
        dt_emissao_despesa

),

nomes_ordenados as (

    select
        fornecedor_bk,
        id_fornecedor,
        tipo_fornecedor,
        nm_fornecedor,
        dt_emissao_despesa,
        quantidade_ocorrencias,

        row_number() over (
            partition by fornecedor_bk

            order by
                dt_emissao_despesa desc,
                quantidade_ocorrencias desc,
                nm_fornecedor asc
        ) as ordem_nome

    from ocorrencias_por_nome_e_data

),

nomes_atuais as (

    select
        fornecedor_bk,
        id_fornecedor,
        tipo_fornecedor,
        nm_fornecedor as nm_fornecedor_atual

    from nomes_ordenados

    where ordem_nome = 1

),

historico_fornecedor as (

    select
        fornecedor_bk,
        min(dt_emissao_despesa) as primeira_dt_observada,
        max(dt_emissao_despesa) as ultima_dt_observada,
        count(distinct nm_fornecedor) as qtd_nomes_observados

    from fornecedores_com_chave

    group by fornecedor_bk

),

dimensao_final as (

    select
        -- A chave substituta é estável porque deriva da chave de negócio
        -- construída segundo as regras específicas de cada tipo.
        md5(nomes.fornecedor_bk) as fornecedor_sk,
        nomes.fornecedor_bk,
        nomes.id_fornecedor,
        nomes.tipo_fornecedor,
        nomes.nm_fornecedor_atual,
        historico.primeira_dt_observada,
        historico.ultima_dt_observada,
        historico.qtd_nomes_observados

    from nomes_atuais as nomes

    inner join historico_fornecedor as historico
        on nomes.fornecedor_bk = historico.fornecedor_bk

)

select
    fornecedor_sk,
    fornecedor_bk,
    id_fornecedor,
    tipo_fornecedor,
    nm_fornecedor_atual,
    primeira_dt_observada,
    ultima_dt_observada,
    qtd_nomes_observados

from dimensao_final
