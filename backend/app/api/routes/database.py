import logging

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from app.core.security import ADMIN, get_current_user, hospital_scope, require_roles
from database.federated_db import get_federated_connection
from database.hospital_db import HOSPITAL_IDS, get_hospital_connection


logger = logging.getLogger("fedhealth.database")

router = APIRouter(
    prefix="/api/database",
    tags=["Database Explorer"]
)

admin_only = [Depends(require_roles(ADMIN))]

# Tables whose contents are never exposed row-by-row.
HIDDEN_TABLES = {"users"}

DATABASES = [
    (f"hospital_{hospital_id}_db",
     lambda hospital_id=hospital_id: get_hospital_connection(hospital_id))
    for hospital_id in HOSPITAL_IDS
] + [("federated_db", get_federated_connection)]


def _list_tables(connection):
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
              AND table_type = 'BASE TABLE'
            ORDER BY table_name
            """
        )

        return [row[0] for row in cursor.fetchall()]


def _row_count(connection, table_name):
    with connection.cursor() as cursor:
        cursor.execute(
            sql.SQL("SELECT COUNT(*) FROM {}").format(
                sql.Identifier(table_name)
            )
        )

        return cursor.fetchone()[0]


def _inspect(name, opener):
    connection = None

    try:
        connection = opener()

        tables = [
            {
                "name": table_name,
                "row_count": _row_count(connection, table_name)
            }
            for table_name in _list_tables(connection)
        ]

        return {
            "name": name,
            "status": "Connected",
            "table_count": len(tables),
            "tables": tables
        }

    except Exception:
        logger.exception("Database inspection failed for %s", name)

        return {
            "name": name,
            "status": "Unreachable",
            "table_count": 0,
            "tables": []
        }

    finally:
        if connection:
            connection.close()


@router.get("/health", dependencies=[Depends(get_current_user)])
def database_health():
    results = {}

    for name, opener in DATABASES:
        connection = None

        try:
            connection = opener()

            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")

            results[name] = "connected"

        except Exception:
            logger.warning("Health check failed for %s", name)
            results[name] = "unreachable"

        finally:
            if connection:
                connection.close()

    healthy = all(value == "connected" for value in results.values())

    return {
        "status": "healthy" if healthy else "degraded",
        "databases": results
    }


@router.get("/info", dependencies=admin_only)
def database_info():
    """Connection status, table names and row counts for every database."""
    return {
        "databases": [
            _inspect(name, opener) for name, opener in DATABASES
        ]
    }


@router.get("/tables", dependencies=admin_only)
def database_tables(
    current_user: dict = Depends(hospital_scope)
):
    hospital_id = current_user["hospital_id"]
    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        return {
            "hospital_id": hospital_id,
            "database": f"hospital_{hospital_id}_db",
            "tables": [
                {"table_name": name}
                for name in _list_tables(connection)
            ]
        }

    except Exception:
        logger.exception("Listing tables failed")
        raise HTTPException(
            status_code=500,
            detail="Unable to fetch database tables"
        )

    finally:
        if connection:
            connection.close()


@router.get("/table/{table_name}", dependencies=admin_only)
def database_table_rows(
    table_name: str = Path(..., max_length=64),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(hospital_scope)
):
    hospital_id = current_user["hospital_id"]

    if table_name in HIDDEN_TABLES:
        raise HTTPException(
            status_code=403,
            detail="This table cannot be browsed"
        )

    connection = None

    try:
        connection = get_hospital_connection(hospital_id)

        # Only names that really exist can reach the query below.
        if table_name not in _list_tables(connection):
            raise HTTPException(
                status_code=404,
                detail="Table not found"
            )

        with connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute(
                sql.SQL("SELECT * FROM {} LIMIT %s").format(
                    sql.Identifier(table_name)
                ),
                (limit,)
            )

            rows = cursor.fetchall()

        return {
            "hospital_id": hospital_id,
            "table": table_name,
            "total_rows": len(rows),
            "rows": rows
        }

    except HTTPException:
        raise

    except Exception:
        logger.exception("Reading table %s failed", table_name)
        raise HTTPException(
            status_code=500,
            detail="Unable to read table"
        )

    finally:
        if connection:
            connection.close()
