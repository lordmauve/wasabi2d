import io
import os.path
from setuptools import setup, find_packages


path = os.path.join(os.path.dirname(__file__), 'README.md')
with io.open(path, encoding='utf8') as f:
    LONG_DESCRIPTION = f.read()


setup(
    name='wasabi2d',
    version='1.0.0',
    description="A convenient 2D OpenGL games framework",
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://github.com/lordmauve/wasabi2d',
    author='Daniel Pope',
    author_email='mauve@mauveweb.co.uk',
    packages=find_packages(include='wasabi2d*'),
    package_data={'wasabi2d': ['data/*']},
    install_requires=open('requirements.txt').read().splitlines(),
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Education',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python :: 3.6',
        'Topic :: Education',
        'Topic :: Games/Entertainment',
    ],
    test_suite='tests'
)
