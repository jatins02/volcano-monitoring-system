# Durable local backend

Stage7 implements the FastAPI session/job API, SQLite persistence, strict input models, managed async worker, bounded subprocess lifecycle, actual Logisim/native execution, output parsers, comparison and immutable provenance artifacts. Python does not compute replacement warning/statistical results.

Run `make dev-api` from the repository root and open http://127.0.0.1:8000/docs. Use one worker. `make test-api` runs real localhost workflows with actual tools. See [API contracts](../docs/backend-api.md) and [verification](../reports/stages3-7-verification.md). Browser controls and full website integration remain later stages.
