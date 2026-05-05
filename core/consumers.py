import json
import random
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)

WASTE_TYPES = [
    ('msw', 'Municipal Solid Waste (MSW)'),
    ('hazardous', 'Hazardous Waste'),
    ('organic', 'Organic Waste'),
    ('recyclable', 'Recyclable Waste'),
    ('liquid', 'Liquid Waste'),
    ('ewaste', 'Electronic Waste (E-waste)'),
    ('cd', 'Construction & Demolition Debris'),
    ('medical', 'Medical/Clinical Waste'),
    ('gaseous', 'Gaseous Waste'),
]

WASTE_WEIGHTS = [0.25, 0.05, 0.20, 0.20, 0.08, 0.07, 0.07, 0.05, 0.03]

PROPERTY_TYPES = [
    ('biodegradable', 'Biodegradable'),
    ('non_biodegradable', 'Non-biodegradable'),
    ('inert', 'Inert'),
]

PROPERTY_WEIGHTS = [0.40, 0.45, 0.15]


def classify_frame(_image_b64: str) -> dict:
    """Mock CV classifier. Replace with a real model (e.g. YOLO, MobileNet) here."""
    waste_type, waste_label = random.choices(WASTE_TYPES, weights=WASTE_WEIGHTS, k=1)[0]
    prop_type, prop_label = random.choices(PROPERTY_TYPES, weights=PROPERTY_WEIGHTS, k=1)[0]
    confidence = round(random.uniform(0.55, 0.99), 2)
    return {
        'waste_type': waste_type,
        'waste_type_label': waste_label,
        'properties': prop_type,
        'properties_label': prop_label,
        'confidence': confidence,
    }


class MonitoringConsumer(AsyncWebsocketConsumer):
    GROUP_NAME = 'monitoring'

    async def connect(self):
        await self.channel_layer.group_add(self.GROUP_NAME, self.channel_name)
        await self.accept()
        logger.debug('MonitoringConsumer connected: %s', self.channel_name)

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.GROUP_NAME, self.channel_name)
        logger.debug('MonitoringConsumer disconnected: %s', self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            await self.send(text_data=json.dumps({'error': 'Invalid JSON'}))
            return

        msg_type = data.get('type')
        if msg_type == 'classify_frame':
            image_b64 = data.get('image', '')
            result = classify_frame(image_b64)
            await self.send(text_data=json.dumps({
                'type': 'classification_result',
                **result,
            }))
        elif msg_type == 'broadcast_item':
            # Broadcast a newly persisted item to all monitoring clients
            await self.channel_layer.group_send(
                self.GROUP_NAME,
                {'type': 'item_added', 'item': data.get('item', {})},
            )

    async def item_added(self, event):
        await self.send(text_data=json.dumps({
            'type': 'item_added',
            'item': event['item'],
        }))
