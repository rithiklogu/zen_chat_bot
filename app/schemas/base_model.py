from typing import Any, Generic, Literal, Optional,  TypeVar, Sequence
from fastapi import status as e_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import and_, or_
from sqlmodel.sql.expression import Select, SelectOfScalar, col


_T = TypeVar('_T')
SearchOrderDirection = Literal['desc', 'asc']


class AppResponse(BaseModel, Generic[_T]):
    status_code: int = e_status.HTTP_200_OK
    """ HTTP Response Status Code. Defaults to 200 (OK) """
    message: str | None = "OK"
    data: Optional[_T] = None
    """ HTTP Response Status Code. Defaults to 200 (OK) """

    def json(self, **kwargs: Any) -> JSONResponse:
        """ Return a JSONResponse object representation of this model. """
        return JSONResponse(status_code=self.status_code, content=jsonable_encoder(self))

    def model_dump(self, *args: Any, **kwargs: Any):
        """
        Exclude unset values on responses default to true. <br>
        @override
        """
        if kwargs and kwargs.get("exclude_none") is not None:
            kwargs["exclude_none"] = False
        return super().model_dump(*args, **kwargs)

    def __new__(cls, *args: Any, **kwargs: Any) -> JSONResponse:
        instance = super().__new__(cls)
        instance.__init__(**kwargs)  # Manually initialize for pydantic model.

        # Return the appropriate JSONResponse.
        return instance.json()

class AuthResponse(AppResponse):
    """ Extends AppResponse to require a JWT Auth token & token type. """
    access_token: str = Field(examples=["eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9"])
    token_type: str = Field(examples=["bearer"], default="bearer")


class SearchRequest(BaseModel):
    search: Optional[str] = None
    """ Value which will be searched for """
    search_cols: Optional[tuple[Any, ...]] = None
    """ Columns or SQLAlchemy functions to search against. Required to perform a search. """
    order_direction: Optional[SearchOrderDirection] = None
    """ Order results by descending or ascending. Must be set with `order_col` to order results. """
    order_col: Any = None
    """ Assign a column reference `Example.my_col`. Must be set with `order_direction` to order results. """
    filter_cols: Optional[tuple[Any, ...]] = None
    "Filter the rows based on list of columns given."
    filter_on_value: Optional[tuple[Any, ...]] = None
    "The values with the row that has to be filtered against"

    def apply(self, stmt: Select | SelectOfScalar) -> Select | SelectOfScalar:
        # If search_cols is not provided or is of length 0, the search function will not be performed.
        search_value = self.search.strip() if self.search else ""
        if self.search_cols and search_value:
            search_terms = [term for term in search_value.split() if term]

            if len(search_terms) == 1:
                # Single word search, use case-insensitive partial matching.
                conditions = or_(*(
                    search_col.ilike(f"%{search_value}%")
                    for search_col in self.search_cols
                ))
            else:
                # Multi-word search supports partial matches for each token.
                conditions = or_(*(
                    search_col.ilike(f"%{term}%")
                    for term in search_terms
                    for search_col in self.search_cols
                ))

            stmt = stmt.where(conditions)

        # If order direction and column are not provided, the results will not be ordered.
        if self.order_direction is not None and self.order_col is not None:
            _col = col(self.order_col)
            order = _col.desc() if self.order_direction == 'desc' else _col.asc()
            stmt = stmt.order_by(order)

        # If filter_on and filter_on_value are not provided, the results will not be ordered.
        if self.filter_cols is not None and self.filter_on_value is not None:
            
            conditions = (
                col(filter_column) == value
                for filter_column, value in
                zip(self.filter_cols, self.filter_on_value))

            stmt = stmt.where(and_(*conditions))
        return stmt


class PagedRequest(BaseModel):
    """ Reqeust model to get the page and size of a paginated request. """
    page: int = Field(ge=1)
    """ Page of the results """
    size: int = Field()
    """ Size of the pages """


class PagedResponse(PagedRequest, Generic[_T]):
    """ Response schema for any paged API. """
    total: int = Field(ge=0)
    """ Total number of potential results across all pages """
    results: Sequence[_T]
    """ The results on this given page """
