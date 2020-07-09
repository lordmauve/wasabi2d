from pathlib import Path
from setuptools import setup, find_packages

root = Path(__file__).parent
LONG_DESCRIPTION = root.joinpath('README.md').read_text(encoding='utf8')


def package_data(dirname):
    w2d = root / 'wasabi2d'
    data_dir = w2d / dirname
    yield f'{dirname}/*'
    for path in data_dir.glob('**/'):
        yield f'{path.relative_to(w2d)}/*'


setup(
    name='wasabi2d',
    version='1.4.0',
    description="A convenient 2D OpenGL games framework",
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://github.com/lordmauve/wasabi2d',
    author='Daniel Pope',
    author_email='mauve@mauveweb.co.uk',
    packages=find_packages(include='wasabi2d*'),
    package_data={'wasabi2d': [
        *package_data('data'),
        *package_data('glsl'),
    ]},
    install_requires=open('requirements.txt').read().splitlines(),
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Education',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Topic :: Education',
        'Topic :: Games/Entertainment',
    ],
    test_suite='tests'
)
