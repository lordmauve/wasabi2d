# Earstrip consumer benchmark

Run from the checkout root, with the **same Python/environment** for both backends:

```sh
PY=python  # Or /path/to/venv/bin/python
$PY -m unittest discover -s benchmarks -p 'test_*.py' -v
$PY benchmarks/triangulate.py --output benchmarks/results.json
```

Before the candidate is installed, add `--baseline-only`. The regression suite
skips candidate checks when its public import is unavailable; a comparative run
fails instead of silently omitting the candidate. Requires NumPy and the actual
`mapbox-earcut==1.0.3` dependency, not a substitute implementation or newer wheel.
The script does not install, compile, alter dependencies, or import wasabi2d's
rendering stack. When the native package is built separately, use `CC=gcc CXX=g++`
and record its exact revision and build log/flags alongside results. The report's
compiler/version/environment metadata describes the host and Python, **not proof
of the compiler or flags used in prebuilt native wheels**. JSON also records
Cython's installed version (or null), native extension SHA256 hashes for both
packages, and the wasabi-geom revision only when its module is located in an
identifiable checkout. Installed wheels without an adjacent checkout get a null
revision and explicit `not_identifiable_from_installed_module` status. A checkout
revision and dirty flag describe nearby source, not proof the binary was built
from it; retain build logs and binary hashes together.

## Source-built comparison setup

Use one virtual environment and compiler toolchain for both packages. For example,
from the consumer checkout with a separate candidate source checkout:

```sh
python -m venv /path/to/venv
PY=/path/to/venv/bin/python
$PY -m pip install numpy Cython setuptools wheel pybind11
# Force a fresh source build of the exact baseline, not a cached wheel.
CC=gcc CXX=g++ $PY -m pip install -v --force-reinstall --no-deps \
    --no-cache-dir --no-binary=mapbox-earcut 'mapbox-earcut==1.0.3' \
    > mapbox-build.log 2>&1
CC=gcc CXX=g++ $PY -m pip install -v --no-deps \
    --no-build-isolation -e /path/to/wasabi-geom-checkout \
    > wasabi-geom-build.log 2>&1
```

Pin your chosen NumPy/Cython/build-tool versions and retain those versions and
logs. The investigated source-built baseline uses gcc/g++ 13.3 with `-O3
-DNDEBUG -flto=auto`; the Earstrip extension uses g++ 13.3 with `-O3 -std=c++17`
and no LTO. The existing wasabi-geom C extension still uses gcc, without C++17.
The setup commands select compilers; actual package build settings determine
flags, so inspect the logs rather than assuming identical optimization settings.
These two native configurations share a compiler toolchain, **not identical
flags**. Investigation build logs are in `artifacts/earstrip-investigation` in
the working environment. Earlier prebuilt-baseline timings are superseded by the
source-built same-compiler comparison; do not mix those samples.

Default timing budget is about 16 seconds, plus validation, warmup, calibration
and metadata (roughly 20 seconds overall on this host). Use `--seconds 2
--repeats 3` for a smoke test. Timing samples are batches of calls, with three
warmups per job, calibrated iteration counts, seven repeats, randomized job order
with fixed seed, and cyclic GC disabled only during timing. Each result includes
raw batch nanoseconds, batch size, normalized per-call samples, median, MAD and
quartiles. No subtraction of Python-loop overhead. Avoid other CPU load, and
optionally pin the **whole** process with `taskset -c <allowed-cpu>`; metadata records
affinity. Run the whole matrix several times before drawing conclusions.

## What is measured

Every fixture is tested as float32 **and** float64, backed by an `(N,3)` allocation
with the `(N,2)` coordinate slice retaining its 3-element row stride. Float32 is
the actual consumer case. Float64 is API coverage, not a claimed wasabi2d workload.

* `mapbox/e2e`: take `storage[:, :2]`, allocate uint32 cumulative ring ends on
  every call, dispatch the actual baseline dtype-specific binding, flatten output.
* `earstrip/e2e`: take the same slice, call
  `from wasabigeom import triangulate; triangulate(view)`, then
  `np.asarray(result).reshape(-1)`. Hole fixtures additionally construct and pass a
  fresh `ring_ends` list. The default single ring is deliberately omitted, as the
  consumer does. The single-ring path includes the consumer's `try/except
  ValueError` handler and mapbox fallback. Validation rejects any fallback before
  timing, and another check after timing rejects unexpected timed fallbacks;
  successful JSON rows record `fallback_count: 0`. Thus no fallback can be silently
  reported as Earstrip work. Hole cases use the generic API without this fallback.
  Change only `runners()` if the public API changes.
* `*/kernel`: pre-created views and ring ends; backend binding call only. These
  still include binding and allocation costs, not isolated native algorithm time.
  No NumPy output conversion for the candidate kernel.

Vertex storage construction, fixture generation, imports, correctness checks,
rendering, GPU upload and scene management are outside both timing paths. Thus
'e2e' means end-to-end **fill-index creation**, not end-to-end rendering.

## Fixture coverage (no selected winners)

All 12 stars and all 12 circles use the parameters in `tests/test_polygons.py`,
with the construction in `Circle` and `Layer.add_star`: float32 trigonometric
boundary construction and the original radii/segment counts. These shapes are
translated locally just as production `orig_verts` are; scene positions do not
alter those local coordinates. The centre sentinel at vertex 0 is excluded.
**Production Circle/Star use their existing triangle fan, not polygon earcut.**
Their boundaries here are representative triangulator workloads, not evidence of
a production Circle/Star speedup. Their existing fan implementation is unchanged.

All six 120-vertex ripple polygons reproduce `test_draw_polygons` with
`random.Random(0)`, six octaves and the harness's 800×600 scene. Additional cases:
triangle, quad, seeded 2048-vertex radially ordered concave polygon, one and two
holes, reversed winding, repeated closing vertex, and a collinear edge vertex.
The large polygon uses NumPy `default_rng(20261027)`; exact library versions and
script hash are in the JSON. All 38 fixtures appear in the console and JSON; there
is no cherry-picked headline speedup or averaging of unlike workloads.

## Correctness and limitations

Before timing every backend/job must return a flat integer triangle buffer with
in-range indices, CCW nondegenerate triangles (tiny degeneracies tolerated), and
sum of absolute triangle areas equal to outer area minus holes. Triangle centroids
must not fall inside holes. Tests also check uint32 output and unchanged inputs,
plus candidate buffer lifetime and contiguous/Fortran/negative-coordinate-stride
views. No exact diagonal, triangle order, or index sequence is prescribed.

These checks catch common regressions but are not a formal proof of complete
non-overlapping coverage: area and centroid checks alone cannot rule out all
compensating overlaps/gaps. Invalid/self-intersecting polygons and malformed ring
metadata are not performance fixtures. Consumer integration tests live in
`tests/test_polygon_triangulation.py`; native API tests live in the companion
wasabi-geom change.
