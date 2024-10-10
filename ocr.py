import datetime
import sys
import threading
import time
import tkinter as tk

import cv2
import keyboard
import numpy as np
import pyautogui
import pytesseract
from PIL import ImageGrab
'''
需要根据设备调整的部分
'''
# 设置 Tesseract 的路径（根据需要调整）
pytesseract.pytesseract.tesseract_cmd = r'D:\Program\Tesseract-OCR\tesseract.exe'

# 定义截图区域的坐标 (左上角和右下角坐标)，根据实际屏幕位置调整
region1 = (850, 400, 1000, 520)  # 区域1的左上角x, y，右下角x, y
region2 = (1150, 400, 1300, 520)  # 区域2的左上角x, y，右下角x, y

# 定义点击位置的坐标
pause_button = (2040, 1320)  # 暂停(草稿)按键坐标
continue_button_first = (1000, 1200)  # PK结束后需要点击的三个按键
continue_button_second = (1200, 1380)
continue_button_third = (1080, 1260)

# 全局状态变量
last_result = None
same_result_count = 0
keep_running = False
gui_label = None
gui_initialized = False
region = 1
blue_one = None
blue_two = None


# 从屏幕截取指定区域的图像
def capture_region(region):
    screenshot = ImageGrab.grab(bbox=region)
    screenshot = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    return screenshot


# 提取图像中的数字并进行预处理
def extract_number_from_image(image):
    global region, canvas, blue_one, blue_two
    try:
        lower_bound = np.array([18, 18, 18])  # 阈值下限
        upper_bound = np.array([40, 40, 40])  # 阈值上限
        mask = cv2.inRange(image, lower_bound, upper_bound)
        coords = cv2.findNonZero(mask)

        if coords is not None:
            x, y, w, h = cv2.boundingRect(coords)
            cropped_image = mask[y - 5:y + h + 5, x - 5:x + w + 5]
            inverted_img = cv2.bitwise_not(cropped_image)
            text = pytesseract.image_to_string(inverted_img, config='--psm 8 digits')
            digits = ''.join(filter(str.isdigit, text))
            if region == 1 and canvas:
                if blue_one:
                    canvas.delete(blue_one)
                blue_one = canvas.create_rectangle(region1[0] + x, region1[1] + y, region1[0] + x + w,
                                                   region1[1] + y + h, outline="royalblue", width=5)
                region = 2
            elif region == 2 and canvas:
                if blue_two:
                    canvas.delete(blue_two)
                blue_two = canvas.create_rectangle(region2[0] + x, region2[1] + y, region2[0] + x + w,
                                                   region2[1] + y + h, outline="royalblue", width=5)
                region = 1
            elif not canvas:
                return

            if len(digits) >= 2:
                number = int(digits[:2])
            elif len(digits) > 0:
                number = int(digits)
            else:
                number = None

            return number, inverted_img
        else:
            return None, mask

    except (ValueError, TypeError) as e:
        print(f"识别数字时发生错误: {e}")
        return None, image


# 绘制大于号
def draw_bigger():
    center_x, center_y = pyautogui.size()[0] // 2, pyautogui.size()[1] // 2 + 350
    pyautogui.moveTo(center_x - 25, center_y)
    pyautogui.dragTo(center_x + 25, center_y + 30, duration=0.001)
    pyautogui.dragTo(center_x - 25, center_y + 60, duration=0.001)


# 绘制小于号
def draw_less():
    center_x, center_y = pyautogui.size()[0] // 2, pyautogui.size()[1] // 2 + 350
    pyautogui.moveTo(center_x + 40, center_y - 18)
    pyautogui.dragTo(center_x - 80, center_y + 30, duration=0.001)
    pyautogui.dragTo(center_x + 40, center_y + 78, duration=0.001)


def draw_equal():
    center_x, center_y = pyautogui.size()[0] // 2, pyautogui.size()[1] // 2 + 350
    pyautogui.moveTo(center_x - 40, center_y + 30)
    pyautogui.dragTo(center_x + 40, center_y + 30, duration=0.001)
    pyautogui.moveTo(center_x - 40, center_y + 78)
    pyautogui.dragTo(center_x + 40, center_y + 78, duration=0.001)


