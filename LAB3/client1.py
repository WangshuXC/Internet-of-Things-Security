import paho.mqtt.client as mqtt
from cryptography.fernet import Fernet
import time
import json

# 配置
broker_address = "127.0.0.1"  # MQTT服务器地址
username = "user1"  # MQTT用户名
password = "user1234"  # MQTT密码
encryption_key = b"09jyez3-73axU9OnTKKhT5DigEKqw2wutZ14z6MQwc8="  # 加密密钥

devices = {}
near_devices = []

# 创建加密器对象
cipher_suite = Fernet(encryption_key)


def main():
    while True:
        print("\n选择操作:")
        print("1. 控制设备")
        print("2. 查看设备状态")
        print("3. 绑定设备")
        print("4. 解绑设备")

        # 获取用户输入
        choice = input()

        if choice == "1":
            broadcast()
            print("选择你要控制的设备(\033[92m", end="")
            for device in devices:
                print(" " + device, end="")
            print(" \033[0m)")

            # 获取用户输入
            device_choice = input()

            # 控制设备
            if device_choice in devices and devices[device_choice]:
                command = {}
                if device_choice == "aircon":
                    print(f"1. 开关{device_choice}\n2. 调节温度")
                    action = input()
                    if action == "2":
                        if not devices[device_choice]["status"]:
                            print("空调未开启，请先打开")
                            continue
                        print("请输入目标温度：")
                        temperature = input()
                        command = {
                            "device": device_choice,
                            "action": "set",
                            "temperature": temperature,
                            "client": username,
                        }
                        if temperature <= 16 or temperature >= 35:
                            print("无效温度，请重试")
                        else:
                            print(f"{device_choice}温度已设置为{temperature}")
                    elif action == "1":
                        print(f"{device_choice}已", end="")
                        if devices[device_choice]["status"]:
                            print("关")
                        else:
                            print("开")
                        command = {
                            "device": device_choice,
                            "action": "switch",
                            "client": username,
                        }
                    else:
                        print("Invalid choice. Please try again.")
                else:
                    print(f"{device_choice}已", end="")
                    if devices[device_choice]["status"]:
                        print("关")
                    else:
                        print("开")
                    command = {
                        "device": device_choice,
                        "action": "switch",
                        "client": username,
                    }
                encrypted_command = cipher_suite.encrypt(json.dumps(command).encode())
                client.publish("command", encrypted_command)
            else:
                print("Invalid choice. Please try again.")
        elif choice == "2":
            broadcast()
            # print(devices)
            if not devices:
                print("\033[91m\n未绑定设备\033[0m")
                continue
            else:
                if "light" in devices:
                    print(
                        "\033[91m\n灯泡: {}\033[0m".format(
                            "开" if devices["light"]["status"] else "关"
                        )
                    )
                if "aircon" in devices:
                    temperature_str = (
                        str(devices["aircon"]["temperature"])
                        if devices["aircon"]["temperature"] is not None
                        else "未设置"
                    )
                    print(
                        "\033[91m\n空调: {}, 温度: {}\033[0m".format(
                            "开" if devices["aircon"]["status"] else "关", temperature_str
                        ),
                        end="\n",
                    )
                if "socket" in devices:
                    print(
                        "\033[91m\n插座: {}\033[0m".format(
                            "开" if devices["socket"]["status"] else "关"
                        )
                    )

        elif choice == "3":
            print("请输入要绑定的设备名称(\033[92m", end="")
            for device in near_devices:
                if device not in devices:
                    print(" " + device, end="")
            print(" \033[0m)")
            device = input()
            bind(device)
            broadcast()

        elif choice == "4":
            print("请输入要解绑的设备名称(\033[91m", end="")
            for device in devices:
                print(" " + device, end="")
            print(" \033[0m)")
            device = input()
            unbind(device)
            broadcast()

        else:
            print("Invalid choice. Please try again.")
            continue

        # 跳出循环，执行下一次操作
        time.sleep(0.2)
        continue


def broadcast():
    command = {"client": username}
    encrypted_command = cipher_suite.encrypt(json.dumps(command).encode())
    client.publish("broadcast", encrypted_command)


def receive(msg):
    global near_devices, devices

    decrypted_msg = cipher_suite.decrypt(msg.payload)
    parsed_msg = json.loads(decrypted_msg)

    device = parsed_msg["device"]
    status = parsed_msg["status"]
    belongsto = parsed_msg["belongsto"]

    if device not in near_devices:
        near_devices.append(device)

    if username not in belongsto:
        return

    devices[device] = {"status": status}
    if device == "aircon":
        temperature = parsed_msg["value"]
        devices[device]["temperature"] = temperature


def bind(device):
    command = {"device": device, "client": username}
    encrypted_command = cipher_suite.encrypt(json.dumps(command).encode())
    client.publish("bind", encrypted_command)


def unbind(device):
    command = {"device": device, "client": username}
    encrypted_command = cipher_suite.encrypt(json.dumps(command).encode())
    client.publish("unbind", encrypted_command)
    del devices[device]


# 处理连接事件
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("成功连接到MQTT服务器")
    else:
        print("连接到MQTT服务器失败， 错误代码 %d\n", rc)

    # 开始订阅消息和启动消息循环
    client.subscribe("receive")

    # 发送状态查询请求
    command = {"client": username}
    encrypted_command = cipher_suite.encrypt(json.dumps(command).encode())
    client.publish("broadcast", encrypted_command)


# 处理消息事件
def on_message(client, userdata, msg):
    if msg.topic == "receive":
        receive(msg)


# 创建 MQTT 客户端对象
client = mqtt.Client(username)
client.username_pw_set(username, password)
client.on_connect = on_connect
client.on_message = on_message

# 连接 MQTT 服务器
client.connect(broker_address, 1883, 20)

# 启动消息循环
client.loop_start()

time.sleep(0.5)
main()

# 停止消息循环
client.loop_stop()
