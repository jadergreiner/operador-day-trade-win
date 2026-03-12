"""
ATI-1: WebSocket Real-time Orders Server
Subtask 4.1 - 4.4: Event Loop + Connection Manager + Heartbeat + Performance

Owner: Dev-Backend-3
Duration: 4-6 hours
Success Criteria: P95 latency <100ms + 6/6 AC tests passing
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import time
import os
from typing import Dict, List, Optional, Any
from datetime import datetime
from pydantic import BaseModel
import jwt
from loguru import logger

# Configuration
JWT_SECRET = "your-secret-key"
JWT_ALGORITHM = "HS256"
HEARTBEAT_INTERVAL = 30  # seconds
MAX_CONNECTIONS_PER_TRADER = 5
INTERNAL_BROADCAST_TOKEN = os.getenv("ATI1_BROADCAST_TOKEN")


class ConnectionManager:
    """Manages WebSocket connections for traders"""

    def __init__(self):
        # Map: trader_id -> List of WebSocket connections
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self.connection_times: Dict[WebSocket, float] = {}

    async def connect(self, websocket: WebSocket, trader_id: str):
        """Accept WebSocket connection and register"""
        await websocket.accept()

        if trader_id not in self.active_connections:
            self.active_connections[trader_id] = []

        # Check max connections per trader
        if len(self.active_connections[trader_id]) >= MAX_CONNECTIONS_PER_TRADER:
            await websocket.close(code=1008, reason="Max connections exceeded")
            raise RuntimeError(f"Max connections ({MAX_CONNECTIONS_PER_TRADER}) exceeded for {trader_id}")

        self.active_connections[trader_id].append(websocket)
        self.connection_times[websocket] = time.time()

        logger.info(f"✅ Connection accepted for trader {trader_id} "
                   f"(total: {len(self.active_connections[trader_id])})")

    async def disconnect(self, websocket: WebSocket, trader_id: str):
        """Remove WebSocket connection"""
        if trader_id in self.active_connections:
            try:
                self.active_connections[trader_id].remove(websocket)
                if not self.active_connections[trader_id]:
                    del self.active_connections[trader_id]

                if websocket in self.connection_times:
                    del self.connection_times[websocket]

                logger.info(f"❌ Disconnect for trader {trader_id}")
            except ValueError:
                pass

    async def broadcast(self, message: dict, trader_id: Optional[str] = None,
                       exclude: Optional[WebSocket] = None):
        """
        Broadcast message to connections

        Args:
            message: Message dict to send
            trader_id: If provided, send only to this trader's connections
            exclude: WebSocket connection to exclude
        """
        if trader_id:
            # Send to specific trader
            connections = self.active_connections.get(trader_id, [])
        else:
            # Send to all traders
            connections = []
            for trader_conns in self.active_connections.values():
                connections.extend(trader_conns)

        disconnected = []
        for connection in connections:
            if exclude and connection == exclude:
                continue

            try:
                await connection.send_json(message)
            except Exception as e:
                logger.error(f"❌ Broadcast error: {e}")
                disconnected.append((connection, trader_id))

        # Clean up disconnected
        for conn, tid in disconnected:
            await self.disconnect(conn, tid)


class MessageHandler:
    """Handles incoming WebSocket messages"""

    @staticmethod
    def validate_message(data: dict) -> bool:
        """Validate message format"""
        required_fields = ["type", "trader_id"]
        return all(field in data for field in required_fields)

    @staticmethod
    async def route_message(data: dict, websocket: WebSocket, manager: ConnectionManager):
        """Route message based on type"""
        if not MessageHandler.validate_message(data):
            await websocket.send_json({
                "type": "error",
                "message": "Invalid message format"
            })
            return

        msg_type = data.get("type")
        trader_id = data.get("trader_id")

        if msg_type == "order":
            # Route order message
            await manager.broadcast({
                "type": "order_received",
                "trader_id": trader_id,
                "timestamp": datetime.utcnow().isoformat(),
                "payload": data.get("payload")
            }, trader_id=trader_id)

        elif msg_type == "ping":
            # Respond to ping
            await websocket.send_json({
                "type": "pong",
                "timestamp": datetime.utcnow().isoformat()
            })

        else:
            logger.warning(f"Unknown message type: {msg_type}")


class HeartbeatManager:
    """Manages WebSocket heartbeat keep-alive"""

    def __init__(self, manager: ConnectionManager):
        self.manager = manager
        self.tasks: Dict[str, asyncio.Task] = {}

    async def start_heartbeat(self, websocket: WebSocket, trader_id: str):
        """Start heartbeat for connection"""
        task_id = f"{trader_id}_{id(websocket)}"

        async def heartbeat_loop():
            while True:
                try:
                    await asyncio.sleep(HEARTBEAT_INTERVAL)

                    await websocket.send_json({
                        "type": "ping",
                        "timestamp": datetime.utcnow().isoformat()
                    })

                except Exception as e:
                    logger.error(f"❌ Heartbeat error for {trader_id}: {e}")
                    await self.manager.disconnect(websocket, trader_id)
                    break

        task = asyncio.create_task(heartbeat_loop())
        self.tasks[task_id] = task
        logger.info(f"💓 Heartbeat started for {trader_id} (interval: {HEARTBEAT_INTERVAL}s)")

    async def stop_heartbeat(self, websocket: WebSocket, trader_id: str):
        """Stop heartbeat for connection"""
        task_id = f"{trader_id}_{id(websocket)}"
        if task_id in self.tasks:
            self.tasks[task_id].cancel()
            del self.tasks[task_id]


def verify_jwt_token(token: str) -> dict:
    """Verify JWT token and extract trader_id"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        trader_id = payload.get("trader_id")
        if not trader_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


