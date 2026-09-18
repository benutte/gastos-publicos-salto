{{
    config(
        materialized="table"
    )
}}

with limites_historicos as (

    -- O início do calendário é determinado pelo primeiro período encontrado
    -- nas tabelas Silver.
    select
        min(
            make_date(
                exercicio,
                mes,
                1
            )
        ) as primeiro_mes

    from (

        select
            exercicio,
            mes

        from {{ ref('stg_despesas') }}

        union all

        select
            exercicio,
            mes

        from {{ ref('stg_receitas') }}

    ) as periodos_silver

),

calendario_mensal as (

    -- A série contínua inclui todos os meses entre o início histórico e o
    -- mês corrente, mesmo quando um período não possui registros nas fatos.
    select
        cast(serie.dt_mes as date) as dt_mes

    from limites_historicos

    cross join generate_series(
        limites_historicos.primeiro_mes,
        date_trunc('month', current_date),
        interval '1 month'
    ) as serie(dt_mes)

),

atributos_temporais as (

    select
        year(dt_mes) as exercicio,
        month(dt_mes) as mes,
        dt_mes

    from calendario_mensal

),

dimensao_final as (

    select
        -- A chave no formato AAAAMM é estável, legível e ordenável.
        exercicio * 100 + mes as tempo_sk,
        dt_mes,
        exercicio,
        mes,

        case mes
            when 1 then 'Janeiro'
            when 2 then 'Fevereiro'
            when 3 then 'Março'
            when 4 then 'Abril'
            when 5 then 'Maio'
            when 6 then 'Junho'
            when 7 then 'Julho'
            when 8 then 'Agosto'
            when 9 then 'Setembro'
            when 10 then 'Outubro'
            when 11 then 'Novembro'
            when 12 then 'Dezembro'
        end as nm_mes,

        cast(
            ceil(mes / 3.0)
            as integer
        ) as trimestre,

        case
            when mes <= 6 then 1
            else 2
        end as semestre,

        concat(
            cast(exercicio as varchar),
            '-',
            lpad(
                cast(mes as varchar),
                2,
                '0'
            )
        ) as ano_mes

    from atributos_temporais

)

select
    tempo_sk,
    dt_mes,
    exercicio,
    mes,
    nm_mes,
    trimestre,
    semestre,
    ano_mes

from dimensao_final
