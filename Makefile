.PHONY: up down logs ps smoke-test reset

up:
	docker compose up -d

down:
	docker compose down

reset:
	docker compose down -v
	rm -rf warehouse/*.duckdb minio_data/*

logs:
	docker compose logs -f

ps:
	docker compose ps

# Triggers the Phase 1 smoke-test DAG via the Airflow CLI inside the
# webserver container and tails the result.
smoke-test:
	docker compose exec airflow-webserver airflow dags unpause phase1_infra_smoke_test
	docker compose exec airflow-webserver airflow dags trigger phase1_infra_smoke_test
	@echo "Triggered. Check status with:"
	@echo "  docker compose exec airflow-webserver airflow dags list-runs -d phase1_infra_smoke_test"
	@echo "Or open http://localhost:8080 (admin/admin) and watch the DAG run."