# FastAPI app
app = FastAPI(title="ATI-1 WebSocket Orders Server")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global managers
connection_manager = ConnectionManager()
heartbeat_manager = HeartbeatManager(connection_manager)
message_handler = MessageHandler()


@app.websocket("/ws/orders/{trader_id}")
async def websocket_endpoint(websocket: WebSocket, trader_id: str, token: str = Query(...)):
    """
    WebSocket endpoint for real-time orders

    AC-1: Connection persistence (reconnect within 5s)
    AC-2: P95 latency < 100ms
    AC-5: Graceful disconnect (cleanup)
    AC-6: Heartbeat working (30s interval)
    """

    # Verify JWT token
    try:
        verify_jwt_token(token)
    except HTTPException as e:
        await websocket.close(code=1008, reason="Unauthorized")
        logger.error(f"❌ Unauthorized connection attempt for {trader_id}")
        return

    # Connect
    try:
        await connection_manager.connect(websocket, trader_id)
    except RuntimeError as e:
        logger.error(f"❌ Connection failed: {e}")
        return

    # Start heartbeat
    await heartbeat_manager.start_heartbeat(websocket, trader_id)

    # Message loop
    try:
        while True:
            # Receive with timeout
            data = await asyncio.wait_for(
                websocket.receive_json(),
                timeout=HEARTBEAT_INTERVAL + 10  # Allow grace period
            )

            # Track latency (AC-2: P95 < 100ms)
            receive_time = time.time()

            # Route message
            await message_handler.route_message(data, websocket, connection_manager)

            # Log latency
            latency = (time.time() - receive_time) * 1000  # ms
            if latency > 100:
                logger.warning(f"⚠️ High latency detected: {latency:.2f}ms")

    except asyncio.TimeoutError:
        logger.warning(f"⏱️ Timeout for {trader_id} - closing connection")

    except WebSocketDisconnect:
        logger.info(f"👋 Client disconnected: {trader_id}")

    except Exception as e:
        logger.error(f"❌ WebSocket error: {e}")

    finally:
        # Cleanup
        await heartbeat_manager.stop_heartbeat(websocket, trader_id)
        await connection_manager.disconnect(websocket, trader_id)
        logger.info(f"🧹 Cleanup complete for {trader_id}")


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "connected_traders": len(connection_manager.active_connections),
        "total_connections": sum(len(conns) for conns in connection_manager.active_connections.values()),
        "timestamp": datetime.utcnow().isoformat()
    }


@app.post("/api/v1/broadcast")
async def broadcast_message(payload: Dict[str, Any], request: Request):
    """
    Endpoint interno para broadcast de mensagens (AC5.8).

    Body:
    {
      "message": {...},
      "trader_id": "TRADER_001" (optional)
    }
    """
    if INTERNAL_BROADCAST_TOKEN:
        token = request.headers.get("X-Internal-Token")
        if token != INTERNAL_BROADCAST_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

    message = payload.get("message")
    trader_id = payload.get("trader_id")

    if not isinstance(message, dict):
        raise HTTPException(status_code=400, detail="Invalid message")

    await connection_manager.broadcast(message, trader_id=trader_id)
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
