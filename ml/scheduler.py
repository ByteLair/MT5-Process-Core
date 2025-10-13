from apscheduler.schedulers.blocking import BlockingScheduler
import subprocess

def retrain():
    subprocess.run(["python","-u","ml/train_worker.py"], check=False)

sched = BlockingScheduler()
sched.add_job(retrain, "cron", hour=0)  # 00:00 diário
sched.start()
