{% macro month_number(column_name) %}
    case trim({{ column_name }})
        when 'Janeiro' then 1
        when 'Fevereiro' then 2
        when 'Março' then 3
        when 'Abril' then 4
        when 'Maio' then 5
        when 'Junho' then 6
        when 'Julho' then 7
        when 'Agosto' then 8
        when 'Setembro' then 9
        when 'Outubro' then 10
        when 'Novembro' then 11
        when 'Dezembro' then 12
        else null
    end
{% endmacro %}
