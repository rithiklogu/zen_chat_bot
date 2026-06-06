from sqlmodel import SQLModel, Session, create_engine

from app.database.models import *

from app.env import env

DATABASE_URL = f"postgresql://{env.POSTGRES_USER}:{env.POSTGRES_PASSWORD}@{env.POSTGRES_HOST}:{env.POSTGRES_PORT}/{env.POSTGRES_DB}"

engine = create_engine(DATABASE_URL, echo=False)


def init_db():
    """
    Initializes the database by creating all tables from SQLModel metadata.
    """
    SQLModel.metadata.create_all(bind=engine)


def get_session():
    with Session(engine) as session:
        yield session


def get_open_session():
    try:
        db = Session(engine, expire_on_commit=False, autocommit=False)
        return db
    finally:
        db.close()


if __name__ == "__main__":
    init_db()
