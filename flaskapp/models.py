import uuid
import json
import sqlalchemy
from flaskapp import db
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import TypeDecorator
from sqlalchemy.orm import relationship
from .constants import SIZE
from sqlalchemy import create_engine, MetaData
from sqlalchemy_utils import UUIDType

engine = create_engine('sqlite:////tmp/test.db', echo = True)
meta = MetaData()


class TextPickleType(TypeDecorator):
    impl = sqlalchemy.Text(SIZE)

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(120), unique=False, nullable=True)
    def __repr__(self):
        return '<User %r>' % self.id
    
class Article(db.Model):
    __tablename__ = 'articles'
    id = db.Column(UUIDType(binary=False), primary_key=True, default=uuid.uuid4)
    title = db.Column(db.String(120), unique=False, nullable=True)
    description = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(120), unique=False, nullable=True)
    firstAuthor = db.Column(db.String(120), unique=False, nullable=True)
    yearPublished = db.Column(db.Integer, unique=False, nullable=True)
    numberOfAuthors = db.Column(db.Integer, unique=False, nullable=True)
    journal = db.Column(db.String(120) , unique=False, nullable=True)
    volume = db.Column(db.Integer, unique=False,nullable = True)
    pages = db.Column(db.Integer, unique=False,nullable =True)
    DOI = db.Column(db.String(120), unique=False, nullable=True)
    eprint = db.Column(db.String(120), unique=False,nullable=True)
    bibtex = db.Column(TextPickleType())

    user_id = db.Column(UUIDType(binary=False), db.ForeignKey('users.id'))

    def __repr__(self):
        return '<Article %r>' % self.title

meta.create_all(engine)