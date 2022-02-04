from flaskapp import db
import json
import sqlalchemy
from sqlalchemy.types import TypeDecorator

ITEMS_PER_PAGE = 9
SIZE=256

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
    
    
class Article(db.Model):
    id = db.Column(db.Integer,primary_key=True)
    title = db.Column(db.String(120), unique=False, nullable=True)
    description = db.Column(db.Text, nullable=True)
    source = db.Column(db.String(120), unique=False, nullable=True)
    firstAuthor = db.Column(db.String(120), unique=False, nullable=True)
    yearPublished = db.Column(db.Integer, unique=False, nullable=True)
    numberOfAuthors = db.Column(db.Integer, unique=False, nullable=True)
    journal = db.Column(db.String(120) , unique=False, nullable=True)
    volume = db.Column(db.Integer, unique=False,nullable = True)
    pages = db.Column(db.Integer, unique=False,nullable =True)
    DOI = db.Column(db.String(120), unique=True, nullable=True)
    eprint = db.Column(db.String(120), unique=True,nullable=True)
    bibtex = db.Column(TextPickleType())
    def __repr__(self):
        return '<Article %r>' % self.title
    