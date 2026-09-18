-- Despesas não apresentaram duplicidades exatas durante o perfil histórico.
-- O teste protege essa característica nas próximas atualizações.

select
    municipio,
    exercicio,
    mes,
    orgao,
    evento,
    nr_empenho,
    id_fornecedor,
    nm_fornecedor,
    dt_emissao_despesa,
    vl_despesa,
    count(*) as quantidade

from {{ ref('stg_despesas') }}

group by
    municipio,
    exercicio,
    mes,
    orgao,
    evento,
    nr_empenho,
    id_fornecedor,
    nm_fornecedor,
    dt_emissao_despesa,
    vl_despesa

having count(*) > 1
