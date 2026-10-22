# Measured fill-index performance — 2026-10-22

These are local measurements, not Earstrip's upstream benchmark claims. The
baseline is wasabi2d's actual `mapbox-earcut==1.0.3` dependency, rebuilt from
source with the same GNU 13.3 compiler used for the candidate. Both ran in the
same CPython 3.12.15 / NumPy 1.26.4 environment, pinned to logical CPU 0 on an
Intel Core Ultra 7 258V, Linux 5.15.167.4 / WSL2 / glibc 2.39. Python itself
reports Clang 23.1.3; the native extensions measured here were built with GCC/G++.

Candidate: wasabi-geom `e4114f6386f4a3e45d18ad9debdf1d73c95057a6`, vendoring
Earstrip `a145683a71b8a723f1ae9afa20b7f434e9b957e3` (ISC).
Harness/consumer source: `90611c885c5aba0a5a7635f32382385eeaa76667`.
The package metadata still says 2.3.0; this is a feature commit, **not a released
2.3.0 Earstrip API**. Binary hashes are in the raw reports.

## Result

The six 120-vertex ripple polygons reproduced from the existing rendering test
improved 1.15–1.46× in run 1 and 1.11–1.44× in run 2, including coordinate slicing,
ring setup, binding allocations and output conversion. This measures fill-index
creation, not whole-frame rendering or game FPS. The large concave case is
essentially tied (0.99× / 1.01× for float32), not an established speedup.

There are regressions: several synthetic star boundaries are slower, with a
worst end-to-end ratio of 0.88× in run 1 and 0.89× in run 2 (about 14% / 13%
more time). Production Circle/Star use their existing fans and are not switched
by this PR; their boundary fixtures are extra triangulator coverage, not claims
of production Circle/Star acceleration. No fixture has been removed for losing.

Run 1 is the first pinned run, not the faster of two. Every per-fixture median
below uses all seven samples; ± is median absolute deviation (MAD), not a
confidence interval. Run 2 is a separate full repetition. Ratios are baseline /
candidate, so values below 1 are regressions. Both complete runs validated all
304 jobs (38 inputs × two dtypes × end-to-end/kernel × two backends), with zero
Earcut fallbacks. All raw batches, iteration counts, quartiles, hashes, versions
and affinity are in [run1.json](run1.json) and [run2.json](run2.json).

## Reproduce

Use a fresh virtual environment with Python 3.12 and a C++17 compiler. From the
wasabi2d feature checkout:

```sh
python -m pip install numpy==1.26.4 Cython==3.3.0
CC=gcc CXX=g++ python -m pip install --no-cache-dir --no-deps \
  --no-binary=mapbox-earcut -Cbuild.verbose=true mapbox-earcut==1.0.3
CC=gcc CXX=g++ python -m pip install \
  'git+https://github.com/lordmauve/wasabi-geom.git@e4114f6386f4a3e45d18ad9debdf1d73c95057a6'
python -m unittest discover -s benchmarks -p 'test_*.py' -v
CC=gcc CXX=g++ taskset -c 0 python benchmarks/triangulate.py \
  --seconds 16 --repeats 7 --output run1.json
CC=gcc CXX=g++ taskset -c 0 python benchmarks/triangulate.py \
  --seconds 16 --repeats 7 --output run2.json
```

Choose an allowed CPU on another host; `taskset` is Linux-specific. Source build
flags and build-tool versions are in [build-config.json](build-config.json).
The baseline used `-O3 -DNDEBUG -flto=auto`; candidate used `-O3 -std=c++17`
without LTO. Project defaults were retained, not tuned separately to win.
Each run has three warmup calls plus calibration, seven randomly interleaved
batches, fixed seeds, and GC disabled only during timing. Timed wall durations
were 17.18 and 16.61 seconds. See [methodology](../README.md) for exact boundaries.

## Tests and limits

