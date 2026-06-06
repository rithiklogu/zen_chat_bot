from app.database.column_definictions import *

class User(User_cols, table=True):
    __tablename__="User"
    