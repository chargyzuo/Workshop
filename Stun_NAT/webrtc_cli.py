import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

# 信令服务器地址 (替换成你实际的)
WS_URL = "ws://101.227.69.36:5991"

# 配置 STUN 服务器
rtc_config = RTCConfiguration(
    iceServers=[
        RTCIceServer(urls=["stun:stun.qq.com:3478"]),
        RTCIceServer(urls=["stun:stun.miwifi.com:3478"])
    ]
)

async def run(role):
    pc = RTCPeerConnection(configuration=rtc_config)
    
    # --- P2P 通信配置 ---
    if role == "offer":
        # 如果是发起方，必须主动创建数据通道
        channel = pc.createDataChannel("chat")
        
        @channel.on("open")
        def on_open():
            print("🔗 P2P 数据通道已开启！")
            channel.send("你好，我是来自 Linux 命令行发起方的消息！")

        @channel.on("message")
        def on_message(message):
            print(f"[P2P 消息] 收到: {message}")
    else:
        # 如果是接收方，等待对方创建数据通道
        @pc.on("datachannel")
        def on_datachannel(channel):
            @channel.on("open")
            def on_open():
                print("🔗 P2P 数据通道已开启！")
                channel.send("你好，我是来自 Linux 命令行接收方的消息！")

            @channel.on("message")
            def on_message(message):
                print(f"[P2P 消息] 收到: {message}")

    # --- 信令阶段 ---
    print(f"正在连接信令服务器 {WS_URL} ...")
    async with websockets.connect(WS_URL) as websocket:
        print("🟢 已连接信令服务器")

        if role == "offer":
            # 1. 创建 Offer
            print("发送打洞邀请 (Offer)...")
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            await websocket.send(json.dumps({
                "type": "offer",
                "offer": {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                }
            }))

        # 循环接收信令
        async for message_str in websocket:
            try:
                msg = json.loads(message_str)
                print(f"📥 收到信令: {msg.get('type')}")
                
                if msg["type"] == "offer" and role != "offer":
                    print("收到打洞邀请，准备接收...")
                    offer = RTCSessionDescription(sdp=msg["offer"]["sdp"], type=msg["offer"]["type"])
                    await pc.setRemoteDescription(offer)
                    
                    # 2. 回复 Answer
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    print("发送打洞同意书 (Answer)...")
                    await websocket.send(json.dumps({
                        "type": "answer",
                        "answer": {
                            "sdp": pc.localDescription.sdp,
                            "type": pc.localDescription.type
                        }
                    }))
                    
                elif msg["type"] == "answer" and role == "offer":
                    print("收到对方打洞同意书，确立连接...")
                    answer = RTCSessionDescription(sdp=msg["answer"]["sdp"], type=msg["answer"]["type"])
                    await pc.setRemoteDescription(answer)
                    
                elif msg["type"] == "ice-candidate":
                    # aiortc 目前在 python 中对通过 addIceCandidate 动态添加的支持有限，
                    # 并且经常由于和底层的 libwebrtc 差异导致问题。
                    # 大多数情况下，aiortc 通过 SDP 交换就能处理好 STUN 打洞。
                    print("收到对方的 ICE Candidate (依赖 SDP 自动打洞)")
            except json.JSONDecodeError:
                pass

if __name__ == "__main__":
    import sys
    role = "answer" # 默认作为接收方等待
    if len(sys.argv) > 1 and sys.argv[1] == "offer":
        role = "offer"
        
    print(f"当前角色: {role} (加参数 'offer' 作为发起方)")
    
    # 保持主循环运行
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(role))
        loop.run_forever() # 保持进程不断开，维持 P2P
    except KeyboardInterrupt:
        print("进程已终止")