* Native API: **142 tests passed**, including holes/winding, repeated/collinear
  vertices, empty/short rings, invalid metadata, nonfinite rejection, float64
  precision, read-only/negative/noncontiguous strides and standard-library buffers.
* New consumer integration: **4 tests passed**; graphics-free benchmark suite:
  **8 tests passed**, including all fixtures and independent output lifetimes.
* Existing polygon rendering: **6 passed, 2 existing reference mismatches**, on
  both old and new paths under llvmpipe. The actual baseline and candidate images
  for those two cases were byte-for-byte equal in pixel arrays (maximum channel
  difference 0); expected images were not changed.
* Full existing wasabi2d tests: old path **173 passed, 12 failed, 8 errors**;
  candidate full run including 12 new tests **185 passed, same 12
  failed and 8 errors**. Failures include fixture asset/renderer and existing
  coroutine/type issues; this is not an all-green full-suite claim.
* Source distribution and wheel built successfully; wheel smoke-tested without
  NumPy. Old released wasabi-geom 2.3.0 was separately installed with the consumer
  and retained its existing uint32 Earcut path. Windows/macOS builds were not
  executed locally; C++17 compilation is left to wheel CI on those platforms.

The native API accepts simple polygons with non-intersecting holes. It disables
new vertices and approximate/constrained repair, preserving input-only indices;
non-Exact upstream status raises ValueError. The consumer catches that refusal
and uses its existing Earcut path. Upstream status is not a guarantee of exact
real-number arithmetic or a general topology validator. Area/CCW/index bounds
and hole-centroid tests do not constitute a formal proof against every possible
compensating overlap/gap. Timing is host-sensitive; no frequency/governor or
system-wide load control was imposed. No invalid-polygon timing claim is made.

## All end-to-end fixtures — float32

