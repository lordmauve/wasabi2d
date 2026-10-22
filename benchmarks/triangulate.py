#!/usr/bin/env python3
"""Reproducible mapbox-earcut 1.0.3 / wasabigeom triangulation comparison."""
import argparse
import gc
import hashlib
import importlib.metadata
import importlib.machinery
import importlib.util
import json
import math
import os
from pathlib import Path
import platform
import random
import subprocess
import sys
import sysconfig
import time

import numpy as np
import mapbox_earcut


def fixtures():
    """Boundary-only versions of test_polygons shapes; no graphics imports."""
    yield 'triangle', np.array([[0, 0], [3, 0], [0, 2]]), None
    yield 'quad', np.array([[-.5, -.5], [-.5, .5], [.5, .5], [.5, -.5]]), None
    # Circle/Star use a triangle fan, NOT polygon triangulation in production.
    # Their orig_verts[0] is a centre sentinel, not part of the boundary.
    for i in range(12):
        radius = 3 * i + 10
        theta = np.linspace(0, 2 * np.pi, max(4, round(math.pi * radius)))
        base = np.column_stack((np.cos(theta), np.sin(theta))).astype('f4')
        yield f'circle-{i:02}', (base * radius)[1:], None
        points = 2 * i + 3
        theta = np.linspace(0, 2 * np.pi, 2 * points + 1)
        base = np.column_stack((np.cos(theta), np.sin(theta))).astype('f4')
        base[::2] *= 3 * i + 10
        base[1::2] *= 2 * i + 2
        yield f'star-{i:02}', base[1:], None
    rng = random.Random(0)
    for layer in range(6):
        h = (6 - layer) * 600 / 24 + 20
        wavelength = np.array([rng.uniform(.2, 1) for _ in range(6)])
        phase = np.array([rng.uniform(0, np.pi) for _ in range(6)])
        mag = np.array([rng.uniform(4, 10) for _ in range(6)])
        xs = np.linspace(0, 800, 60)
        ts = np.linspace(4, 12, 60)[:, None]
        ys = np.sum(mag[None, :] * np.sin(ts / wavelength + phase), axis=1)
        yield f'ripple-{layer}', np.vstack((np.column_stack((xs, 300 + h + ys)),
                                              np.column_stack((xs, 300 - h - ys))[::-1])), None
    rng = np.random.default_rng(20261027)
    theta = np.arange(2048) * (2 * np.pi / 2048)
    radius = rng.uniform(.4, 1, len(theta))
    yield 'large-concave', np.column_stack((radius * np.cos(theta), radius * np.sin(theta))), None
    outer = np.array([[0, 0], [12, 0], [12, 10], [0, 10]])
    hole = np.array([[2, 2], [2, 4], [4, 4], [4, 2]])
    hole2 = np.array([[7, 5], [7, 8], [10, 8], [10, 5]])
    yield 'one-hole', np.vstack((outer, hole)), [4, 8]
    yield 'two-holes', np.vstack((outer, hole, hole2)), [4, 8, 12]
    yield 'reverse-winding', outer[::-1].copy(), None
    yield 'closed-duplicate', np.vstack((outer, outer[0])), None
    yield 'collinear-edge', np.array([[0, 0], [6, 0], [12, 0], [12, 10], [0, 10]]), None


def area(points):
    p = np.asarray(points, dtype='f8')
    return float(np.sum(p[:, 0] * np.roll(p[:, 1], -1) - p[:, 1] * np.roll(p[:, 0], -1)) / 2)


def validate(vertices, ends, result):
    """Check geometric invariants, not a particular diagonal/order."""
    idx = np.asarray(result)
    assert idx.ndim == 1 and idx.size % 3 == 0, 'not a flat triangle buffer'
    assert idx.dtype.kind in 'iu', 'non-integer indices'
    assert idx.size and int(idx.min()) >= 0 and int(idx.max()) < len(vertices), 'index bounds'
    p = vertices.astype('f8')[idx.reshape(-1, 3)]
    a, b = p[:, 1] - p[:, 0], p[:, 2] - p[:, 0]
    signed = (a[:, 0] * b[:, 1] - a[:, 1] * b[:, 0]) / 2
    # Both backends must return CCW triangles; tiny zero-area degeneracies allowed.
    scale = max(float(np.ptp(vertices, axis=0).max()) ** 2, 1)
    assert np.all(signed >= -scale * 1e-10), 'clockwise triangle'
    boundaries = ends if ends is not None else [len(vertices)]
    start, expected = 0, 0.
    for i, end in enumerate(boundaries):
        expected += (1 if i == 0 else -1) * abs(area(vertices[start:end]))
        start = end
    assert np.isclose(np.abs(signed).sum(), expected, rtol=2e-5, atol=scale * 1e-8), 'area mismatch'
    # Triangle centroids may not lie strictly inside any hole.
    centers = p.mean(axis=1)
    start = boundaries[0]
    for end in boundaries[1:]:
        ring = vertices[start:end].astype('f8')
        inside = np.zeros(len(centers), dtype=bool)
        x, y = centers.T
        for a, b in zip(ring, np.roll(ring, -1, axis=0)):
            if a[1] != b[1]:
                inside ^= ((a[1] > y) != (b[1] > y)) & (x < (b[0] - a[0]) * (y - a[1]) / (b[1] - a[1]) + a[0])
        assert not inside.any(), 'triangle centroid inside hole'
        start = end


