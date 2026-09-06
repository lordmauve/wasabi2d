"""One-off release migration, safe to rerun without editing existing releases."""
import json
from pathlib import Path
import subprocess


def gh(*args, **kwargs):
    return subprocess.check_output(['gh', *args], text=True, **kwargs)


def create(tag, title, body, *, prerelease=False, target=None):
    args = ['release', 'create', tag, '--title', title, '--notes-file', '-', '--latest=false']
    args += ['--target', target] if target else ['--verify-tag']
    if prerelease:
        args.append('--prerelease')
    print(gh(*args, input=body))


existing = {r['tagName'] for r in json.loads(gh('release', 'list', '--limit', '1000', '--json', 'tagName'))}
for release in json.loads(Path('.github/release-history.json').read_text()):
    if release['tag'] not in existing:
        create(release['tag'], release['version'], release['body'], prerelease=release['prerelease'])

# Releases created by GITHUB_TOKEN do not trigger release workflows. Explicit
# workflow_dispatch does, and tests the same tag checkout/build/publish path.
tag = 'v1.5.0a2.dev0'
if tag not in existing:
    create(tag, '1.5.0a2.dev0', '''Development release to exercise the uv / flit_scm release pipeline.

* Derive package and documentation versions from Git tags, generating `wasabi2d/__version__.py` at build time.
* Build and publish using uv when a version tag is pushed or a GitHub Release is published.
* Generate the Sphinx changelog from GitHub Releases, with historical release notes preserved.
* Includes development since 1.5.0a1, including nine-patch sprites and expanded documentation.
''', prerelease=True, target=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip())
gh('workflow', 'run', 'release.yml', '--ref', 'master', '-f', f'tag={tag}')
