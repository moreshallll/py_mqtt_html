from paho.mqtt import client as mqtt_client
import re
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit
import time
import os

def process_hex_data(hex_input):
    """报文处理"""
    try:
        # 去掉空格
        hex_clean = hex_input.replace(" ", "")
        
        if len(hex_clean) != 26:
            raise ValueError(f"报文长度不正确: {len(hex_clean)}，应为26")
        
        # 验证十六进制格式
        if not re.match(r'^[0-9A-Fa-f]+$', hex_clean):
            raise ValueError("不符合hex格式")
        
        # 转换为字节序列
        frame_bytes = bytes.fromhex(hex_clean)
        
        print(f"输入HEX: {hex_clean.upper()}")
        
        if len(frame_bytes) != 13:
            raise ValueError(f"字节长度不正确: {len(frame_bytes)}，应为13")
        
        identifier_bytes = frame_bytes[:4]
        data_bytes = frame_bytes[4:12]
        checksum_byte = frame_bytes[12]

        print(f"地址标识: {[f'0x{b:02X}' for b in identifier_bytes]}")
        print(f"数据: {[f'0x{b:02X}' for b in data_bytes]}")
        print(f"校验码: 0x{checksum_byte:02X}")
        
        # BCC异或校验
        calculated_checksum = 0
        for byte in frame_bytes[:12]:
            calculated_checksum ^= byte
        
        is_valid = (calculated_checksum == checksum_byte)

        print(f"计算校验: 0x{calculated_checksum:02X}")
        print(f"校验结果: {'通过' if is_valid else '失败'}")
        
        # 字节拆分成比特
        data_bits = []
        for i, byte_val in enumerate(data_bytes):
            bits = [(byte_val >> (7 - j)) & 1 for j in range(8)]
            data_bits.append(bits)
            
            bit_str = ''.join(str(b) for b in bits)
            print(f"数据{i+1:2d}: 0x{byte_val:02X} -> {bit_str} (msb-lsb)")
        
        return {
            'is_valid': is_valid,
            'frame_bytes': frame_bytes,
            'identifier': identifier_bytes,
            'data_bytes': data_bytes,
            'data_bits': data_bits,
            'calculated_checksum': calculated_checksum,
            'received_checksum': checksum_byte
        }
    except Exception as e:
        print(f"process_hex_data错误: {e}")
        raise