# 比较区域中的数字
def compare_regions():
    global last_result, same_result_count

    # 截取并提取区域的数字
    number1, processed_image1 = extract_number_from_image(capture_region(region1))
    number2, processed_image2 = extract_number_from_image(capture_region(region2))

    if number1 is None or number2 is None:
        print("无法识别区域中的数字")
        return

    print(f"区域1的数字: {number1}, 区域2的数字: {number2}")
    current_result = (number1, number2)

    # 检测是否有连续的相同结果
    if current_result == last_result:
        same_result_count += 1
    else:
        same_result_count = 0  # 重置计数

    if same_result_count >= 1:
        print("识别结果相同2次，暂停0.4秒...")  # 防卡死
        update_gui("识别结果相同2次，暂停0.4秒...", color="darkorange")
        time.sleep(0.4)
        same_result_count = 0  # 重置

    last_result = current_result

    # 根据比较结果执行相应动作
    if number1 > number2:
        draw_bigger()
        update_gui(f"{number1} 大于 {number2}", color="royalblue")
        print(f"{number1}大于{number2}")
    elif number1 < number2:
        draw_less()
        update_gui(f"{number1} 小于 {number2}", color="royalblue")
        print(f"{number1}小于{number2}")
    else:
        draw_equal()
        update_gui(f"{number1} 等于 {number2}", color="royalblue")
        print(f"{number1}等于{number2}")
    pyautogui.click(pause_button)
    pyautogui.click(pause_button)


# 连续比较线程
def continuous_compare():
    global keep_running
    while keep_running:
        compare_regions()


# 更新 GUI 显示信息
def update_gui(message, color="green"):
    global gui_initialized
    if not gui_initialized:
        print("GUI 未初始化，信息：", message)  # GUI 未准备好时打印到控制台
        return
    current_time = datetime.datetime.now().strftime('%H:%M:%S')
    full_message = f"[{current_time}]  {message}"
    gui_label.config(text=full_message, fg=color)


# 创建透明窗口和绘制红框
def create_gui():
    global gui_label, gui_initialized, canvas
    # 创建主窗口
    root = tk.Tk()
    root.geometry(f"{root.winfo_screenwidth()}x{root.winfo_screenheight()}+0+0")
    root.overrideredirect(True)  # 隐藏窗口边框
    root.attributes("-topmost", True)  # 保持窗口在最前端
    root.attributes("-transparentcolor", "white")  # 设置透明色

    # 创建画布
    canvas = tk.Canvas(root, width=root.winfo_screenwidth(), height=root.winfo_screenheight(), bg='white')
    canvas.pack()

    # 绘制两个红框来标记区域
    # canvas.create_rectangle(region1[0], region1[1], region1[2], region1[3], outline="brown", width=5)
    # canvas.create_rectangle(region2[0], region2[1], region2[2], region2[3], outline="brown", width=5)

    # 创建标签用于显示调试信息（时间和比较结果）
    gui_label = tk.Label(root, text="", font=('Microsoft YaHei', 12, 'bold'), fg='green')
    gui_label.place(x=20, y=root.winfo_screenheight() - 50)

    # 标志 GUI 初始化完成
    gui_initialized = True

    # 绑定 ESC 键关闭窗口
    root.bind('<Escape>', lambda e: root.quit())

    # 运行 GUI 主循环
    root.mainloop()


# 按下空格开始比较
def on_space_press():
    global keep_running
    if not keep_running:
        keep_running = True
        print("开始持续比较区域中的数字...")
        update_gui("开始持续比较区域中的数字...", color="darkorange")
        threading.Thread(target=continuous_compare, daemon=True).start()
    else:
        print("程序已在运行...")


# 按下 ESC 结束程序
def stop_on_esc():
    global keep_running
    print("检测到按下ESC键，停止程序。")
    sys.exit()


# 定时点击功能
def timed_click():
    while True:
        time.sleep(50)  # 每52秒执行一次点击
        print("执行定时点击...")
        update_gui("执行定时点击...", color="darkorange")
        pyautogui.click(1000, 1200)
        time.sleep(0.5)
        pyautogui.click(1200, 1380)
        time.sleep(0.5)
        pyautogui.click(1080, 1260)


if __name__ == "__main__":
    # 设置按键监听
    keyboard.add_hotkey('space', on_space_press)  # 空格键启动
    keyboard.add_hotkey('esc', stop_on_esc)  # ESC键停止

    # 启动 GUI 界面
    threading.Thread(target=create_gui, daemon=True).start()

    # 延迟调用，等待 GUI 初始化
    while not gui_initialized:
        time.sleep(0.1)

    # GUI 初始化后，调用更新界面函数
    update_gui("按下空格键运行程序，按下ESC键停止程序。", color="darkorange")

    # 启动定时点击线程
    threading.Thread(target=timed_click, daemon=True).start()

    # 保持主线程运行，监听按键
    while True:
        time.sleep(0.1)
