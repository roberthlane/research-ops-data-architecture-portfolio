"""Run a disposable SQL Server integration test on an amd64 Linux Docker host."""

from __future__ import annotations

import argparse
import csv
import os
import secrets
import subprocess
import tempfile
import time
from pathlib import Path

from research_ops_architecture.models import TABLES
from research_ops_architecture.quality import require_quality, run_staging_checks
from research_ops_architecture.sqlite_mirror import connect_mirror, load_synthetic_csvs
from research_ops_architecture.synthetic import build_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]
SQL = ROOT / "sql/azure_sql"
IMAGE = "mcr.microsoft.com/mssql/server@sha256:4402d880dd4c34bfa7d8705e56a86cd6c88da80a1f6bbbe741f999e76264a090"


def literal(value: str) -> str:
    return "N'" + value.replace("'", "''") + "'" if value else "NULL"


def seed_sql(data_dir: Path) -> str:
    """Validate CSVs before importing into SQL Server's typed staging tables."""
    conn = connect_mirror()
    try:
        load_synthetic_csvs(conn, data_dir)
        require_quality(run_staging_checks(conn))
    finally:
        conn.close()
    lines = ["SET XACT_ABORT ON; BEGIN TRANSACTION;"]
    for name, spec in TABLES.items():
        with (data_dir / f"{name}.csv").open(newline="") as handle:
            for row in csv.DictReader(handle):
                values = ", ".join(literal(row[c]) for c in spec.columns)
                columns = ", ".join(spec.columns)
                lines.append(f"INSERT INTO stg.{name} ({columns}) VALUES ({values});")
    return "\n".join([*lines, "COMMIT TRANSACTION;\nGO"])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--accept-eula",
        action="store_true",
        help="Accept Microsoft's SQL Server container EULA for this disposable test",
    )
    args = parser.parse_args()
    if not args.accept_eula:
        parser.error("--accept-eula is required to start Microsoft's Developer edition container")
    arch = subprocess.check_output(
        ["docker", "info", "--format", "{{.Architecture}}"], text=True
    ).strip()
    if arch not in {"x86_64", "amd64"}:
        raise RuntimeError("This test requires an amd64 Linux Docker engine")
    name = "research-ops-test-" + secrets.token_hex(5)
    env = dict(os.environ, MSSQL_SA_PASSWORD="Test!" + secrets.token_urlsafe(24))
    env["SQLCMDPASSWORD"] = env["MSSQL_SA_PASSWORD"]
    # No host port, volume, external database, or credential is reused.
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-d",
            "--name",
            name,
            "-e",
            "ACCEPT_EULA=Y",
            "-e",
            "MSSQL_PID=Developer",
            "-e",
            "MSSQL_SA_PASSWORD",
            IMAGE,
        ],
        env=env,
        check=True,
        capture_output=True,
    )

    def sql(
        text: str, database: str = "ResearchOpsIntegration", expected_failure: bool = False
    ) -> str:
        result = subprocess.run(
            [
                "docker",
                "exec",
                "-i",
                "-e",
                "SQLCMDPASSWORD",
                name,
                "/opt/mssql-tools18/bin/sqlcmd",
                "-S",
                "localhost",
                "-U",
                "sa",
                "-C",
                "-b",
                "-r",
                "1",
                "-d",
                database,
            ],
            input=text,
            env=env,
            text=True,
            capture_output=True,
            timeout=90,
        )
        if (result.returncode != 0) != expected_failure:
            raise RuntimeError(result.stdout + result.stderr or "Unexpected SQL exit status")
        return result.stdout + result.stderr

    def load(day: str) -> None:
        sql(
            f"EXEC sys.sp_set_session_context @key=N'load_date', @value=N'{day}';\nGO\n"
            + (SQL / "05_elt_build_mart.sql").read_text()
        )

    try:
        for attempt in range(45):
            try:
                sql("SELECT 1;", "master")
                break
            except (RuntimeError, subprocess.TimeoutExpired):
                if attempt == 44:
                    raise RuntimeError("SQL Server did not become ready") from None
                time.sleep(2)
        sql("CREATE DATABASE ResearchOpsIntegration;", "master")
        for path in sorted(SQL.glob("0[0-3]_*.sql")):
            sql(path.read_text())
        with tempfile.TemporaryDirectory() as tmp:
            build_synthetic_dataset(tmp)
            sql(seed_sql(Path(tmp)))
        core = (SQL / "04_elt_load_core.sql").read_text()
        sql(core)
        load("2026-07-01")
        sql("""
            IF (SELECT COUNT(*) FROM mart.fact_request_lifecycle) <> 12 THROW 51000, 'Fact count', 1;
            IF (SELECT COUNT(*) FROM mart.dim_author) <> 48 THROW 51000, 'Initial dimension count', 1;
        """)
        sql(core)
        load("2026-07-01")
        sql("IF (SELECT COUNT(*) FROM mart.dim_author) <> 48 THROW 51000, 'Unchanged rerun', 1;")
        print("PASS SQL: schema, validated import, core/mart load, unchanged rerun")
        # Controlled attribute changes isolate SCD behavior from workflow event generation.
        sql(
            "UPDATE core.author_approval SET author_name=N'Demo Revised' WHERE author_approval_id='AUT-0001-01';"
        )
        load("2026-07-02")
        sql("""
            IF (SELECT COUNT(*) FROM mart.dim_author WHERE author_approval_id='AUT-0001-01') <> 2
                THROW 51000, 'Next-day version missing', 1;
            IF NOT EXISTS (SELECT 1 FROM mart.dim_author WHERE author_approval_id='AUT-0001-01'
                AND effective_start_date='2026-07-01' AND effective_end_date='2026-07-01' AND is_current=0)
                THROW 51000, 'Prior interval incorrect', 1;
        """)
        sql(
            "UPDATE core.author_approval SET author_name=N'Demo Revised Again' WHERE author_approval_id='AUT-0001-01';"
        )
        load("2026-07-02")
        sql("""
            IF (SELECT COUNT(*) FROM mart.dim_author WHERE author_approval_id='AUT-0001-01') <> 2
                THROW 51000, 'Same-day duplicate version', 1;
            IF NOT EXISTS (SELECT 1 FROM mart.dim_author WHERE author_approval_id='AUT-0001-01'
                AND author_name=N'Demo Revised Again' AND effective_start_date='2026-07-02' AND is_current=1)
                THROW 51000, 'Same-day change missing', 1;
        """)
        error = sql(
            "EXEC sys.sp_set_session_context @key=N'load_date', @value=N'2026-07-01';\nGO\n"
            + (SQL / "05_elt_build_mart.sql").read_text(),
            expected_failure=True,
        )
        if "Backdated dimension loads" not in error:
            raise RuntimeError("Unexpected backdated-load failure")
        sql(
            "IF (SELECT COUNT(*) FROM mart.dim_author) <> 49 THROW 51000, 'Failed load altered dimensions', 1;"
        )
        print("PASS SQL: next-day, same-day, and rejected backdated SCD loads")
        sql("DELETE FROM stg.dashboard_exports;")
        load("2026-07-02")
        sql("""
            IF (SELECT COUNT(*) FROM mart.fact_request_lifecycle) <> 12 THROW 51000, 'Staging-dependent fact count', 1;
            IF EXISTS (
                SELECT 1 FROM mart.fact_request_lifecycle f CROSS APPLY (
                    SELECT COUNT(*) AS total FROM core.author_approval a WHERE a.request_id=f.request_id
                ) c WHERE f.total_authors<>c.total
            ) THROW 51000, 'Core count mismatch', 1;
        """)
        print("PASS SQL: lifecycle facts are independent of dashboard staging")
        for path in sorted(SQL.glob("0[6-7]_*.sql")):
            sql(path.read_text())
        sql(
            "CREATE USER portfolio_reader WITHOUT LOGIN; ALTER ROLE research_ops_reader ADD MEMBER portfolio_reader;"
        )
        sql("""
            EXECUTE AS USER='portfolio_reader';
            EXEC rpt.usp_request_lifecycle_summary;
            EXEC rpt.usp_stale_dashboard_exports;
            SELECT TOP (1) * FROM rpt.vw_open_approval_queue;
            REVERT;
        """)
        for table in ("stg.requests", "core.request"):
            denied = sql(
                f"EXECUTE AS USER='portfolio_reader'; SELECT * FROM {table};", expected_failure=True
            )
            if "permission was denied" not in denied:
                raise RuntimeError("Expected direct table SELECT denial")
        # Real timestamps at the 2-calendar-day boundary, observed through the procedure.
        sql("""
            INSERT INTO stg.dashboard_exports
              (request_id,workflow_type,review_title,review_identifier,total_authors,approved_authors,
               outstanding_authors,current_status,last_exported_at)
            VALUES ('BOUNDARY-OK','copublication','Synthetic','BOUNDARY-OK',0,0,0,'sent',
                    DATEADD(day,-2,CONVERT(datetime2(0),CONVERT(date,SYSUTCDATETIME())))),
                   ('BOUNDARY-OLD','copublication','Synthetic','BOUNDARY-OLD',0,0,0,'sent',
                    DATEADD(second,-1,DATEADD(day,-2,CONVERT(datetime2(0),CONVERT(date,SYSUTCDATETIME())))));
            CREATE TABLE #stale(request_id varchar(20), review_identifier varchar(30), review_title nvarchar(300),
                                current_status varchar(40), last_exported_at datetime2(0), export_age_days int);
            INSERT #stale EXEC rpt.usp_stale_dashboard_exports @max_age_days=2;
            IF (SELECT COUNT(*) FROM #stale) <> 1 OR NOT EXISTS(SELECT 1 FROM #stale WHERE request_id='BOUNDARY-OLD')
                THROW 51000, 'Freshness calendar boundary', 1;
        """)
        print("PASS SQL: reader execution, direct-table denial, freshness boundary")
        print(sql("SELECT @@VERSION AS engine_version;").strip())
    finally:
        # Only this invocation's random, disposable container can be removed.
        subprocess.run(["docker", "rm", "-f", name], check=True, capture_output=True)


if __name__ == "__main__":
    main()
