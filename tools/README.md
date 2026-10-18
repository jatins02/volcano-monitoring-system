# Pinned local toolchain

The source-controlled toolchain.json records exact official download URLs and SHA-256 values. versions.json records the measured reference environment, including the observed browser user agent. Portable downloads target Linux x86_64 only; do not use those archives on other platforms.

## Setup

Install Python 3.12-3.14 with venv/pip support and GNU gcc/binutils/make using your distribution's supported packages. The reference interpreter is Python 3.14.4; compiler/linker versions are recorded, not silently downloaded or globally replaced.

From the repository root:

```bash
make bootstrap
make check
make dev
```

Bootstrap downloads only the pinned Node 22.22.0, Temurin JRE 21.0.12.1 and Logisim-evolution 4.1.0 archives. It verifies SHA-256 before extraction/install, refuses unexpected existing runtime directories and uses safe tar extraction. It installs Python packages into .venv from requirements.lock and npm packages using npm ci/package-lock.json. First setup needs network access to the official release hosts, PyPI and the npm registry. After installation, check/build/dev commands do not require remote UI assets.

The Node wrapper prepends tools/node/bin for child processes and uses bundled npm 10.9.4. No global npm/Python/Java installation is changed. Commands must run with permission to execute local files and bind a localhost port; a restrictive sandbox can deny these independently of application correctness.

Generated tools/node, tools/java, tools/cache, .venv, frontend/node_modules, runtime and build files are ignored. Do not commit archives, virtual environments or generated session data. To repair an interrupted/mismatched runtime directory, inspect it and remove only the relevant generated tools/node or tools/java directory, then rerun bootstrap. Do not change a manifest checksum to accept unknown bytes.

## Source and version choices

- Logisim release: https://github.com/logisim-evolution/logisim-evolution/releases/tag/v4.1.0 . This stable pre-5 release is deliberately pinned; its CLI and smoke circuit were tested. It requires Java 21 or newer. The manifest's JAR SHA comes from GitHub release-asset metadata and was independently verified against the downloaded file.
- Java release metadata: https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jre&os=linux . Setup uses the resolved immutable archive URL and digest in the manifest, not the moving latest endpoint.
- Node release: https://nodejs.org/dist/v22.22.0/SHASUMS256.txt . The selected runtime meets Vite's supported Node engine range: https://vite.dev/guide/ . A newer global Node is not needed.
- Direct Python dependencies are recorded in requirements.in; requirements.lock pins the complete tested resolution. Update deliberately in a clean virtual environment and run pip check, imports and the test suite before recording a new lock.
- Direct frontend packages are exact pins; the committed npm lock contains the full resolution and integrity hashes. npm audit fix resolved compatible transitive patches before finalizing this lock; no force/major upgrade was used.

## Command scope

`make doctor` is offline and returns nonzero if the platform, compiler, runtime/JAR, CLI, Python pins/imports, frontend direct dependencies or runtime writability fail. `make check-rules` rejects stale generated views and mismatched/moved circuit constants. `make check` combines doctor, unit tests, native smoke build/run, TypeScript/production build and a real Logisim constant/halt run and an automatically cleaned-up Vite HTTP startup check on port5174.

`make dev` serves the setup page on http://127.0.0.1:5173 with strict port selection. It does not start monitoring or a FastAPI API. A full `make run` target belongs to the application integration stage and is intentionally not presented as available.
