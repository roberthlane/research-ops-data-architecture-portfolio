# Third-party dependencies and notices

Reviewed 2026-09-19 for this **source-only** candidate. The project code,
documentation, and generated fixtures use the MIT licence in `LICENSE`,
approved by the owner on 2026-09-19. Third-party tools retain their own terms.

## Shipped contents and runtime

`pyproject.toml` declares `dependencies = []`. Inspection of all Python imports
found only the standard library and local project modules. The quick start and
demo require no package installation, external dataset, service, or credentials.
No vendored code, Python/SQLite binaries, JavaScript bundle, model, font, image,
or dependency archive is included. There is therefore no separately bundled
third-party runtime dependency tree to redistribute in this source archive.

| Component | Use and terms | Release treatment |
| --- | --- | --- |
| Python standard library | PSF licence and notices for incorporated software; [official terms](https://docs.python.org/3/license.html) | Installed by the reviewer, not bundled. A future interpreter distribution needs its own complete notices. |
| SQLite through Python `sqlite3` | SQLite core is public domain; [upstream statement](https://www.sqlite.org/copyright.html) | System/interpreter component, not bundled. Extensions or binary distributions can have additional terms. |
| setuptools | Optional package build backend (`setuptools>=69`), MIT; [upstream licence](https://github.com/pypa/setuptools/blob/main/LICENSE) | Not needed by the demo and not installed or bundled by this release. Range is not a lockfile; bundled/vendor components must be inventoried if a build environment is later redistributed. |
| actions/checkout | CI tool, MIT; [licence at pinned revision](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE) | Referenced by immutable commit, fetched by GitHub Actions, not bundled. |
| actions/setup-python | CI tool, MIT; [licence at pinned revision](https://github.com/actions/setup-python/blob/ece7cb06caefa5fff74198d8649806c4678c61a1/LICENSE) | Referenced by immutable commit, fetched by GitHub Actions, not bundled. |

The two CI actions identify GitHub, Inc. and contributors as copyright holders.
Their dependency bundles and the hosted runner are outside this source archive.
The pinned source archives' cached dependency notices were also inspected:
24 notices for checkout and 48 for setup-python. The declared licence families
are MIT, Apache-2.0, ISC, and 0BSD. Four cache entries marked `other` contain
MIT text (`@actions/http-client` versions and `concat-map`); those were reviewed
rather than treated as cleared by the classifier. See upstream
[checkout notices](https://github.com/actions/checkout/tree/3d3c42e5aac5ba805825da76410c181273ba90b1/.licenses)
and [setup-python notices](https://github.com/actions/setup-python/tree/ece7cb06caefa5fff74198d8649806c4678c61a1/.licenses).
This is a review of upstream cached notices, not an independent complete SBOM
of the runner or a reconstruction of bundled JavaScript. Preserve all relevant
upstream notices if redistributing those components. CI execution uses GitHub's
service terms and account settings; no cloud run is asserted by local tests.

Git and `make` are optional developer tools, not shipped runtime dependencies.
The Markdown diagrams are text declarations; no Mermaid implementation is
bundled. SQL Server/Azure SQL are optional proprietary validation environments,
not supplied with this sample and not necessary to run the local demo.

## Borrowed material and fixture rights

The selected source and its three baseline commits contained no identified
external code attribution, imported corpus, or copied document assets. That is
an inspection finding, not proof of line-by-line originality. No third-party
code notice was removed. The baseline had no root project licence.

Fixture provenance is documented in `docs/synthetic-data-provenance.md`. All CSVs
can be regenerated from local constants and arithmetic. Known borrowed material
or additional rights restrictions, if later identified, require review before
release; a new MIT file cannot supersede another party's rights.

## Why MIT

MIT permits inspection, reuse, modification, and commercial distribution while
requiring retention of its copyright and permission notice. This fits a small
employment work sample whose purpose is easy technical review and reuse.
It does not require publishing downstream modifications and has no express
patent grant. See the [OSI licence text](https://opensource.org/license/mit).
The holder line is `Copyright (c) 2026 Robert Lane`. The owner approved this
licence and attribution on 2026-09-19.
