SHELL := /bin/sh
.SHELLFLAGS := -eu -c
.DEFAULT_GOAL := help
PYTHON ?= python3
CC := gcc
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))

.PHONY: help bootstrap bootstrap-tools setup-python setup-web generate-rules check-rules \
        doctor build-asm build-web test check smoke-logisim smoke-web smoke-bridge test-bridge dev

help:
	@echo "Project: bootstrap, doctor, generate-rules, check-rules, build-asm, build-web, test, smoke-bridge, test-bridge, test-web, test-acceptance, check, run, dev, submission, clean-generated"

bootstrap: setup-python setup-web generate-rules

bootstrap-tools:
	cd "$(ROOT)" && $(PYTHON) -B scripts/toolchain.py

setup-python:
	cd "$(ROOT)" && $(PYTHON) -m venv .venv
	cd "$(ROOT)" && .venv/bin/python -m pip install -r requirements.lock

setup-web: bootstrap-tools
	cd "$(ROOT)" && sh scripts/npm.sh ci --prefix frontend --cache runtime/npm-cache

generate-rules:
	cd "$(ROOT)" && $(PYTHON) -B scripts/generate_rules.py

check-rules:
	cd "$(ROOT)" && $(PYTHON) -B scripts/generate_rules.py --check
	cd "$(ROOT)" && $(PYTHON) -B scripts/verify_circuit_rules.py

doctor:
	cd "$(ROOT)" && sh scripts/doctor.sh

build-asm: check-rules
	mkdir -p "$(ROOT)/build"
	cd "$(ROOT)" && $(CC) -g -pie -Wl,-z,noexecstack assembly/toolchain_smoke.s -o build/toolchain-smoke
	cd "$(ROOT)" && ./build/toolchain-smoke
	cd "$(ROOT)" && $(PYTHON) -B -m scripts.build_native

build-web: check-rules
	cd "$(ROOT)" && sh scripts/npm.sh run build --prefix frontend

smoke-logisim: check-rules
	cd "$(ROOT)" && $(PYTHON) -B scripts/logisim.py --smoke

test:
	cd "$(ROOT)" && $(PYTHON) -B -m unittest discover -s tests -v

smoke-web:
	cd "$(ROOT)" && $(PYTHON) -B scripts/smoke_web.py

check: test-web check-circuit test-combinational test-counters test-replay test-native test-api doctor test build-asm build-web smoke-logisim smoke-web smoke-bridge test-bridge

dev:
	cd "$(ROOT)" && sh scripts/npm.sh run dev --prefix frontend

smoke-bridge:
	cd "$(ROOT)" && $(PYTHON) -B scripts/bridge_proof.py

test-bridge:
	cd "$(ROOT)" && $(PYTHON) -B -m unittest discover -s tests/integration -p test_stage2_bridge.py -v

.PHONY: check-circuit test-combinational
check-circuit:
	cd "$(ROOT)" && $(PYTHON) -B scripts/build_monitor.py --check

test-combinational:
	cd "$(ROOT)" && $(PYTHON) -B scripts/check_combinational.py

.PHONY: test-counters
test-counters:
	cd "$(ROOT)" && $(PYTHON) -B -m scripts.check_counters

.PHONY: test-replay
test-replay:
	cd "$(ROOT)" && $(PYTHON) -B -m scripts.check_replay

.PHONY: test-native
test-native: build-asm
	cd "$(ROOT)" && $(PYTHON) -B -m scripts.check_native

.PHONY: dev-api
dev-api: build-asm
	cd "$(ROOT)" && .venv/bin/python -B -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1

.PHONY: test-api
test-api: build-asm
	cd "$(ROOT)" && .venv/bin/python -B -m scripts.check_api
	cd "$(ROOT)" && .venv/bin/python -B -m scripts.check_api_failures

.PHONY: test-web test-acceptance
test-web:
	cd "$(ROOT)" && tools/node/bin/node scripts/test_web.mjs
	cd "$(ROOT)" && sh scripts/npm.sh run format:check --prefix frontend

test-acceptance: build-asm
	cd "$(ROOT)" && .venv/bin/python -B -m scripts.check_acceptance

.PHONY: run clean-generated submission
run: build-asm build-web
	cd "$(ROOT)" && .venv/bin/python -B -m uvicorn backend.app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1

clean-generated:
	cd "$(ROOT)" && $(PYTHON) -B -m scripts.clean_generated

submission:
	cd "$(ROOT)" && $(PYTHON) -B -m scripts.package_submission
