import asyncio
import base64
import io
import json
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

PROPERTY_TYPES = [
    ('biodegradable', 'Biodegradable'),
    ('non_biodegradable', 'Non-biodegradable'),
    ('inert', 'Inert'),
]

WASTE_LABEL_LOOKUP = dict(WASTE_TYPES)
PROPERTY_LABEL_LOOKUP = dict(PROPERTY_TYPES)

# Maps the 12 classes from kendrickfff/waste-classification-yolov8-ken
# to our (waste_type, properties) schema.
MODEL_LABEL_MAP = {
    'battery':     ('hazardous',  'non_biodegradable'),
    'biological':  ('organic',    'biodegradable'),
    'brown-glass': ('recyclable', 'inert'),
    'cardboard':   ('recyclable', 'biodegradable'),
    'clothes':     ('msw',        'non_biodegradable'),
    'green-glass': ('recyclable', 'inert'),
    'metal':       ('recyclable', 'non_biodegradable'),
    'paper':       ('recyclable', 'biodegradable'),
    'plastic':     ('recyclable', 'non_biodegradable'),
    'shoes':       ('msw',        'non_biodegradable'),
    'trash':       ('msw',        'non_biodegradable'),
    'white-glass': ('recyclable', 'inert'),
}

_model = None


def _load_model():
    """Lazy-load the YOLOv8 waste classifier from HuggingFace on first use."""
    global _model
    if _model is not None:
        return _model

    from ultralytics import YOLO

    repo_id = "kendrickfff/waste-classification-yolov8-ken"
    try:
        # ultralytics >= 8.3 can resolve HF repo ids directly.
        _model = YOLO(repo_id)
    except Exception:
        # Fallback: download weights via huggingface_hub and load locally.
        from huggingface_hub import hf_hub_download

        last_err = None
        for fname in ("yolov8n-waste-12cls-best.pt", "best.pt", "weights.pt", "model.pt"):
            try:
                weights_path = hf_hub_download(repo_id=repo_id, filename=fname)
                _model = YOLO(weights_path)
                break
            except Exception as exc:
                last_err = exc
                continue
        if _model is None:
            raise RuntimeError(
                f"Could not load weights for {repo_id}: {last_err}"
            )

    logger.info("Loaded YOLO model %s; classes=%s", repo_id, getattr(_model, "names", "?"))
    return _model


def _map_label(name: str):
    """Map a raw model class label to (waste_type, properties)."""
    n = name.lower().strip().replace('_', '-')
    if n in MODEL_LABEL_MAP:
        return MODEL_LABEL_MAP[n]
    for key, mapping in MODEL_LABEL_MAP.items():
        if key in n or n in key:
            return mapping
    return ('msw', 'non_biodegradable')


def classify_frame(image_b64: str) -> dict:
    """Run YOLOv8 classification on a base64-encoded JPEG frame."""
    try:
        from PIL import Image
        import numpy as np

        model = _load_model()
        raw = base64.b64decode(image_b64)
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        results = model(np.array(img), verbose=False)
        r = results[0]

        # YOLOv8 classification heads expose .probs; detection heads expose .boxes.
        if getattr(r, 'probs', None) is not None:
            top_idx = int(r.probs.top1)
            confidence = float(r.probs.top1conf)
            raw_label = r.names[top_idx]
        elif getattr(r, 'boxes', None) is not None and len(r.boxes) > 0:
            # Detection-style output: pick the highest-confidence box.
            best = r.boxes.conf.argmax()
            top_idx = int(r.boxes.cls[best])
            confidence = float(r.boxes.conf[best])
            raw_label = r.names[top_idx]
        else:
            raise ValueError("Model returned no probs or boxes")

        waste_type, prop_type = _map_label(raw_label)
        return {
            'waste_type': waste_type,
            'waste_type_label': WASTE_LABEL_LOOKUP.get(waste_type, waste_type),
            'properties': prop_type,
            'properties_label': PROPERTY_LABEL_LOOKUP.get(prop_type, prop_type),
            'confidence': round(confidence, 2),
            'model_label': raw_label,
        }
    except Exception:
        logger.exception("Inference failed; returning low-confidence fallback")
        return {
            'waste_type': 'msw',
            'waste_type_label': WASTE_LABEL_LOOKUP['msw'],
            'properties': 'non_biodegradable',
            'properties_label': PROPERTY_LABEL_LOOKUP['non_biodegradable'],
            'confidence': 0.0,
            'model_label': 'error',
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
            # Inference is CPU-bound; run off the event loop.
            result = await asyncio.to_thread(classify_frame, image_b64)
            await self.send(text_data=json.dumps({
                'type': 'classification_result',
                **result,
            }))
        elif msg_type == 'broadcast_item':
            await self.channel_layer.group_send(
                self.GROUP_NAME,
                {'type': 'item_added', 'item': data.get('item', {})},
            )

    async def item_added(self, event):
        await self.send(text_data=json.dumps({
            'type': 'item_added',
            'item': event['item'],
        }))
