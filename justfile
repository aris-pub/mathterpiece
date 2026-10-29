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

# run the web runtime's tests
web-test *args:
    cd web && pnpm test {{args}}

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