def decode_bits(identifier, data, bits_list):
    """解码车轮监控数据 - 可扩展版本"""
    print(f"\n开始解码...标识符: {identifier.hex()}")
    
    decoded_data = {
        'hex_identifier': identifier.hex(),  # 添加标识符用于前端识别
        'timestamp': time.strftime('%H:%M:%S'),
        'device_type': None  # 设备类型，用于前端自动切换
    }
    
    # 车轮监控数据 (0cffc6ef)
    if identifier == bytes.fromhex("0cffc6ef"):
        decoded_data['device_type'] = 'wheel_monitor'
        print("标识匹配: 开始解码车轮监控数据")
        try:
            # 转速值: 前2字节
            speed_raw = int.from_bytes(data[0:2], byteorder='big', signed=False)
            speed_value = speed_raw * 0.5 - 10000
            decoded_data['speed_value'] = speed_value
            
            # 转矩值: 第3-4字节
            torque_raw = int.from_bytes(data[2:4], byteorder='big', signed=False)
            torque_value = torque_raw * 1 / 1000
            decoded_data['torque_value'] = torque_value
            
            # 控制模式指令
            decoded_data['mode1'] = "自由模式" if bits_list[4][0] == 1 else "非自由模式"
            decoded_data['mode2'] = "力矩模式" if bits_list[4][1] == 1 else "非力矩模式"
            decoded_data['mode3'] = "速度模式" if bits_list[4][2] == 1 else "非速度模式"
            decoded_data['mode4'] = "制动模式" if bits_list[4][3] == 1 else "非制动模式"
            decoded_data['mode5'] = "零速锁定模式" if bits_list[4][4] == 1 else "非零速锁定模式"
            decoded_data['mode6'] = "系统故障，要求停机" if bits_list[4][4] == 1 else "正常运行"

            # 其他指令
            decoded_data['mode7'] = "控制器已就绪" if bits_list[5][0] == 1 else "控制器未就绪"
            decoded_data['mode8'] = "预充已完成" if bits_list[5][1] == 1 else "预充未完成"
            decoded_data['mode9'] = "旋变故障" if bits_list[5][2] == 1 else "旋变正常"
            decoded_data['mode10'] = "过流报警" if bits_list[5][3] == 1 else "过流正常"
            decoded_data['mode11'] = "母线过压报警" if bits_list[5][4] == 1 else "母线过压正常"
            decoded_data['mode12'] = "控制电异常报警" if bits_list[5][5] == 1 else "控制电正常"
            decoded_data['mode13'] = "母线欠压报警" if bits_list[5][6] == 1 else "母线欠压正常"
            decoded_data['mode14'] = "功率限幅报警" if bits_list[5][7] == 1 else "功率限幅正常"
            decoded_data['mode15'] = "控制器温度报警" if bits_list[6][0] == 1 else "控制器温度正常"
            decoded_data['mode16'] = "电机温度报警" if bits_list[6][1] == 1 else "电机温度正常"
            decoded_data['mode17'] = "自检完成并正常" if bits_list[6][7] == 1 else "自检未完成或不正常"

            # 综合报警 - 修复逻辑错误
            if bits_list[7][0] == 0:
                if bits_list[7][1] == 0:
                    decoded_data['mode18'] = "正常"
                else:
                    decoded_data['mode18'] = "三级报警(警告提示)"
            else:
                if bits_list[7][1] == 0:
                    decoded_data['mode18'] = "二级报警（限功率输出）"
                else:
                    decoded_data['mode18'] = "一级报警(停机)"

            print(f"解码完成: 转速={speed_value:.2f}, 转矩={torque_value:.4f}")
            
        except Exception as e:
            print(f"解码过程中出错: {e}")
            return {}
    
    # ============ 扩展示例：电池监控设备 ============
    elif identifier == bytes.fromhex("0aabbccd"):  # 示例电池监控设备
        decoded_data['device_type'] = 'battery_monitor'
        print("标识匹配: 开始解码电池监控数据")
        try:
            # 电池监控数据解码逻辑
            decoded_data['voltage'] = int.from_bytes(data[0:2], byteorder='big', signed=False) * 0.1
            decoded_data['current'] = int.from_bytes(data[2:4], byteorder='big', signed=True) * 0.01
            decoded_data['temperature'] = int.from_bytes(data[4:6], byteorder='big', signed=True)
            decoded_data['soc'] = data[6]  # 电池电量百分比
            decoded_data['health'] = "良好" if data[7] > 80 else "需维护"
            
            print(f"解码完成: 电压={decoded_data['voltage']:.1f}V, 电流={decoded_data['current']:.2f}A")
            
        except Exception as e:
            print(f"解码过程中出错: {e}")
            return {}
    
    else:
        print(f"标识不匹配: 未知标识符 {identifier.hex()}")
        return {}
    
    return decoded_data

# Flask配置
app = Flask(__name__)
app.config['SECRET_KEY'] = 'wheel_monitor_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

# 提供静态文件服务
@app.route('/')
def index():
    """主页面 - 提供静态HTML文件"""
    return send_from_directory('static', 'scalable_static_index.html')

@app.route('/<path:path>')
def static_files(path):
    """提供静态文件"""
    return send_from_directory('static', path)

@socketio.on('connect')
def handle_connect():
    """客户端连接时触发"""
    print(f"[WebSocket] 客户端已连接")
    emit('connection_status', {'status': 'connected', 'message': '已连接到车轮监控系统'})

@socketio.on('disconnect')
def handle_disconnect():
    """客户端断开时触发"""
    print(f"[WebSocket] 客户端已断开")

# MQTT配置 - 修复：添加正确的代理地址
broker = 'z1f4a3e9.ala.cn-hangzhou.emqxsl.cn'  # 修复：添加正确的代理地址
port = 8883
topic = "topic/mqttx2py"
client_id = 'client/py0'
username = 'py_0'
password = '119514'

def on_mqtt_connect(client, userdata, flags, reason_code, properties):
    """MQTT连接回调"""
    if reason_code == 0:
        print(f"[MQTT] 成功连接到代理 {broker}:{port}")
        print(f"[MQTT] 订阅主题: {topic}")
        client.subscribe(topic, qos=0)
        # 发送连接状态到前端
        socketio.emit('mqtt_status', {
            'status': 'connected', 
            'topic': topic,
            'timestamp': time.strftime('%H:%M:%S')
        })
    else:
        print(f"[MQTT] 连接失败，代码: {reason_code}")
        socketio.emit('error', {'message': f'MQTT连接失败: {reason_code}'})

