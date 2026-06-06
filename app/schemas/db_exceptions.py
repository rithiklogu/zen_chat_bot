from psycopg2 import errors as pg_errors
from sqlmodel import Session
from sqlalchemy.exc import (
    IntegrityError,
    OperationalError,
    DataError,
    ProgrammingError,
    InterfaceError,
    DatabaseError,
    TimeoutError,
    DisconnectionError,
)
from app.schemas.exceptions import AppException, AppError

from logger.log import log

def handle_db_exception(e: Exception, db:Session =None) -> None:
    if db:
        db.rollback()

    log.exception("Database error: %s", str(e))

   
    if isinstance(e, IntegrityError):
        orig = getattr(e, "orig", None)

        if isinstance(orig, pg_errors.UniqueViolation):
            raise AppException(AppError.DB_DUPLICATE_ENTRY, str(orig)) from e

        if isinstance(orig, pg_errors.ForeignKeyViolation):
            raise AppException(AppError.DB_FOREIGN_KEY_VIOLATION, str(orig)) from e

        if isinstance(orig, pg_errors.NotNullViolation):
            raise AppException(AppError.DB_NULL_CONSTRAINT_VIOLATION, str(orig)) from e

        if isinstance(orig, pg_errors.CheckViolation):
            raise AppException(AppError.DB_CHECK_CONSTRAINT_VIOLATION, str(orig)) from e

        # Fallback for any other integrity error
        raise AppException(AppError.DATABASE_INTEGRITY_ERROR, str(e)) from e

    if isinstance(e, DataError):
        raise AppException(AppError.DB_INVALID_DATA, str(getattr(e, "orig", e))) from e

   
    if isinstance(e, (OperationalError, DisconnectionError)):
        raise AppException(AppError.DB_CONNECTION_ERROR, str(e)) from e

   
    if isinstance(e, TimeoutError):
        raise AppException(AppError.DB_TIMEOUT, str(e)) from e

    
    if isinstance(e, InterfaceError):
        raise AppException(AppError.DB_CONNECTION_ERROR, str(e)) from e

   
    if isinstance(e, ProgrammingError):
        raise AppException(AppError.DB_QUERY_ERROR, str(e)) from e

   
    if isinstance(e, DatabaseError):
        raise AppException(AppError.DB_QUERY_ERROR, str(e)) from e

    # Not a DB error — re-raise as-is
    raise e