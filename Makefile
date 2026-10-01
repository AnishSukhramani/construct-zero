.PHONY: ci test lint fmt cov guardrails

ci:
	@./scripts/ci-local.sh ci

test:
	@./scripts/ci-local.sh test

guardrails:
	@./scripts/ci-local.sh guardrails

lint:
	@./scripts/ci-local.sh lint

fmt:
	@./scripts/ci-local.sh fmt

cov:
	@./scripts/ci-local.sh cov
