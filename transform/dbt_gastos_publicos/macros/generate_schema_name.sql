{% macro generate_schema_name(custom_schema_name, node) -%}

    {#
        Quando um modelo possui schema configurado, usamos esse nome
        diretamente, sem concatená-lo com o schema padrão do perfil.
    #}

    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}

{%- endmacro %}
