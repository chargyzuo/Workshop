import asyncio
import websockets
import json

# 存储所有已连接的客户端
connected_clients = set()

async def signaling_handler(websocket):
    print("一个新客户端已连接")
    connected_clients.add(websocket)
    try:
        async for message_str in websocket:
            try:
                message = json.loads(message_str)
                print(f"收到信令消息: {message}")

                # 广播给除了发送者之外的所有客户端
                for client in connected_clients:
                    if client != websocket:
                        await client.send(json.dumps(message))
            except json.JSONDecodeError:
                print("解析消息失败，信令必须是 JSON 格式")
                
    except websockets.exceptions.ConnectionClosed as e:
        print(f"客户端断开连接: {e}")
    finally:
        connected_clients.remove(websocket)
        print("清理已断开的客户端")

async def main():
    # 监听 0.0.0.0 可以让外部网络访问（公网IP），监听端口 8081
    print("信令服务器已启动，监听 0.0.0.0:8081")
    async with websockets.serve(signaling_handler, "0.0.0.0", 8081):
        await asyncio.Future()  # 永远运行

if __name__ == "__main__":
    asyncio.run(main())
