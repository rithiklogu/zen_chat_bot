from datetime import datetime
from uuid import uuid4,UUID
from sqlmodel import SQLModel, Field, select
from sqlalchemy import text, func, ScalarResult
from sqlalchemy.engine import TupleResult
from sqlalchemy.ext.asyncio import AsyncSession
from typing import TypeVar, Union, Sequence, Any, Type, final
from sqlmodel import Session, or_
from sqlalchemy.sql._typing import _ColumnExpressionArgument

from app.schemas.base_model import PagedRequest, PagedResponse, SearchRequest

_T = TypeVar("_T")
_Self = TypeVar("_Self", bound="BaseMixin")

class TimestampMixin(SQLModel):
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP")}
    )
    updated_at: datetime = Field(
        default_factory=datetime.utcnow,
        nullable=False,
        sa_column_kwargs={"server_default": text("CURRENT_TIMESTAMP"), "onupdate": text("CURRENT_TIMESTAMP")}
    )

class UUIDMixin(SQLModel):
    id: UUID = Field(
        default_factory=lambda: (uuid4()),
        primary_key=True,
        index=True,
        nullable=False,
        sa_column_kwargs={"unique": True}
    )

# Soft delete / active flags
class ActiveMixin(SQLModel):
    is_active: bool = Field(default=True)


class BaseMixin(SQLModel):
    @classmethod
    @final
    def count(cls, db: Session, *where: Union[_ColumnExpressionArgument[bool], bool]) -> int:
        return db.exec(select(func.count()).select_from(cls).where(*where)).one()

    @classmethod
    def select_by_id(cls: Type[_T], db: Session, u_id: Union[int, str]) -> _T | None:
        return cls.select(db, cls.id == u_id).first()
    
    @classmethod
    def select_paged(
            cls: Type[_Self], db: Session, page_request: PagedRequest,
            joins: Union[tuple[Type[SQLModel], ...], tuple[tuple[Type[SQLModel], bool], ...]] = None,
            use_distinct: bool = False,
            is_outer: bool = False,
            search_request: SearchRequest = None,
            where: tuple[Union[_ColumnExpressionArgument[bool], bool], ...] = ()) -> PagedResponse[_Self]:
        """ Get a paged selection of rows from this model, refined by any given where conditions """
        skip = (page_request.page - 1) * page_request.size  # Calculate the number of records to skip
        stmt = select(cls)
        if use_distinct:
            stmt = stmt.distinct(cls.id)

        if joins is not None:
            for join in joins:
                if not isinstance(join, tuple):
                    join = (join,)
                stmt = stmt.join(*join, isouter=is_outer)

        stmt = stmt.where(*where)
        if search_request:
            stmt = search_request.apply(stmt)

        total = db.exec(select(func.count()).select_from(stmt.subquery())).one()
        results = db.exec(stmt.offset(skip).limit(page_request.size)).all()
        if page_request.size > len(results):
            page_request.size = len(results)

        return PagedResponse(
            **page_request.model_dump(),
            total=total,
            results=results
        )

    @classmethod
    def select_by_ids(
        cls, db: Session, u_ids: Sequence[Union[int, str]],
        *where: Union[_ColumnExpressionArgument[bool], bool]
    ) -> Sequence[_T]:
        return [] if not u_ids else cls.select(db, or_(*[cls.id == u_id for u_id in u_ids]), *where).all()

    @classmethod
    @final
    def select(cls: Type[_T], db: Session, *where: Union[_ColumnExpressionArgument[bool], bool]) \
            -> TupleResult[_T] | ScalarResult[_T]:
        return db.exec(select(cls).where(*where))
    
    @classmethod
    @final
    async def select_async(cls: Type[_T], db: AsyncSession, *where: Union[_ColumnExpressionArgument[bool], bool]) \
            -> ScalarResult[_T]:
        obj = await db.execute(select(cls).where(*where))
        return obj.scalars().all()
    
    @classmethod
    def upsert_deep(cls, *args: Any) -> _T:
        raise Exception('Function not implemented')

    @classmethod
    @final
    def upsert(cls, db: Session, data: dict, u_id: Any = None, exclude: Sequence = None) -> _T:
        exclude = exclude or []
        data = data.copy()
        for key in ['id', 'created_at', 'updated_at'] + list(exclude):
            data.pop(key, None)

        obj = cls.select_by_id(db, u_id) if u_id else None
        if obj:
            for key, value in data.items():
                setattr(obj, key, value)
        else:
            obj = cls(**data)  # type: ignore

        db.add(obj)
        # db.commit()
        # db.refresh(obj)
        return obj
    
    def db_delete(self, db: Session) -> None:
        """
        By default, simply calls `db.delete(self)`. If a more complex delete function that applies across multiple
        tables is needed, override this function.
        """
        db.delete(self)
