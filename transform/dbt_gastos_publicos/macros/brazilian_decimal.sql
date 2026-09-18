{% macro brazilian_decimal(column_name) %}
    try_cast(
        replace(
            replace(trim({{ column_name }}), '.', ''),
            ',',
            '.'
        ) as decimal(18, 2)
    )
{% endmacro %}
