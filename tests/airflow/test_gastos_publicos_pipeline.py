"""Testes estruturais da DAG de gastos públicos."""

from pathlib import Path

from airflow.models import DagBag


DAGS_FOLDER = Path("/opt/airflow/project/airflow/dags")
DAG_ID = "gastos_publicos_salto"


def load_dag():
    """Carrega e retorna a DAG principal do projeto."""
    dag_bag = DagBag(
        dag_folder=str(DAGS_FOLDER),
    )

    assert dag_bag.import_errors == {}
    assert DAG_ID in dag_bag.dags

    return dag_bag.dags[DAG_ID]


def test_dag_contains_expected_tasks() -> None:
    """Valida as tarefas que compõem o pipeline."""
    dag = load_dag()

    assert set(dag.task_ids) == {
        "atualizar_bronze",
        "transformar_e_testar",
    }


def test_transformation_depends_on_bronze_update() -> None:
    """Garante que a transformação execute depois da ingestão."""
    dag = load_dag()

    atualizar_bronze = dag.get_task("atualizar_bronze")
    transformar_e_testar = dag.get_task("transformar_e_testar")

    assert atualizar_bronze.downstream_task_ids == {
        "transformar_e_testar"
    }
    assert transformar_e_testar.upstream_task_ids == {
        "atualizar_bronze"
    }


def test_dag_operational_configuration() -> None:
    """Valida as principais proteções operacionais da DAG."""
    dag = load_dag()

    assert dag.catchup is False
    assert dag.max_active_runs == 1
    assert dag.timetable.expression == "0 10 * * 1"


def test_tasks_have_retries_and_timeouts() -> None:
    """Valida retentativas e limites de duração das tarefas."""
    dag = load_dag()

    atualizar_bronze = dag.get_task("atualizar_bronze")
    transformar_e_testar = dag.get_task("transformar_e_testar")

    assert atualizar_bronze.retries == 2
    assert transformar_e_testar.retries == 2
    assert atualizar_bronze.execution_timeout is not None
    assert transformar_e_testar.execution_timeout is not None
