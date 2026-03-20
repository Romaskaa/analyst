from faststream import FastStream
from faststream.rabbit import RabbitBroker, RabbitQueue

from ..core.schemas import QueueData
from ..settings import settings

broker = RabbitBroker(settings.rabbit.url)
app = FastStream(broker)

main_queue = RabbitQueue("main_queue")
queue_1 = RabbitQueue("queue_1")
queue_2 = RabbitQueue("queue_2")
queue_3 = RabbitQueue("queue_3")

async def _forward(data: QueueData) -> None:
    await broker.publish(data.model_dump(mode="json"), queue="main_queue")

@broker.subscriber("queue_1")
async def subscribe_queue_1(data: QueueData) -> None:
    await _forward(data)


@broker.subscriber("queue_2")
async def subscribe_queue_2(data: QueueData) -> None:
    await _forward(data)


@broker.subscriber("queue_3")
async def subscribe_queue_3(data: QueueData) -> None:
    await _forward(data)
