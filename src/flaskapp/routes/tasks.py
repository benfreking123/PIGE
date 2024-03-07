from ..celery_worker import app
from celery import group
from src.scrapper import datamart_scrapper
from var.config import Schedule

datamart_processor = datamart_scrapper.DatamartProcessor()


@app.task
def test():
    print('test')

@app.task()
def run_datamart_scrapper(schedule):
    try:
        Schedule.schedule.get(schedule)
    except:
        f'{schedule} is not a known schedule'


    slug_ids = Schedule.schedule.get(schedule)
    tasks_to_run = [run_datamart_slug_datamart.s(slug) for slug in slug_ids]
    task_group = group(tasks_to_run)
    result = task_group.apply_async()
    print(result)

@app.task
def run_datamart_slug_datamart(slug_id):
    """
    Runs each slug_id Datmart API pull
    """
    try:
        datamart_processor.scrap_slug(slug_id)
        msg = f'Running Datamart Auto Prints with slug_id {slug_id}'
        print(msg)
    except:
        msg = f'Failed to find Slug ID: {slug_id} in config class "Slugs"'
        print(msg)