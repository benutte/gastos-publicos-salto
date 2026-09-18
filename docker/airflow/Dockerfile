FROM apache/airflow:3.3.2-python3.12

ARG AIRFLOW_VERSION=3.3.2

# A imagem oficial já utiliza o usuário airflow para instalações Python.
# Repetimos a versão do Airflow para impedir que o resolvedor do pip faça
# upgrade ou downgrade ao instalar as dependências do projeto.
COPY requirements.txt /tmp/project-requirements.txt

RUN pip install --no-cache-dir \
    "apache-airflow==${AIRFLOW_VERSION}" \
    -r /tmp/project-requirements.txt
