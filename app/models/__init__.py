from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

# Import all models to ensure they're registered with SQLAlchemy
from .user import User
from .category import Category  
from .document import Document
from .role import Role
from .permission import Permission
