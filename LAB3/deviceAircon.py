import paho.mqtt.client as mqtt
from cryptography.fernet import Fernet
from datetime import datetime
import time
import json

# 配置
broker_address = "127.0.0.1"  # MQTT服务器地址
username = "aircon"  # MQTT用户名
password = "device1234"  # MQTT密码
encryption_key = b"09jyez3-73axU9OnTKKhT5DigEKqw2wutZ14z6MQwc8="  # 加密密钥

status = False
temperature = None
belongsto = []

# 创建加密器对象
cipher_suite = Fernet(encryption_key)


def send_status():
    msg = {
        "device": username,
        "status": status,
        "value": temperature,
        "belongsto": belongsto,
    }
    encrypted_msg = cipher_suite.encrypt(json.dumps(msg).encode())
    client.publish("receive", encrypted_msg)


def unbind(msg):
    global belongsto
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    decrypted_command = cipher_suite.decrypt(msg.payload)
    parsed_command = json.loads(decrypted_command.decode())
    device = parsed_command["device"]
    client_id = parsed_command["client"]
    if device != "aircon":
        return
    if client_id not in belongsto:
        return
    else:
        belongsto.remove(client_id)
        print(f"\n[{timestamp}] 收到{client_id}的解绑请求")


def bind(msg):
    global belongsto
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    decrypted_command = cipher_suite.decrypt(msg.payload)
    parsed_command = json.loads(decrypted_command.decode())
    device = parsed_command["device"]
    client_id = parsed_command["client"]
    if device != "aircon":
        return
    if client_id in belongsto:
        return
    else:
        print(f"\n[{timestamp}] 收到{client_id}的绑定请求")
        belongsto.append(client_id)


def command(msg):
    global status, temperature
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    decrypted_command = cipher_suite.decrypt(msg.payload)
    parsed_command = json.loads(decrypted_command.decode())

    device = parsed_command["device"]
    action = parsed_command["action"]
    client_id = parsed_command["client"]

    if device != "aircon":
        return
    if client_id not in belongsto:
        return

    if action == "switch":
        print(f"\n[{timestamp}] 收到控制开关请求")
        status = not status
        if not status:
            temperature = None
            print("开关已关")
        else:
            temperature = 25
            print("开关已开")
    elif action == "set":
        setTemp = parsed_command["temperature"]
        if not status:
            return
        print(f"\n[{timestamp}] 收到控制温度请求")
        if temperature <= 16 or temperature >= 35:
            print("\n[{timestamp}] 无效空调温度")
            return
        temperature = setTemp
        print(f"\n[{timestamp}] 已设置空调温度为{temperature}")


# 处理连接事件
def on_connect(client, userdata, flags, rc):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if rc == 0:
        print(f"\n[{timestamp}] {username}成功连接到MQTT服务器")
    else:
        print(f"\n[{timestamp}] {username}连接到MQTT服务器失败， 错误代码 %d\n", rc)

    # 开始订阅消息和启动消息循环
    client.subscribe("bind")
    client.subscribe("unbind")
    client.subscribe("broadcast")
    client.subscribe("command")


# 处理消息事件
def on_message(client, userdata, msg):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if msg.topic == "bind":
        bind(msg)
    if msg.topic == "unbind":
        unbind(msg)
    if msg.topic == "command":
        command(msg)
    if msg.topic == "broadcast":
        send_status()
        print(f"\n[{timestamp}] 收到广播")


# 创建 MQTT 客户端对象
client = mqtt.Client(username)
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_message = on_message

# 连接 MQTT 服务器
client.connect(broker_address, 1883, 20)

client.loop_forever()