def on_mqtt_subscribe(client, userdata, mid, granted_qos, properties):
    """MQTT订阅回调"""
    print(f"[MQTT] 订阅成功，消息ID: {mid}, QoS: {granted_qos}")

def on_mqtt_message(client, userdata, msg):
    """MQTT消息回调"""
    try:
        print(f"\n{'='*50}")
        print(f"[MQTT] 收到消息")
        print(f"主题: {msg.topic}")
        
        hex_receive = msg.payload.hex()
        print(f"HEX格式: {hex_receive}")
        print(f"HEX长度: {len(hex_receive)}")
        
        # 处理HEX数据
        analysis_res = process_hex_data(hex_receive)
        
        # 解码数据
        decoded_data = decode_bits(
            analysis_res['identifier'],
            analysis_res['data_bytes'],
            analysis_res['data_bits']
        )
        
        if decoded_data:
            # 添加校验结果
            decoded_data['is_valid'] = analysis_res['is_valid']
            decoded_data['hex_data'] = hex_receive
            
            print(f"[WebSocket] 发送数据到前端")
            
            # 通过WebSocket发送到前端
            socketio.emit('update_data', decoded_data)
            socketio.emit('mqtt_status', {
                'status': 'message_received',
                'topic': msg.topic,
                'timestamp': time.strftime('%H:%M:%S')
            })
        else:
            print("[警告] 解码数据为空，未发送到前端")
            socketio.emit('warning', {'message': '收到数据但解码失败'})
        
        print(f"{'='*50}\n")
        
    except Exception as e:
        error_msg = f"处理MQTT消息时出错: {str(e)}"
        print(f"[错误] {error_msg}")
        socketio.emit('error', {'message': error_msg})

def on_mqtt_disconnect(client, userdata, reason_code, properties):
    """MQTT断开连接回调"""
    print(f"[MQTT] 连接断开，代码: {reason_code}")
    socketio.emit('error', {'message': f'MQTT连接断开: {reason_code}'})

def connect_mqtt():
    """连接MQTT代理"""
    print(f"[MQTT] 正在连接 {broker}:{port}...")
    
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id)
    
    # 设置回调
    client.on_connect = on_mqtt_connect
    client.on_subscribe = on_mqtt_subscribe
    client.on_message = on_mqtt_message
    client.on_disconnect = on_mqtt_disconnect
    
    # 设置TLS证书
    try:
        client.tls_set(ca_certs='./emqxsl-ca.crt')
        print("[MQTT] TLS证书已设置")
    except Exception as e:
        print(f"[警告] 设置TLS证书失败: {e}")
        socketio.emit('warning', {'message': f'TLS证书设置失败: {e}'})
    
    # 设置用户名密码
    client.username_pw_set(username, password)
    
    # 连接
    try:
        client.connect(broker, port, 60)
        print("[MQTT] 连接请求已发送")
        return client
    except Exception as e:
        print(f"[错误] 连接失败: {e}")
        socketio.emit('error', {'message': f'连接失败: {e}'})
        return None

def run():
    """主运行函数"""
    print("启动车轮监控数据推送系统...")
    print(f"WebSocket服务器: http://127.0.0.1:5000")  # 修复：添加正确的URL
    print(f"MQTT代理: {broker}:{port}")
    print(f"订阅主题: {topic}")
    
    # 检查static文件夹
    if not os.path.exists('static'):
        os.makedirs('static')
        print("[INFO] 创建static文件夹")
        print("[警告] 请将index.html文件放入static文件夹中")
    
    # 连接MQTT
    mqtt_client_instance = connect_mqtt()
    
    if mqtt_client_instance is None:
        print("[错误] MQTT连接失败，程序退出")
        return
    
    # 启动MQTT循环（非阻塞）
    mqtt_client_instance.loop_start()
    print("[MQTT] 循环已启动（非阻塞模式）")
    
    # 启动Flask-SocketIO服务器
    try:
        print("[WebSocket] 服务器启动中...")
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\n正在关闭服务器...")
    except Exception as e:
        print(f"[错误] 服务器运行出错: {e}")
    finally:
        # 停止MQTT循环
        mqtt_client_instance.loop_stop()
        mqtt_client_instance.disconnect()
        print("[MQTT] 循环已停止，连接已断开")

if __name__ == '__main__':
    run()