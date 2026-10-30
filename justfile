default:
    @just --list

# run the test suite
test *args:
    uv run pytest {{args}}

# lint and check formatting
lint:
    uv run ruff check
    uv run ruff format --check

# format code and apply safe lint fixes
fmt:
    uv run ruff format
    uv run ruff check --fix

# type check
typecheck:
    uv run ty check

# build the examples, the cases both runtimes must agree on, and the web's own test fixtures to JSON
web-examples:
    mkdir -p web/test/data/examples web/test/data/shared web/test/data/fixtures
    for f in examples/*.mtp; do uv run mtp build "$f" -o "web/test/data/examples/$(basename "$f" .mtp).json"; done
    for f in tests/shared/*.mtp; do uv run mtp build "$f" -o "web/test/data/shared/$(basename "$f" .mtp).json"; cp "$f" web/test/data/shared/; done
    for f in web/test/fixtures/*.mtp; do uv run mtp build "$f" -o "web/test/data/fixtures/$(basename "$f" .mtp).json"; done

# run the web runtime's tests
web-test *args: web-examples
    cd web && pnpm test {{args}}

# serve a page that draws any example with the web runtime
web-dev: web-examples
    cd web && pnpm exec vite

# type check the web runtime
web-typecheck:
    cd web && pnpm typecheck

# build the web runtime and copy it where mtp build looks for it
build-web:
    cd web && pnpm build
    mkdir -p mathterpiece/web
    cp web/dist/mathterpiece.js mathterpiece/web/mathterpiece.js

# run lint, type check, and tests, for Python and the web runtime
check: lint typecheck test web-typecheck web-test
