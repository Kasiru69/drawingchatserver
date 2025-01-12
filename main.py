import asyncio
import json
import websockets

rooms = {}


async def register(websocket, room_id):
    if room_id not in rooms:
        rooms[room_id] = set()
        print(f"\n[NEW ROOM CREATED] Room ID: {room_id}")
    rooms[room_id].add(websocket)
    print(f"[USER JOINED] Room {room_id} now has {len(rooms[room_id])} users")
    print(f"[ACTIVE ROOMS] Current rooms: {list(rooms.keys())}")


async def unregister(websocket, room_id):
    if room_id in rooms:
        rooms[room_id].remove(websocket)
        print(f"\n[USER LEFT] User left room {room_id}")
        print(f"[ROOM STATUS] Room {room_id} now has {len(rooms[room_id])} users")

        if len(rooms[room_id]) == 0:
            del rooms[room_id]
            print(f"[ROOM CLOSED] Room {room_id} was deleted (no users left)")
            print(f"[ACTIVE ROOMS] Current rooms: {list(rooms.keys())}")


async def broadcast_to_room(room_id, message, sender):
    if room_id in rooms:
        data = json.loads(message)
        message_type = data.get('type', 'unknown')
        print(f"\n[BROADCASTING] Message type: {message_type} in room {room_id}")
        recipients = 0
        for client in rooms[room_id]:
            if client != sender:  # Don't send back to the sender
                await client.send(message)
                recipients += 1

        print(f"[BROADCAST COMPLETE] Message sent to {recipients} users in room {room_id}")


async def handle_connection(websocket):
    try:
        join_message = await websocket.recv()
        data = json.loads(join_message)
        room_id = data.get('room_id')
        user_name = data.get('user_name', 'Unknown User')

        print(f"\n[NEW CONNECTION] User {user_name} attempting to join room {room_id}")

        if not room_id:
            print(f"[ERROR] No room_id provided in join message")
            return

        await register(websocket, room_id)
        print(f"[SUCCESS] User {user_name} successfully joined room {room_id}")

        # Handle incoming messages
        async for message in websocket:
            try:
                data = json.loads(message)
                message_type = data.get('type', 'unknown')
                print(f"\n[RECEIVED MESSAGE] Type: {message_type}")
                print(f"[MESSAGE DETAILS] From: {user_name} in Room: {room_id}")
                if message_type == 'draw':
                    print(f"[DRAW DATA] Color: {data.get('color')}, "
                          f"Eraser: {data.get('is_eraser')}, "
                          f"Stroke Width: {data.get('stroke_width')}")
                elif message_type == 'clear':
                    print(f"[CLEAR CANVAS] User {user_name} cleared the canvas in room {room_id}")

                await broadcast_to_room(room_id, message, websocket)

            except json.JSONDecodeError:
                print(f"[ERROR] Failed to parse message: {message}")

    except websockets.exceptions.ConnectionClosed:
        print(f"\n[CONNECTION CLOSED] User {user_name} disconnected from room {room_id}")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {str(e)}")
    finally:
        await unregister(websocket, room_id)


async def main():
    print("\n[SERVER STARTING] WebSocket server is starting...")
    server = await websockets.serve(handle_connection, "0.0.0.0", 8765)
    print("[SERVER READY] WebSocket server is running on ws://localhost:8765")
    print("[WAITING] Waiting for connections...\n")
    await asyncio.Future()  # run forever


if __name__ == "__main__":
    print("[INITIALIZING] Drawing WebSocket Server")
    asyncio.run(main())