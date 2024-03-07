from celery import Celery
import sqlite3
from celery.schedules import crontab
from celery.signals import task_failure

# Called by run.bat to start celery worker and beat
app = Celery('worker',
             broker='sqla+sqlite:///var/celery/celerydb.sqlite',
             include=['src.flaskapp.routes.tasks']

             )

app.conf.update(
    result_backend='db+sqlite:///var/celery/celeryresults.sqlite'
)

app.conf.beat_schedule = {
    #'increment-counter-every-second': {
    #    'task': 'src.webapp.tasks.routes.increment_counter',  # Correct tasks name
    #    'schedule': 250.0,  # Every 1 second
    #},
    'daily-tasks-at-9-30': {
        'task': 'src.flaskapp.routes.tasks.run_datamart_scrapper',  # Replace with your actual tasks name
        'args': ('AFTERNOON',),
        'schedule': 30.0,
        #'schedule': crontab(hour=19, minute=30), # 9:30 AM
    },
}