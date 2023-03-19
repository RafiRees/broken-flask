from . import DB_NAME, db, app
from .auth import auth
from .dash_app.dashboard import app_layout
from .views import views
from .models import User

from .dash_app.dashboard import app_dash

from os import path

from flask_login import LoginManager
from dash_bootstrap_components import themes
from dash import Dash

def create_app():
    app.config['SECRET_KEY'] = 'rafis app'
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_NAME}'
    db.init_app(app)

    app.register_blueprint(views, url_prefix='/')
    app.register_blueprint(auth, url_prefix='/')

    with app.app_context():
        db.create_all()

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(int(id))
    
    # create the Dash app and register it with Flask
    app_dash.layout = app_layout

    return app


def create_database(app):
    if not path.exists('website/' + DB_NAME):
        db.create_all(app=app)
        print('Created Database!')
