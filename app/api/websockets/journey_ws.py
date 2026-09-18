import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

class JourneyConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, journey_id: str):
        await websocket.accept()
        self.active_connections[journey_id] = websocket
        logger.info(f"Journey WebSocket connected: {journey_id}")

    def disconnect(self, journey_id: str):
        if journey_id in self.active_connections:
            del self.active_connections[journey_id]
            logger.info(f"Journey WebSocket disconnected: {journey_id}")

    async def send_personal_message(self, message: dict, journey_id: str):
        websocket = self.active_connections.get(journey_id)
        if websocket:
            try:
                await websocket.send_json(message)
            except Exception as e:
                logger.error(f"Error sending ws message to {journey_id}: {str(e)}")
                self.disconnect(journey_id)

journey_manager = JourneyConnectionManager()

@router.websocket("/{journey_id}")
async def journey_websocket_endpoint(websocket: WebSocket, journey_id: str):
    await journey_manager.connect(websocket, journey_id)
    try:
        while True:
            # We don't necessarily expect incoming messages, just keep connection open
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        journey_manager.disconnect(journey_id)
