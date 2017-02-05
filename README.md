# classgrade

Peer grading application (Django framework).  

A professor defines an assignment by giving:  
- a description 
- a list of assigned students 
- a submission and a grading deadlines
- a number of graders for an assignment  
- a number of questions and the associated problem statements and coefficients   

Students upload their assignment, and grade X classmate assignments. Students can rate how they were evaluated. 

The professor can take the lead on grading some students. 

## How to make the app run locally?

Requirements:
- Python 3
- Python packages listed in ``requirements.txt`  

To set up the app locally:    
1. Install required packages  
2. Create a Postgres database. If you want, you can change it (for development purposes for instance) in `classgrade/settings.py`. 
3. Define the following environment variables:  
    - `CG_DATABASE_NAME`: database name  
    - `CG_DATABASE_USER`: database user  
    - `CG_DATABASE_PASSWORD`: database password  
    - `CG_EMAIL`: email   
    - `CG_EMAIL_PASSWORD`: password of the email account  
    - `CG_WORKING_ENV`: working environment, can be set to `DEV` or `PROD`
4. Run migrations: `python manage.py migrate`  

To run the app locally: `python manage.py runserver`  

## How to deploy the app on heroku  

...Soon...
