import subprocess

def run_commands():
    # Paths and commands
    flask_app_cmd = 'start cmd /k "cd C:\\Users\\bfreking\\OneDrive - Ever.Ag\\Desktop\\Ben\'s Tools\\PIGE && python main.py"'
    celery_worker_cmd = 'start cmd /k "cd C:\\Users\\bfreking\\OneDrive - Ever.Ag\\Desktop\\Ben\'s Tools\\PIGE && C:\\Users\\bfreking\\AppData\\Local\\anaconda3\\envs\\PIGE\\Scripts\\celery -A src.flaskapp.celery_worker worker --pool=solo -l info"'
    celery_beat_cmd = 'start cmd /k "cd C:\\Users\\bfreking\\OneDrive - Ever.Ag\\Desktop\\Ben\'s Tools\\PIGE && C:\\Users\\bfreking\\AppData\\Local\\anaconda3\\envs\\PIGE\\Scripts\\celery -A src.flaskapp.celery_worker beat --loglevel=info -s var/celery/celerybeat-schedule.db"'

    # Run Flask App
    subprocess.run(flask_app_cmd, shell=True)

    # Run Celery Worker 1
    subprocess.run(celery_worker_cmd, shell=True)

    # Run Celery Beat
    subprocess.run(celery_beat_cmd, shell=True)

if __name__ == '__main__':
    run_commands()