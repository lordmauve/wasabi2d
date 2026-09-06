"""Check release versions and assets without importing the graphics engine."""
import ast
from email.parser import BytesParser
from pathlib import Path
import sys
import tarfile
import zipfile

from packaging.version import Version

expected = Version(sys.argv[1].removeprefix('v'))
wheel, = Path('dist').glob('*.whl')
sdist, = Path('dist').glob('*.tar.gz')
with zipfile.ZipFile(wheel) as archive:
    names = set(archive.namelist())
    metadata, = (name for name in names if name.endswith('.dist-info/METADATA'))
    assert Version(BytesParser().parsebytes(archive.read(metadata))['Version']) == expected
    tree = ast.parse(archive.read('wasabi2d/__version__.py'))
    assignment, = (node for node in tree.body if isinstance(node, ast.Assign))
    assert Version(ast.literal_eval(assignment.value)) == expected
    assets = {
        path.as_posix()
        for directory in ('wasabi2d/data', 'wasabi2d/glsl')
        for path in Path(directory).rglob('*') if path.is_file()
    }
    assert assets and assets <= names, assets - names
with tarfile.open(sdist) as archive:
    members = archive.getnames()
    metadata, = (name for name in members if name.count('/') == 1 and name.endswith('/PKG-INFO'))
    assert Version(BytesParser().parsebytes(archive.extractfile(metadata).read())['Version']) == expected
    assert any(name.endswith('/wasabi2d/__version__.py') for name in members)
print(f'Checked sdist, wheel, generated version, and {len(assets)} package assets: {expected}')
