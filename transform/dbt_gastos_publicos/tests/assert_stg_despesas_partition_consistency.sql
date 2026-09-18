-- O exercício e o mês tipados na Silver devem corresponder aos valores
-- presentes no caminho do snapshot Bronze que originou cada registro.

select
    municipio,
    exercicio,
    mes,
    arquivo_origem

from {{ ref('stg_despesas') }}

where exercicio is distinct from try_cast(
    regexp_extract(
        arquivo_origem,
        'exercicio=([0-9]{4})',
        1
    ) as integer
)

or mes is distinct from try_cast(
    regexp_extract(
        arquivo_origem,
        'mes=([0-9]{2})',
        1
    ) as integer
)
