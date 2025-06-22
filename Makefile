.PHONY: build_web demo-setup demo-run compose-up loadtest proto proto-verify benchmark

build_web:
	pnpm --dir src/interface/web_client install
	pnpm --dir src/interface/web_client run build

demo-setup:
	bash scripts/demo_setup.sh

demo-run:
	@RUN_MODE=${RUN_MODE:-cli}; \
	if [ "$$RUN_MODE" = "web" ]; then \
		.venv/bin/python -m streamlit run alpha_factory_v1/demos/alpha_agi_insight_v1/src/interface/web_app.py; \
	else \
		.venv/bin/python -m alpha_factory_v1.demos.alpha_agi_insight_v1 --episodes 5; \
	fi

compose-up:
	docker compose -f docker-compose.yml up --build &
	sleep 2
	python -m webbrowser http://localhost:8080 >/dev/null 2>&1

loadtest:
	k6 run --summary-export=tools/loadtest/summary.json tools/loadtest/insight.js
	@python - <<'PY2'
	import json
	with open('tools/loadtest/summary.json') as f:
	    data=json.load(f)
	print(f"p95 latency: {data['metrics']['http_req_duration']['p(95)']} ms")
	PY2

proto:
	./scripts/gen_proto.py

proto-verify:
	git --no-pager diff --exit-code src/utils/a2a_pb2.py tools/go_a2a_client/a2a.pb.go

benchmark:
	python benchmarks/docker_runner.py > bench_results.json
