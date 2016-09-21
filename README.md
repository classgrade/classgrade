# classgrade

Peer grading application (Django framework)

## Environment variables:

By default, the db is a postgres database. You can change it (for development purposes for instance) in `classgrade/settings.py`. If you use the default database, you need to create a postgres database and setup the correspondig environment variables:   
- `CG_DATABASE_NAME`: database name  
- `CG_DATABASE_USER`: database user  
- `CG_DATABASE_PASSWORD`: database password  
- `CG_EMAIL_PASSWORD`: password of the email account 
