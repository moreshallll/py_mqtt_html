from paho.mqtt import client as mqtt_client
import re


def process_hex_data(hex_input):# 报文处理
    # 去掉空格
    hex_clean = hex_input.replace(" ", "")
    
    if len(hex_clean) != 26:
        raise ValueError(f"报文不完整_1")
    
    # 验证十六进制格式
    if not re.match(r'^[0-9A-Fa-f]+$', hex_clean):
        raise ValueError("不符合hex格式")
    
    # 转换为字节序列
    frame_bytes = bytes.fromhex(hex_clean)
    
    print(f"输入的十六进制数据: {hex_clean.upper()}")
    # print(f"字节序列: {[f'0x{b:02X}' for b in data_bytes]}")
    
    # 3. 分离数据和校验字节
    if len(frame_bytes) != 13:
        raise ValueError("报文不完整_2")
    
    identifier_bytes = frame_bytes[:4] # 前4字节为地址标识
    data_bytes = frame_bytes[4:12]  # 中间8字节为数据
    checksum_byte = frame_bytes[12]  # 最后1字节为校验码

    print(f"地址标识: {[f'0x{b:02X}' for b in identifier_bytes]}")
    print(f"数据: {[f'0x{b:02X}' for b in data_bytes]}")
    print(f"校验码: 0x{checksum_byte:02X}")
    
    # BCC异或校验
    calculated_checksum = 0
    for byte in frame_bytes[:12] :
        calculated_checksum ^= byte
    
    is_valid = (calculated_checksum == checksum_byte)

    print(f"计算出的校验码: 0x{calculated_checksum:02X}")
    print(f"校验结果: {'通过' if is_valid else '失败'}")
    
    # 字节拆分成比特
    print("\n字节到比特拆分结果:")
    print("-" * 40)
    
    data_bits = []
    for i, byte_val in enumerate(data_bytes):
        # 将每个字节拆分为8个bit msb-lsb
        bits = [(byte_val >> (7 - j)) & 1 for j in range(8)] # 右位移然后位与01
        data_bits.append(bits)
        
        bit_str = ''.join(str(b) for b in bits)
        print(f"数据{i+1:2d}: 0x{byte_val:02X} -> {bit_str} (msb-lsb))")
    
    return {
        'is_valid': is_valid,                       # 校验结果
        'frame_bytes': frame_bytes,                 # 字节形式报文
        'identifier':identifier_bytes,              # 地址标识字节
        'data_bytes':data_bytes,                    # 数据字节
        'data_bits': data_bits,                     # 数据比特
        'calculated_checksum': calculated_checksum, # 计算校验和
        'received_checksum': checksum_byte          # 传输校验和
    }

def decode_bits_example(identifier, data ,bits_list):# 解码
    print("\n比特数据解码:")
    print("-" * 30)
    
    decoded_info = {}
    
    # id:0cffc6ef 解码车轮监控数据
    mode_wheel = bytes.fromhex("0cffc6ef")
    if identifier == mode_wheel:
        print("开始解码车轮监控数据")
        speed_value = int.from_bytes(data[0:1], byteorder='big', signed=False) * 0.5 - 10000 
        print(f"转速值：{speed_value}")
        torque_value = int.from_bytes(data[2:3], byteorder='big', signed=False) * 1 / 1000 
        print(f"转矩值：{torque_value}")
        print("非自由模式") if bits_list[4][0] == 0 else print("自由模式")
        print("非力矩模式") if bits_list[4][1] == 0 else print("力矩模式")
        print("非速度模式") if bits_list[4][2] == 0 else print("速度模式")
        print("非制动模式") if bits_list[4][3] == 0 else print("制动模式")
    
    return decoded_info



# 以下，配置paho.mqtt并开始连接
broker = 'z1f4a3e9.ala.cn-hangzhou.emqxsl.cn'
port = 8883
topic = "topic/mqttx2py"
client_id = 'client/py0'
username = 'py_0'
password = '119514'


def connect_mqtt():
    def on_connect(client, userdata, flags, reason_code, properties):
        if reason_code == 0:
            print("Connected successfully.")
        else:
            print(f"Failed to connect, reason code: {reason_code}")
    # 填写客户端ID
    client = mqtt_client.Client(mqtt_client.CallbackAPIVersion.VERSION2, client_id)
    # 注册CA安全证书
    client.tls_set(ca_certs='./emqxsl-ca.crt')
    client.username_pw_set(username, password)
    client.on_connect = on_connect
    client.connect(broker, port)
    return client


# 回调订阅函数
def subscribe(client: mqtt_client):
    def on_message(client, userdata, msg):
        hex_receive = msg.payload.hex()
        print()
        print(f"Received `{msg.payload.hex()}` from `{msg.topic}` topic")
        print()

        analysis_res = process_hex_data(hex_receive)

        decode_bits_example(analysis_res['identifier'], analysis_res['data_bytes'], analysis_res['data_bits'])
        

    client.subscribe(topic=topic, qos=0)
    client.on_message = on_message


def run():
    client = connect_mqtt()
    subscribe(client)

    client.loop_forever()


if __name__ == '__main__':
    run()