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

# serve the spec site at http://127.0.0.1:8820, building it again and reloading the page on each save
spec:
    uv run --group docs sphinx-autobuild -E -W --keep-going docs docs/_build/html --host 127.0.0.1 --port 8820 --watch mathterpiece --watch docs/_ext

# build the spec site once into docs/_build/html
spec-build:
    uv run --group docs sphinx-build -E -W --keep-going -b html -d docs/_build/doctrees docs docs/_build/html

# check every link of the spec site, internal and external, and fail on a broken one
spec-linkcheck:
    uv run --group docs sphinx-build -E -W --keep-going -b linkcheck -d docs/_build/doctrees docs docs/_build/linkcheck
    uv run --group docs sphinx-build -E -W --keep-going -b html -d docs/_build/doctrees docs docs/_build/html
    uv run --no-project python docs/_ext/check_local_links.py docs/_build/html

# build the spec site and publish it to its fixed draft address on Netlify, https://draft--mtp-spec.netlify.app, to read on a phone
spec-preview: spec-build
    npx -y --loglevel=silent netlify-cli@27.16.2 deploy --dir docs/_build/html --site d1eaf3d8-0626-4e13-a3a1-c9ed535b30da --alias draft --json | uv run --no-project python -c "import json, sys; print(json.load(sys.stdin)['deploy_url'])"

# build the spec site and publish it at https://spec.mtp-lang.org
spec-publish: spec-build
    npx -y --loglevel=silent netlify-cli@27.16.2 deploy --dir docs/_build/html --site d1eaf3d8-0626-4e13-a3a1-c9ed535b30da --prod --json | uv run --no-project python -c "import json, sys; print(json.load(sys.stdin)['url'])"
