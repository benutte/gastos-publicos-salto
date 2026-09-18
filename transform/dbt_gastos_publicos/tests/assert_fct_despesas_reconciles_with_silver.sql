-- A Gold deve preservar a quantidade de registros e o valor total de cada
-- evento existente na Silver. A comparação por evento evita somar conceitos
-- financeiros diferentes, como empenhado, liquidado e pago.

with silver as (

    select
        evento,
        count(*) as quantidade_registros,
        sum(vl_despesa) as valor_total

    from {{ ref('stg_despesas') }}

    group by evento

),

gold as (

    select
        evento,
        count(*) as quantidade_registros,
        sum(vl_despesa) as valor_total

    from {{ ref('fct_despesas') }}

    group by evento

)

select
    coalesce(silver.evento, gold.evento) as evento,
    silver.quantidade_registros as quantidade_silver,
    gold.quantidade_registros as quantidade_gold,
    silver.valor_total as valor_silver,
    gold.valor_total as valor_gold

from silver

full outer join gold
    on silver.evento = gold.evento

where silver.quantidade_registros
      is distinct from gold.quantidade_registros

or silver.valor_total
   is distinct from gold.valor_total
