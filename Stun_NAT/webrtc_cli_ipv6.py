import asyncio
import json
import websockets
from aiortc import RTCPeerConnection, RTCSessionDescription, RTCConfiguration, RTCIceServer

WS_URL = "ws://101.227.69.36:5991"

# 强制不使用 STUN，只用本地网卡
rtc_config = RTCConfiguration(iceServers=[])

async def run(role):
    pc = RTCPeerConnection(configuration=rtc_config)
    
    @pc.on("iceconnectionstatechange")
    async def on_iceconnectionstatechange():
        print(f"🔄 内部 ICE 状态变化: {pc.iceConnectionState}")

    @pc.on("connectionstatechange")
    async def on_connectionstatechange():
        print(f"🔄 内部连接状态变化: {pc.connectionState}")
    
    if role == "offer":
        channel = pc.createDataChannel("chat")
        @channel.on("open")
        def on_open():
            print("🔗 P2P 数据通道已开启！")
            channel.send("你好，我是来自 Linux IPv6 的消息！")
        @channel.on("message")
        def on_message(message):
            print(f"[P2P 消息] 收到: {message}")
    else:
        @pc.on("datachannel")
        def on_datachannel(channel):
            @channel.on("open")
            def on_open():
                print("🔗 P2P 数据通道已开启！")
                channel.send("你好，我是来自 Linux IPv6 接收方的消息！")
            @channel.on("message")
            def on_message(message):
                print(f"[P2P 消息] 收到: {message}")

    print(f"正在连接信令服务器 {WS_URL} ...")
    async with websockets.connect(WS_URL) as websocket:
        print("🟢 已连接信令服务器")

        if role == "offer":
            print("正在生成 IPv6 Offer...")
            offer = await pc.createOffer()
            await pc.setLocalDescription(offer)
            
            while pc.iceGatheringState != "complete":
                await asyncio.sleep(0.1)
                
            print("发送直连邀请 (Offer)...")
            print(f"DEBUG Offer SDP:\n{pc.localDescription.sdp}")
            await websocket.send(json.dumps({
                "type": "offer",
                "offer": {
                    "sdp": pc.localDescription.sdp,
                    "type": pc.localDescription.type
                }
            }))

        async for message_str in websocket:
            try:
                msg = json.loads(message_str)
                if msg["type"] == "offer" and role != "offer":
                    print("收到直连邀请，准备接收...")
                    offer = RTCSessionDescription(sdp=msg["offer"]["sdp"], type=msg["offer"]["type"])
                    await pc.setRemoteDescription(offer)
                    
                    answer = await pc.createAnswer()
                    await pc.setLocalDescription(answer)
                    
                    while pc.iceGatheringState != "complete":
                        await asyncio.sleep(0.1)
                        
                    print("发送直连同意书 (Answer)...")
                    await websocket.send(json.dumps({
                        "type": "answer",
                        "answer": {
                            "sdp": pc.localDescription.sdp,
                            "type": pc.localDescription.type
                        }
                    }))
                    
                elif msg["type"] == "answer" and role == "offer":
                    print("收到对方直连同意书，确立连接...")
                    print(f"DEBUG Received Answer SDP:\n{msg['answer']['sdp']}")
                    answer = RTCSessionDescription(sdp=msg["answer"]["sdp"], type=msg["answer"]["type"])
                    await pc.setRemoteDescription(answer)
                    
                elif msg["type"] == "ice-candidate":
                    from aiortc.sdp import candidate_from_sdp
                    candidate_info = msg["candidate"]
                    sdp_str = candidate_info.get("candidate", "")
                    if sdp_str:
                        # 【黑科技核心】拦截浏览器的 mDNS 假地址，替换为我们手动传入的真 IPv6 地址
                        if ".local" in sdp_str and target_ipv6:
                            parts = sdp_str.split(" ")
                            for i, part in enumerate(parts):
                                if ".local" in part:
                                    parts[i] = target_ipv6
                            sdp_str = " ".join(parts)
                            print(f"🔧 [黑科技] 拦截 mDNS，注入真实 IPv6 地址: {sdp_str}")

                        if ":" in sdp_str and ".local" not in sdp_str:
                            remote_candidate = candidate_from_sdp(sdp_str)
                            remote_candidate.sdpMid = candidate_info.get("sdpMid")
                            remote_candidate.sdpMLineIndex = candidate_info.get("sdpMLineIndex")
                            
                            await pc.addIceCandidate(remote_candidate)
                            print(f"🕳️ 已添加来自浏览器的特征尝试直连: [{remote_candidate.ip}]:{remote_candidate.port}")
            except json.JSONDecodeError:
                pass

if __name__ == "__main__":
    import sys
    role = "answer"
    target_ipv6 = None
    
    if len(sys.argv) > 1 and sys.argv[1] == "offer":
        role = "offer"
    if len(sys.argv) > 2:
        target_ipv6 = sys.argv[2]
        
    print(f"当前角色: {role}")
    if target_ipv6:
        print(f"🎯 强制注入目标 IPv6 地址: {target_ipv6}")
    else:
        print("⚠️ 未提供目标 IPv6，若浏览器开启了 mDNS 隐私保护可能无法直连。")
        
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run(role))
        loop.run_forever()
    except KeyboardInterrupt:
        print("进程已终止")
