from rq import Worker

from app import models
from app.task_queue import DOCUMENT_PROCESSING_QUEUE, get_redis_connection


def main() -> None:
    connection = get_redis_connection()
    worker = Worker([DOCUMENT_PROCESSING_QUEUE], connection=connection)
    worker.work()


if __name__ == "__main__":
    main()
