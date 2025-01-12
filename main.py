import asyncio
import json
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

# Store rooms with their respective websockets
rooms = {}

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, you might want to restrict this
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# HTML page to connect to WebSocket (for testing purposes)
@app.get("/")
async def get():
    html_content = """
    <html>
        <body>
            <h1>WebSocket Test</h1>
            <script>
                // Use secure WebSocket for HTTPS connections
                const wsProtocol = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
                const wsUrl = `${wsProtocol}${window.location.host}/ws`;
                console.log('Connecting to:', wsUrl);

                const socket = new WebSocket(wsUrl);

                socket.onopen = () => {
                    console.log('Connected!');
                    socket.send(JSON.stringify({ "room_id": "room1", "user_name": "Test User" }));
                };
                socket.onmessage = (event) => {
                    console.log('Received:', event.data);
                };
                socket.onerror = (error) => {
                    console.error('WebSocket error:', error);
                };
                socket.onclose = (event) => {
                    console.log("Disconnected - Code:", event.code, "Reason:", event.reason);
                };
            </script>
        </body>
    </html>
    """
    return HTMLResponse(content=html_content)


# WebSocket endpoint for users to join rooms and interact
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    join_message = await websocket.receive_text()
    data = json.loads(join_message)
    room_id = data.get('room_id')
    user_name = data.get('user_name', 'Unknown User')

    print(f"[NEW CONNECTION] User {user_name} attempting to join room {room_id}")

    if not room_id:
        print(f"[ERROR] No room_id provided in join message")
        await websocket.close()
        return

    # Register the user in the room
    await register(websocket, room_id, user_name)

    try:
        # Handle incoming messages
        while True:
            message = await websocket.receive_text()
            await handle_message(message, room_id, user_name, websocket)
    except WebSocketDisconnect:
        print(f"[CONNECTION CLOSED] User {user_name} disconnected from room {room_id}")
        await unregister(websocket, room_id)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {str(e)}")
        await unregister(websocket, room_id)


# Register a new WebSocket connection to a room
async def register(websocket, room_id, user_name):
    if room_id not in rooms:
        rooms[room_id] = set()
        print(f"[NEW ROOM CREATED] Room ID: {room_id}")
    rooms[room_id].add(websocket)
    print(f"[USER JOINED] User {user_name} joined room {room_id}.")
    print(f"[ACTIVE ROOMS] Current rooms: {list(rooms.keys())}")

    # Notify the user that they've successfully joined
    try:
        await websocket.send_text(json.dumps({
            "type": "system",
            "message": f"Successfully joined room {room_id}"
        }))
    except Exception as e:
        print(f"[ERROR] Failed to send join confirmation: {str(e)}")


# Unregister a WebSocket connection from a room
async def unregister(websocket, room_id):
    if room_id in rooms:
        rooms[room_id].remove(websocket)
        print(f"[USER LEFT] A user left room {room_id}.")
        if len(rooms[room_id]) == 0:
            del rooms[room_id]
            print(f"[ROOM CLOSED] Room {room_id} deleted (no users left).")


# Broadcast a message to all users in a room (except the sender)
async def broadcast_to_room(room_id, message, sender):
    if room_id in rooms:
        try:
            data = json.loads(message)
            message_type = data.get('type', 'unknown')
            print(f"[BROADCAST] Message type: {message_type} in room {room_id}")
            recipients = 0
            for client in rooms[room_id]:
                if client != sender:  # Don't send the message back to the sender
                    try:
                        await client.send_text(message)
                        recipients += 1
                    except Exception as e:
                        print(f"[ERROR] Failed to send to a recipient: {str(e)}")
            print(f"[BROADCAST COMPLETE] Sent to {recipients} users in room {room_id}")
        except json.JSONDecodeError:
            print(f"[ERROR] Failed to parse broadcast message: {message}")
        except Exception as e:
            print(f"[ERROR] Broadcast error: {str(e)}")


# Handle incoming messages and broadcast to the room
async def handle_message(message, room_id, user_name, sender):
    try:
        data = json.loads(message)
        message_type = data.get('type', 'unknown')
        print(f"[RECEIVED MESSAGE] Type: {message_type}")
        print(f"[MESSAGE DETAILS] From: {user_name} in Room: {room_id}")

        if message_type == 'draw':
            print(f"[DRAW DATA] Color: {data.get('color')}, "
                  f"Eraser: {data.get('is_eraser')}, "
                  f"Stroke Width: {data.get('stroke_width')}")
        elif message_type == 'clear':
            print(f"[CLEAR CANVAS] User {user_name} cleared the canvas in room {room_id}")

        await broadcast_to_room(room_id, message, sender)

    except json.JSONDecodeError:
        print(f"[ERROR] Failed to parse message: {message}")
    except Exception as e:
        print(f"[ERROR] Message handling error: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8765)