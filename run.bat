@echo off

:: Start Flask App
start cmd /k "cd C:\Users\bfreking\PycharmProjects\Otto && python run.py"

:: Start Celery Worker 1
start cmd /k "cd C:\Users\bfreking\OneDrive - Ever.Ag\Desktop\Ben's Tools\PIGE && C:\Users\bfreking\AppData\Local\anaconda3\envs\PIGE\Scripts\celery -A src.flaskapp.celery_worker worker --pool=solo -l info"

:: Start Celery Beat
start cmd /k "cd C:\Users\bfreking\OneDrive - Ever.Ag\Desktop\Ben's Tools\PIGE && C:\Users\bfreking\AppData\Local\anaconda3\envs\PIGE\Scripts\celery -A src.flaskapp.celery_worker beat --loglevel=info -s var/celery/celerybeat-schedule.db"
