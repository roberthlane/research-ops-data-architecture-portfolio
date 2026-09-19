# Third-party notices

The project code, documentation, and synthetic fixtures use the MIT licence.
No external dataset, document corpus, binary, or dependency bundle is vendored.

| Component | Use | Upstream terms |
| --- | --- | --- |
| Python standard library | Runtime | [PSF and incorporated notices](https://docs.python.org/3/license.html) |
| SQLite | Runtime via Python | [Public-domain core](https://www.sqlite.org/copyright.html) |
| setuptools | Optional build backend | [MIT](https://github.com/pypa/setuptools/blob/main/LICENSE) |
| Ruff | Development lint/format | [MIT](https://github.com/astral-sh/ruff/blob/main/LICENSE) |
| mypy | Development type checking | [MIT](https://github.com/python/mypy/blob/master/LICENSE) |
| build | Development package build | [MIT](https://github.com/pypa/build/blob/main/LICENSE) |
| GitHub checkout/setup-python actions | CI | [checkout MIT](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE), [setup-python MIT](https://github.com/actions/setup-python/blob/ece7cb06caefa5fff74198d8649806c4678c61a1/LICENSE) |
| SQL Server Developer container | Optional integration test | [Microsoft container terms/setup](https://learn.microsoft.com/en-us/sql/linux/quickstart-install-connect-docker?view=sql-server-ver17) |

These tools are fetched separately and retain their own dependency notices and terms.
The pinned Actions sources include transitive notices; Python distributions and the
SQL Server image have their own bundled components. The project MIT licence does not
relicense those components. No interpreter, runner, container, or build environment
is redistributed in the source package.
