import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hard-to-guess-string'
    
    # Priority: Environment Variable -> Azure Persistent Storage -> Local SQLite
    db_url = os.environ.get('DATABASE_URL')
    if db_url and db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)
        
    if db_url:
        SQLALCHEMY_DATABASE_URI = db_url
    elif os.environ.get('WEBSITE_HOSTNAME'):
        # We are in Azure, use the persistent /home directory for SQLite
        home_data = '/home/data'
        if not os.path.exists(home_data):
            # This would usually be handled by a startup script, but we'll fallback here
            SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance/app.db')
        else:
            SQLALCHEMY_DATABASE_URI = 'sqlite:////home/data/app.db'
    else:
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'instance/app.db')
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