def runners(storage, ends, dtype, candidate=None):
    view = storage[:, :2]
    rings = np.array(ends if ends is not None else [len(view)], dtype=np.uint32)
    baseline = getattr(mapbox_earcut, f'triangulate_float{dtype[-2:]}')
    def mapbox_e2e():
        verts = storage[:, :2]
        ring_ends = np.array(ends if ends is not None else [len(verts)], dtype=np.uint32)
        return baseline(verts, ring_ends).reshape(-1)
    result = {'mapbox/e2e': mapbox_e2e, 'mapbox/kernel': lambda: baseline(view, rings)}
    if candidate is not None:
        def candidate_e2e():
            if ends is None:
                # Match the consumer success path, including its exception handler.
                try:
                    idxs = candidate(storage[:, :2])
                except ValueError:
                    candidate_e2e.fallback_count += 1
                    return mapbox_e2e()
                return np.asarray(idxs).reshape(-1)
            # Holes exercise the generic API, not the single-ring consumer path.
            return np.asarray(candidate(storage[:, :2], ring_ends=list(ends))).reshape(-1)
        candidate_e2e.fallback_count = 0
        result['earstrip/e2e'] = candidate_e2e
        result['earstrip/kernel'] = (lambda: candidate(view)) if ends is None else (lambda: candidate(view, ring_ends=rings))
    return result


def reject_fallback(fn):
    if getattr(fn, 'fallback_count', 0):
        raise AssertionError('Earstrip fallback occurred; refusing to label mapbox work as Earstrip')


def timed(fn, count):
    start = time.perf_counter_ns()
    for _ in range(count):
        fn()
    return time.perf_counter_ns() - start