| Fixture | Vertices | Mapbox µs ± MAD (run 1) | Earstrip µs ± MAD (run 1) | Ratio run 1 | Ratio run 2 |
|---|---:|---:|---:|---:|---:|
| triangle | 3 | 1.405 ± 0.198 | 0.721 ± 0.097 | 1.95× | 1.68× |
| quad | 4 | 1.453 ± 0.032 | 0.731 ± 0.043 | 1.99× | 1.55× |
| circle-00 | 30 | 2.118 ± 0.100 | 1.038 ± 0.027 | 2.04× | 2.05× |
| star-00 | 6 | 1.370 ± 0.075 | 0.851 ± 0.028 | 1.61× | 1.67× |
| circle-01 | 40 | 2.572 ± 0.115 | 1.168 ± 0.030 | 2.20× | 2.02× |
| star-01 | 10 | 1.568 ± 0.032 | 0.984 ± 0.053 | 1.59× | 1.57× |
| circle-02 | 49 | 3.011 ± 0.149 | 1.244 ± 0.023 | 2.42× | 2.31× |
| star-02 | 14 | 1.596 ± 0.054 | 1.139 ± 0.107 | 1.40× | 1.50× |
| circle-03 | 59 | 3.868 ± 0.076 | 1.375 ± 0.109 | 2.81× | 2.68× |
| star-03 | 18 | 1.767 ± 0.030 | 1.386 ± 0.063 | 1.28× | 1.25× |
| circle-04 | 68 | 4.791 ± 0.126 | 1.442 ± 0.075 | 3.32× | 3.51× |
| star-04 | 22 | 1.789 ± 0.036 | 1.542 ± 0.050 | 1.16× | 1.15× |
| circle-05 | 78 | 5.853 ± 0.225 | 1.437 ± 0.106 | 4.07× | 4.40× |
| star-05 | 26 | 1.975 ± 0.094 | 1.839 ± 0.007 | 1.07× | 1.14× |
| circle-06 | 87 | 4.051 ± 0.326 | 1.555 ± 0.023 | 2.61× | 2.69× |
| star-06 | 30 | 2.190 ± 0.150 | 1.897 ± 0.128 | 1.15× | 1.06× |
| circle-07 | 96 | 4.571 ± 0.063 | 1.673 ± 0.025 | 2.73× | 2.61× |
| star-07 | 34 | 2.388 ± 0.082 | 2.142 ± 0.175 | 1.11× | 1.00× |
| circle-08 | 106 | 4.879 ± 0.174 | 1.686 ± 0.019 | 2.89× | 2.95× |
| star-08 | 38 | 2.567 ± 0.018 | 2.229 ± 0.159 | 1.15× | 1.03× |
| circle-09 | 115 | 5.300 ± 0.343 | 1.803 ± 0.019 | 2.94× | 2.96× |
| star-09 | 42 | 2.688 ± 0.086 | 2.748 ± 0.120 | 0.98× | 0.92× |
| circle-10 | 125 | 5.490 ± 0.261 | 1.849 ± 0.111 | 2.97× | 3.19× |
| star-10 | 46 | 2.796 ± 0.119 | 3.178 ± 0.181 | 0.88× | 0.89× |
| circle-11 | 134 | 6.537 ± 0.109 | 1.871 ± 0.060 | 3.49× | 3.03× |
| star-11 | 50 | 3.074 ± 0.080 | 3.363 ± 0.172 | 0.91× | 0.89× |
| ripple-0 | 120 | 6.460 ± 0.586 | 4.436 ± 0.180 | 1.46× | 1.26× |
| ripple-1 | 120 | 6.106 ± 0.553 | 4.433 ± 0.239 | 1.38× | 1.44× |
| ripple-2 | 120 | 6.137 ± 0.425 | 4.648 ± 0.155 | 1.32× | 1.25× |
| ripple-3 | 120 | 5.977 ± 0.278 | 4.766 ± 0.165 | 1.25× | 1.35× |
| ripple-4 | 120 | 5.799 ± 0.382 | 4.406 ± 0.260 | 1.32× | 1.11× |
| ripple-5 | 120 | 5.692 ± 0.278 | 4.939 ± 0.300 | 1.15× | 1.15× |
| large-concave | 2048 | 562.944 ± 44.539 | 571.090 ± 34.407 | 0.99× | 1.01× |
| one-hole | 8 | 1.669 ± 0.174 | 1.238 ± 0.085 | 1.35× | 1.36× |
| two-holes | 12 | 2.072 ± 0.085 | 1.719 ± 0.073 | 1.21× | 1.23× |
| reverse-winding | 4 | 1.348 ± 0.115 | 0.748 ± 0.015 | 1.80× | 1.85× |
| closed-duplicate | 5 | 1.369 ± 0.089 | 0.776 ± 0.048 | 1.76× | 1.88× |
| collinear-edge | 5 | 1.425 ± 0.144 | 0.797 ± 0.043 | 1.79× | 1.75× |

## All end-to-end fixtures — float64

