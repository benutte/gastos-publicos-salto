{{
    config(
        materialized="table"
    )
}}

with despesas_com_chaves_de_negocio as (

    select
        despesas.*,

        -- Para pessoas físicas, o identificador fornecido pela API não
        -- distingue todas as pessoas. A mesma regra da dim_fornecedor deve
        -- ser aplicada aqui para garantir o relacionamento correto.
        case
            when id_fornecedor like 'PESSOA FÍSICA -%'
                then concat_ws(
                    '||',
                    id_fornecedor,
                    nm_fornecedor
                )
            else id_fornecedor
        end as fornecedor_bk

    from {{ ref('stg_despesas') }} as despesas

),

despesas_com_chaves_dimensionais as (

    select
        -- A impressão digital utiliza os atributos que identificam o
        -- conteúdo do lançamento. O arquivo de origem não participa para
        -- que a chave permaneça estável após uma nova extração do período.
        md5(
            concat_ws(
                '||',
                despesas.municipio,
                cast(despesas.exercicio as varchar),
                cast(despesas.mes as varchar),
                despesas.orgao,
                despesas.evento,
                despesas.nr_empenho,
                despesas.id_fornecedor,
                despesas.nm_fornecedor,
                cast(despesas.dt_emissao_despesa as varchar),
                cast(despesas.vl_despesa as varchar)
            )
        ) as despesa_sk,

        municipio.municipio_sk,
        orgao.orgao_sk,
        despesas.exercicio * 100 + despesas.mes as tempo_sk,
        fornecedor.fornecedor_sk,

        despesas.exercicio,
        despesas.mes,
        despesas.evento,
        despesas.nr_empenho,
        despesas.dt_emissao_despesa,
        despesas.vl_despesa,

        -- Os atributos originais são mantidos como dimensões degeneradas e
        -- campos de auditoria, mesmo existindo dimensões relacionadas.
        despesas.id_fornecedor,
        despesas.nm_fornecedor as nm_fornecedor_origem,
        despesas.arquivo_origem

    from despesas_com_chaves_de_negocio as despesas

    inner join {{ ref('dim_municipio') }} as municipio
        on despesas.municipio = municipio.municipio

    inner join {{ ref('dim_orgao') }} as orgao
        on despesas.municipio = orgao.municipio
        and despesas.orgao = orgao.nm_orgao

    inner join {{ ref('dim_fornecedor') }} as fornecedor
        on despesas.fornecedor_bk = fornecedor.fornecedor_bk

)

select
    despesa_sk,
    municipio_sk,
    orgao_sk,
    tempo_sk,
    fornecedor_sk,
    exercicio,
    mes,
    evento,
    nr_empenho,
    dt_emissao_despesa,
    vl_despesa,
    id_fornecedor,
    nm_fornecedor_origem,
    arquivo_origem

from despesas_com_chaves_dimensionais