def metadata():
    def command(args):
        try:
            return subprocess.check_output(args, text=True, stderr=subprocess.STDOUT).strip()
        except (OSError, subprocess.CalledProcessError):
            return None
    cpu = None
    try:
        cpu = next(line.split(':', 1)[1].strip() for line in Path('/proc/cpuinfo').read_text().splitlines() if line.startswith('model name'))
    except (OSError, StopIteration):
        pass
    versions = {}
    for name in ('numpy', 'mapbox-earcut', 'wasabi-geom', 'Cython'):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    native_extensions = {}
    geom_origin = None
    for module, distribution in (('mapbox_earcut', 'mapbox-earcut'),
                                 ('wasabigeom', 'wasabi-geom'),
                                 ('_wasabi_earstrip', 'wasabi-geom')):
        spec = importlib.util.find_spec(module)
        origin = Path(spec.origin).resolve() if spec and spec.origin else None
        if module == 'wasabigeom':
            geom_origin = origin
        paths = {origin} if origin and any(str(origin).endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES) else set()
        try:
            dist = importlib.metadata.distribution(distribution)
            for entry in dist.files or ():
                if any(str(entry).endswith(s) for s in importlib.machinery.EXTENSION_SUFFIXES):
                    paths.add(Path(dist.locate_file(entry)).resolve())
        except importlib.metadata.PackageNotFoundError:
            pass
        native_extensions[module] = [dict(path=str(path), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
                                     for path in sorted(paths) if path.is_file()]
    # Bound discovery to the module's directory and one package parent. Never
    # infer a source revision from an unrelated ancestor of site-packages.
    geom_revision, geom_dirty = None, None
    geom_revision_status = 'not_identifiable_from_installed_module'
    if geom_origin:
        for directory in (geom_origin.parent, geom_origin.parent.parent):
            if (directory / '.git').exists():
                geom_revision = command(['git', '-C', str(directory), 'rev-parse', 'HEAD'])
                if geom_revision:
                    status = command(['git', '-C', str(directory), 'status', '--porcelain'])
                    geom_dirty = bool(status) if status is not None else None
                    geom_revision_status = 'checkout_at_module_location'
                break
    return dict(python=sys.version, executable=sys.executable, platform=platform.platform(),
                native_extensions=native_extensions, wasabi_geom_module=str(geom_origin) if geom_origin else None,
                wasabi_geom_revision=geom_revision, wasabi_geom_revision_status=geom_revision_status,
                wasabi_geom_checkout_dirty=geom_dirty,
                cpu=cpu, affinity=sorted(os.sched_getaffinity(0)) if hasattr(os, 'sched_getaffinity') else None,
                versions=versions, python_compiler=platform.python_compiler(),
                configured_cc=sysconfig.get_config_var('CC'),
                env={k: os.environ.get(k) for k in ('CC', 'CXX', 'CFLAGS', 'CXXFLAGS', 'LDFLAGS')},
                gcc=command(['gcc', '--version']), gxx=command(['g++', '--version']),
                revision=command(['git', '-C', str(Path(__file__).resolve().parents[1]), 'rev-parse', 'HEAD']),
                script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-only', action='store_true', help='validate harness before candidate is installed')
    parser.add_argument('--seconds', type=float, default=16, help='approximate total timing budget; validation/metadata extra')
    parser.add_argument('--repeats', type=int, default=7)
    parser.add_argument('--output', type=Path, default=Path('triangulate-results.json'))
    args = parser.parse_args()
    if args.seconds <= 0 or args.repeats < 3:
        parser.error('positive seconds and at least three repeats required')
    if importlib.metadata.version('mapbox-earcut') != '1.0.3':
        parser.error('requires actual pinned baseline mapbox-earcut==1.0.3')
    candidate = None
    if not args.baseline_only:
        from wasabigeom import triangulate
        candidate = triangulate
    jobs = []
    for name, vertices, ends in fixtures():
        for dtype in ('float32', 'float64'):
            storage = np.ones((len(vertices), 3), dtype=dtype)
            storage[:, :2] = vertices
            for label, fn in runners(storage, ends, dtype, candidate).items():
                validate(storage[:, :2], ends, fn())
                reject_fallback(fn)
                for _ in range(3):
                    fn()
                reject_fallback(fn)
                jobs.append((dict(fixture=name, dtype=dtype, shape=list(storage[:, :2].shape),
                                  strides=list(storage[:, :2].strides), backend=label), fn))
    # Calibrate once; bound counts to keep the complete matrix inexpensive.
    per_repeat_ns = args.seconds * 1e9 / (len(jobs) * args.repeats)
    counts = [max(1, min(100000, int(per_repeat_ns / max(timed(fn, 10) / 10, 1)))) for _, fn in jobs]
    samples = [[] for _ in jobs]
    rng = random.Random(20261027)
    enabled = gc.isenabled()
    gc.disable()
    started = time.perf_counter()
    try:
        for _ in range(args.repeats):
            order = list(range(len(jobs)))
            rng.shuffle(order)  # Rotate all backends/fixtures to reduce thermal/order bias.
            for i in order:
                samples[i].append(timed(jobs[i][1], counts[i]))
    finally:
        if enabled:
            gc.enable()
    rows = []
    for (row, fn), count, raw in zip(jobs, counts, samples):
        reject_fallback(fn)  # Also catch unexpected fallback during timed batches.
        row['fallback_count'] = getattr(fn, 'fallback_count', 0)
        ns = np.array(raw) / count
        median = float(np.median(ns))
        rows.append(dict(row, calls_per_sample=count, raw_batch_ns=raw, ns_per_call=ns.tolist(),
                         median_ns=median, mad_ns=float(np.median(np.abs(ns - median))),
                         p25_ns=float(np.percentile(ns, 25)), p75_ns=float(np.percentile(ns, 75))))
    report = dict(metadata=metadata(), arguments=vars(args) | {'output': str(args.output)},
                  timing_wall_seconds=time.perf_counter() - started, warmups=3,
                  gc_disabled_during_timing=True, validation='all fixtures/backends passed', rows=rows)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(f'{len(rows)} cases validated; raw timings and metadata: {args.output}')
    # Report every fixture, not a cherry-picked aggregate or headline speedup.
    for row in rows:
        print(f"{row['fixture']:20} {row['dtype']:7} {row['backend']:16} "
              f"median {row['median_ns']/1000:9.3f} us  MAD {row['mad_ns']/1000:.3f} us")


if __name__ == '__main__':
    main()
