from flask import Flask
from flask_sqlalchemy import SQLAlchemy 
from .constants import DB_URI

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = DB_URI + '?check_same_thread=False'
app.config['SECRET_KEY'] = '5791628bb0b13ce0c676dfde2aaa0ba245'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db=SQLAlchemy(app)

@app.before_first_request
def initialize_database():
    # Create all tables defined in the models
    db.create_all()
    
    


from flaskapp import routes