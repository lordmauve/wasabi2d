from pytest import fixture
from pathlib import Path

from wasabi2d.scene import HeadlessScene


ROOT = Path(__file__).parent


@fixture
def scene():
    """Fixture to create a new Scene object for use in a test."""
    scene = HeadlessScene(rootdir=ROOT)
    yield scene
    scene.release()


@fixture
def tilemap(scene):
    return scene.layers[0].add_tile_map()

