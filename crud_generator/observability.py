"""Escritura del stack de observabilidad (Prometheus/Loki/Grafana) que acompaña
al docker-compose.yml generado. Compartido por generator.py y ports_generator.py."""

from . import templates


def write_observability_stack(write_file, base_dir, entity_name, entity_lower):
    write_file(
        f"{base_dir}/observability/prometheus.yml",
        templates.get_prometheus_config(entity_lower),
    )
    write_file(
        f"{base_dir}/observability/loki-config.yml",
        templates.get_loki_config(),
    )
    write_file(
        f"{base_dir}/observability/grafana/provisioning/datasources/datasources.yml",
        templates.get_grafana_datasources(),
    )
    write_file(
        f"{base_dir}/observability/grafana/provisioning/dashboards/dashboards.yml",
        templates.get_grafana_dashboard_provider(),
    )
    write_file(
        f"{base_dir}/observability/grafana/dashboards/{entity_lower}-overview.json",
        templates.get_grafana_business_dashboard(entity_name, entity_lower),
    )
