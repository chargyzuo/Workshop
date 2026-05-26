const WebSocket = require('ws');

// 监听 8081 端口，在公网服务器上你需要确保安全组/防火墙放行该端口
const wss = new WebSocket.Server({ port: 8081 }, () => {
    console.log('信令服务器已启动，监听端口: 8081');
});

// 存储所有已连接的客户端
// 实际生产环境中，可能会用 Map 存储，并为每个客户端分配唯一的 ID
const clients = new Set();

wss.on('connection', (ws) => {
    console.log('一个新客户端已连接');
    clients.add(ws);

    // 当收到某个客户端发来的消息时
    ws.on('message', (messageAsString) => {
        try {
            const message = JSON.parse(messageAsString);
            console.log('收到信令消息:', message);

            // 核心逻辑：作为一个中继器，将消息广播给除了发送者之外的其他所有客户端
            // 在真正的 1v1 P2P 中，消息里通常会带上 "targetId"（目标用户ID）
            // 然后服务器只把消息发给那个特定的 targetId 对应的 WebSocket 连接
            
            clients.forEach((client) => {
                if (client !== ws && client.readyState === WebSocket.OPEN) {
                    client.send(JSON.stringify(message));
                }
            });
        } catch (e) {
            console.error('解析消息失败，信令必须是 JSON 格式', e);
        }
    });

    ws.on('close', () => {
        console.log('客户端已断开连接');
        clients.delete(ws);
    });

    ws.on('error', (error) => {
        console.error('WebSocket 发生错误:', error);
    });
});