| Fixture | Vertices | Mapbox µs ± MAD (run 1) | Earstrip µs ± MAD (run 1) | Ratio run 1 | Ratio run 2 |
|---|---:|---:|---:|---:|---:|
| triangle | 3 | 1.387 ± 0.073 | 0.831 ± 0.012 | 1.67× | 1.86× |
| quad | 4 | 1.446 ± 0.056 | 0.727 ± 0.030 | 1.99× | 1.89× |
| circle-00 | 30 | 2.101 ± 0.032 | 1.061 ± 0.129 | 1.98× | 1.97× |
| star-00 | 6 | 1.469 ± 0.044 | 0.961 ± 0.022 | 1.53× | 1.66× |
| circle-01 | 40 | 2.507 ± 0.095 | 1.232 ± 0.078 | 2.04× | 2.07× |
| star-01 | 10 | 1.563 ± 0.044 | 1.101 ± 0.085 | 1.42× | 1.40× |
| circle-02 | 49 | 3.093 ± 0.073 | 1.289 ± 0.099 | 2.40× | 2.41× |
| star-02 | 14 | 1.698 ± 0.047 | 1.187 ± 0.052 | 1.43× | 1.27× |
| circle-03 | 59 | 3.798 ± 0.102 | 1.392 ± 0.069 | 2.73× | 2.62× |
| star-03 | 18 | 1.772 ± 0.069 | 1.460 ± 0.019 | 1.21× | 1.24× |
| circle-04 | 68 | 4.636 ± 0.210 | 1.508 ± 0.099 | 3.07× | 3.34× |
| star-04 | 22 | 1.910 ± 0.044 | 1.630 ± 0.036 | 1.17× | 1.09× |
| circle-05 | 78 | 5.690 ± 0.225 | 1.599 ± 0.070 | 3.56× | 3.68× |
| star-05 | 26 | 1.921 ± 0.027 | 1.896 ± 0.053 | 1.01× | 1.07× |
| circle-06 | 87 | 4.235 ± 0.237 | 1.598 ± 0.061 | 2.65× | 2.65× |
| star-06 | 30 | 2.203 ± 0.195 | 2.088 ± 0.028 | 1.05× | 1.02× |
| circle-07 | 96 | 4.711 ± 0.117 | 1.690 ± 0.080 | 2.79× | 2.77× |
| star-07 | 34 | 2.324 ± 0.138 | 2.328 ± 0.115 | 1.00× | 0.99× |
| circle-08 | 106 | 4.942 ± 0.097 | 1.863 ± 0.142 | 2.65× | 3.23× |
| star-08 | 38 | 2.442 ± 0.227 | 2.359 ± 0.128 | 1.03× | 0.98× |
| circle-09 | 115 | 5.470 ± 0.532 | 1.625 ± 0.111 | 3.37× | 3.02× |
| star-09 | 42 | 2.594 ± 0.262 | 2.703 ± 0.222 | 0.96× | 0.92× |
| circle-10 | 125 | 5.116 ± 0.178 | 1.929 ± 0.056 | 2.65× | 2.84× |
| star-10 | 46 | 2.774 ± 0.127 | 2.788 ± 0.214 | 0.99× | 0.91× |
| circle-11 | 134 | 6.335 ± 0.573 | 2.063 ± 0.079 | 3.07× | 3.27× |
| star-11 | 50 | 3.005 ± 0.073 | 3.357 ± 0.106 | 0.90× | 0.92× |
| ripple-0 | 120 | 6.338 ± 0.448 | 4.715 ± 0.163 | 1.34× | 1.34× |
| ripple-1 | 120 | 5.816 ± 0.316 | 4.400 ± 0.319 | 1.32× | 1.41× |
| ripple-2 | 120 | 5.765 ± 0.273 | 4.608 ± 0.140 | 1.25× | 1.29× |
| ripple-3 | 120 | 6.160 ± 0.660 | 4.887 ± 0.082 | 1.26× | 1.17× |
| ripple-4 | 120 | 5.896 ± 0.615 | 4.847 ± 0.114 | 1.22× | 1.25× |
| ripple-5 | 120 | 6.466 ± 0.185 | 4.794 ± 0.214 | 1.35× | 1.18× |
| large-concave | 2048 | 586.323 ± 24.943 | 548.506 ± 36.863 | 1.07× | 1.12× |
| one-hole | 8 | 1.623 ± 0.093 | 1.276 ± 0.081 | 1.27× | 1.19× |
| two-holes | 12 | 2.095 ± 0.121 | 1.812 ± 0.039 | 1.16× | 1.22× |
| reverse-winding | 4 | 1.422 ± 0.074 | 0.778 ± 0.054 | 1.83× | 1.67× |
| closed-duplicate | 5 | 1.455 ± 0.041 | 0.816 ± 0.090 | 1.78× | 1.80× |
| collinear-edge | 5 | 1.379 ± 0.051 | 0.904 ± 0.035 | 1.52× | 1.58× |
