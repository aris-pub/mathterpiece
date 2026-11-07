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

# build the examples (but house.mtp, which is not a figure), the demo, the shared cases and the web runtime's fixtures to .mtpc, for the dev page and the tests
web-examples:
    rm -rf web/test/data/shared
    mkdir -p web/test/data/shared
    for f in tests/shared/*.mtp; do uv run mtp compile "$f" -o "web/test/data/shared/$(basename "$f" .mtp).mtpc"; cp "$f" web/test/data/shared/; done
    rm -rf web/test/data/runtime web/test/data/demo web/test/data/examples
    for f in examples/*.mtp; do [ "$f" = examples/house.mtp ] && continue; uv run mtp compile "$f" -o "web/test/data/examples/$(basename "$f" .mtp).mtpc"; cp "$f" web/test/data/examples/; done
    for f in web/test/fixtures/runtime/*.mtp; do uv run mtp compile "$f" -o "web/test/data/runtime/$(basename "$f" .mtp).mtpc"; cp "$f" web/test/data/runtime/; done
    for f in web/demo/*.mtp; do uv run mtp compile "$f" -o "web/test/data/demo/$(basename "$f" .mtp).mtpc"; cp "$f" web/test/data/demo/; done

# run the web runtime's tests
web-test *args: web-examples
    cd web && pnpm test {{args}}

# serve a page that draws any example with the web runtime
web-dev: web-examples
    cd web && pnpm exec vite

# type check the web runtime
web-typecheck:
    cd web && pnpm typecheck

# build the web runtime bundle (web/dist/mathterpiece.js)
build-web:
    cd web && pnpm build

# run the Emacs mode's tests
emacs-test:
    emacs --batch -L editors -l editors/mtp-mode.el -l editors/mtp-mode-test.el -f ert-run-tests-batch-and-exit

# run lint, type check, and tests, for Python and the web runtime
check: lint typecheck test web-typecheck web-test

# time compiling each example against scripts/perf/compile-times.json and fail at over 30% and 20 ms slower; the baseline is this machine's times, so on another machine record its own first with --update
compile-times *args:
    uv run python scripts/perf/compile_times.py {{args}}

# open each example's built page in Chromium as a phone (390x844, touch, CPU 4 times slower) and fail when it draws in over 2 s or an update does over 16 ms of work (handlers, style and layout, and the next frame's callbacks; waiting for the screen is left out)
phone-speed *examples: _web-ready
    cd web && node perf/phone.mjs {{examples}}

# install the web runtime's packages and Chromium, and build the runtime bundle mtp build puts in a page
_web-ready:
    cd web && pnpm install --frozen-lockfile && pnpm build && pnpm exec playwright install chromium
