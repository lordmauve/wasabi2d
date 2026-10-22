"""Graphics-free regression checks. Run with unittest discover (see README)."""
import unittest

import numpy as np
import triangulate as bench

try:
    from wasabigeom import triangulate as candidate
except ImportError:
    candidate = None


class InvariantTests(unittest.TestCase):
    def setUp(self):
        self.vertices = np.array([[0., 0.], [3., 0.], [0., 2.]])

    def test_valid_triangle(self):
        bench.validate(self.vertices, None, np.array([0, 1, 2], dtype='u4'))

    def test_bad_results_are_detected(self):
        for indices in ([0., 1., 2.], [0, 1, 3], [-1, 0, 1], [0, 2, 1],
                        [0, 1], [0, 0, 0], [0, 1, 2, 0, 1, 2]):
            with self.subTest(indices=indices), self.assertRaises(AssertionError):
                bench.validate(self.vertices, None, np.array(indices))

    def test_hole_filled_in_is_rejected(self):
        outer = np.array([[0., 0.], [10., 0.], [10., 10.], [0., 10.]])
        hole = np.array([[2., 2.], [2., 4.], [4., 4.], [4., 2.]])
        with self.assertRaises(AssertionError):
            bench.validate(np.vstack((outer, hole)), [4, 8], np.array([0, 1, 2, 0, 2, 3]))

    def test_fallback_is_not_accepted_as_earstrip(self):
        def refuses(vertices):
            raise ValueError('fixture refusal')
        storage = np.ones((3, 3), dtype='f4')
        storage[:, :2] = self.vertices
        fn = bench.runners(storage, None, 'float32', refuses)['earstrip/e2e']
        bench.validate(storage[:, :2], None, fn())  # Consumer-compatible fallback.
        self.assertEqual(fn.fallback_count, 1)
        with self.assertRaisesRegex(AssertionError, 'fallback occurred'):
            bench.reject_fallback(fn)

    def test_fixture_matrix(self):
        cases = list(bench.fixtures())
        self.assertEqual(len(cases), 38)
        self.assertEqual(len({name for name, _, _ in cases}), len(cases))


class BackendTests(unittest.TestCase):
    def test_all_baseline_fixtures(self):
        self.check_fixtures(None)

    @unittest.skipIf(candidate is None, 'candidate not installed yet')
    def test_all_candidate_fixtures(self):
        self.check_fixtures(candidate)

    def check_fixtures(self, triangulate):
        for name, vertices, ends in bench.fixtures():
            for dtype in ('float32', 'float64'):
                storage = np.ones((len(vertices), 3), dtype=dtype)
                storage[:, :2] = vertices
                original = storage.copy()
                for backend, fn in bench.runners(storage, ends, dtype, triangulate).items():
                    with self.subTest(fixture=name, dtype=dtype, backend=backend):
                        output = fn()
                        bench.reject_fallback(fn)
                        bench.validate(storage[:, :2], ends, output)
                        self.assertEqual(np.asarray(output).dtype, np.dtype('u4'))
                        np.testing.assert_array_equal(original, storage)

    @unittest.skipIf(candidate is None, 'candidate not installed yet')
    def test_candidate_strides_and_output_lifetime(self):
        for dtype in ('f4', 'f8'):
            storage = np.ones((4, 3), dtype=dtype)
            storage[:, :2] = [[0, 0], [3, 0], [3, 2], [0, 2]]
            views = [storage[:, :2], storage[::-1, :2], storage[:, 1::-1],
                     np.asfortranarray(storage[:, :2]), storage[:, :2].copy()]
            for view in views:
                with self.subTest(dtype=dtype, strides=view.strides):
                    raw = candidate(view)
                    output = np.asarray(raw)
                    saved = output.copy()
                    del raw
                    # A later call must not overwrite or invalidate retained buffers.
                    candidate(view)
                    np.testing.assert_array_equal(output, saved)
                    bench.validate(view, None, output)
                    self.assertEqual(output.dtype, np.dtype('u4'))


if __name__ == '__main__':
    unittest.main()
