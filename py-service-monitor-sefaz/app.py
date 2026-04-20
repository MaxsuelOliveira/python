import schedule
import time
from core.get import monitorar

def job():
    monitorar()
    
def main():  
    schedule.every(1).minutes.do(job)
    
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main()