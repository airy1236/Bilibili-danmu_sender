import urllib.request
import urllib.parse
import json
import os
import time
import threading
import tkinter as tk
from tkinter import messagebox, colorchooser, simpledialog, Toplevel
from PIL import Image, ImageTk

# 定义主题
themes = {
    "sxwz": {
        "color": "#A50C12", #禧运红
        "background": "photos/background_shining.jpg"
    },
    "queenie": {
        "color": "#A1D29A", #淡苹果绿
        "background": "photos/background_queenie.png"
    },
    "bekki": {
        "color": "#A7C9D3", #冰川湖泊
        "background": "photos/background_bekki.png"
    },
    "lian": {
        "color": "#E38691", #浅梨粉
        "background": "photos/background_lian.png"
    },
    "yoyi": {
        "color": "#E3BA09", #郁金
        "background": "photos/background_yoyi.png"
    }
}
current_theme = "lian"


CONFIG_FILE = "config/config.txt"  # 配置文件相对地址
MAX_COMMON_ROOM = 20               # 最多保存的常用直播间数量
running = False                    # 全局变量控制弹幕发送状态
time_step = 5                      # 发送弹幕的时间间隔
default_color = "#FFFFFF"          # 默认弹幕颜色
default_font_size = 25             # 默认字体大小
default_mode = 1                   # 默认弹幕模式

def load_config():
    """加载配置文件"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as file:
            config = json.load(file)
    else:
        config = {
            "common_rooms": {},
            "settings": {
                "time_step": time_step,
                "color": default_color,
                "font_size": default_font_size,
                "mode": default_mode,
                "theme": current_theme
            }
        }

    # 确保 settings 键存在
    if "settings" not in config:
        config["settings"] = {
            "time_step": time_step,
            "color": default_color,
            "font_size": default_font_size,
            "mode": default_mode,
            "theme": current_theme
        }

    # 确保 common_rooms 中的所有房间都有 danmus 键
    for room_id in config["common_rooms"]:
        if "danmus" not in config["common_rooms"][room_id]:
            config["common_rooms"][room_id]["danmus"] = []

    return config


def save_config(config):
    """保存配置文件"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as file:
        json.dump(config, file)


def send_danmu(room_id, message, csrf, csrf_token, sessdata, color, font_size, mode):
    """发送弹幕"""
    url = "https://api.live.bilibili.com/msg/send"
    headers = {
        "Cookie": f"SESSDATA={sessdata}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    }
    data = {
        "roomid": room_id,
        "msg": message,
        "rnd": int(time.time()),              # 随机数
        "color": int(color.lstrip('#'), 16),  # 弹幕颜色
        "fontsize": font_size,                # 字体大小
        "mode": mode,                         # 弹幕模式
        "csrf": csrf,
        "csrf_token": csrf_token
    }
    encoded_data = urllib.parse.urlencode(data).encode("utf-8")
    req = urllib.request.Request(url, data=encoded_data, headers=headers)

    try:
        with urllib.request.urlopen(req) as response:
            result = response.read().decode("utf-8")
            print(f"弹幕发送结果：{result}")
    except Exception as e:
        print(f"发送弹幕失败：{e}")


def start_sending_danmu(room_id, message, csrf, csrf_token, sessdata, color, font_size, mode):
    """循环发送弹幕"""
    global running
    while running:
        if not message:
            print("弹幕内容为空，停止发送")
            break
        send_danmu(room_id, message, csrf, csrf_token, sessdata, color, font_size, mode)
        time.sleep(time_step)  
        

def toggle_sending(room_id, message, csrf, csrf_token, sessdata, button, config):
    """控制发送状态的切换"""
    global running
    if running:
        running = False
        button.config(text="开始发送")
        print("已停止发送弹幕")
    else:
        running = True
        button.config(text="停止发送")
        print("开始发送弹幕")
        add_to_common_room(room_id, csrf, csrf_token, sessdata, config)
        threading.Thread(target=start_sending_danmu, args=(room_id, message, csrf, csrf_token, sessdata, config["settings"]["color"], config["settings"]["font_size"], config["settings"]["mode"]), daemon=True).start()


def add_to_common_room(room_id, csrf, csrf_token, sessdata, config):
    """将直播间添加到常用直播间列表中"""
    if room_id not in config["common_rooms"]:
        config["common_rooms"][room_id] = {"csrf": csrf, "csrf_token": csrf_token, "sessdata": sessdata, "danmus": []}
    else:
        # 确保 danmus 键存在
        if "danmus" not in config["common_rooms"][room_id]:
            config["common_rooms"][room_id]["danmus"] = []
    if len(config["common_rooms"]) > MAX_COMMON_ROOM:
        oldest_room_id = next(iter(config["common_rooms"]))
        del config["common_rooms"][oldest_room_id]
    save_config(config)
    update_common_rooms_display(config)


def on_select_common_room(room_id_entry, message_entry, room_id, config):
    """选择常用直播间"""
    global selected_room_id
    selected_room_id = room_id
    if room_id in config["common_rooms"]:
        room_info = config["common_rooms"][room_id]
        room_id_entry.delete(0, tk.END)
        room_id_entry.insert(0, room_id)

        csrf_entry.delete(0, tk.END)
        csrf_entry.insert(0, room_info.get("csrf", ""))
        csrf_token_entry.delete(0, tk.END)
        csrf_token_entry.insert(0, room_info.get("csrf_token", ""))
        sessdata_entry.delete(0, tk.END)
        sessdata_entry.insert(0, room_info.get("sessdata", ""))
        update_danmu_listbox(room_info.get("danmus", []))


def update_common_rooms_display(config):
    """更新常用直播间显示"""
    for widget in common_rooms_frame.winfo_children():
        widget.destroy()
    for room_id in config["common_rooms"].keys():
        button = tk.Button(common_rooms_frame, text=f"房间{room_id}", command=lambda r=room_id: on_select_common_room(room_id_entry, message_entry, r, config))
        button.pack(side=tk.TOP, fill=tk.X)


def choose_color(button, config):
    """选择弹幕颜色"""
    color_code = colorchooser.askcolor(title ="Choose color")[1]
    if color_code:
        config["settings"]["color"] = color_code
        save_config(config)
        button.config(bg=color_code)


def set_time_step(entry, config):
    """设置弹幕发送间隔"""
    try:
        new_time_step = float(entry.get())
        if new_time_step <= 0:
            raise ValueError("时间间隔必须大于0")
        config["settings"]["time_step"] = new_time_step
        save_config(config)
        messagebox.showinfo("成功", "时间间隔已更新！")
    except ValueError as e:
        messagebox.showwarning("警告", str(e))


def set_font_size(entry, config):
    """设置字体大小"""
    try:
        new_font_size = int(entry.get())
        if new_font_size <= 0:
            raise ValueError("字体大小必须大于0")
        config["settings"]["font_size"] = new_font_size
        save_config(config)
        messagebox.showinfo("成功", "字体大小已更新！")
    except ValueError as e:
        messagebox.showwarning("警告", str(e))


def set_mode(entry, config):
    """设置弹幕模式"""
    try:
        new_mode = int(entry.get())
        if new_mode < 1 or new_mode > 9:
            raise ValueError("弹幕模式必须在1到9之间")
        config["settings"]["mode"] = new_mode
        save_config(config)
        messagebox.showinfo("成功", "弹幕模式已更新！")
    except ValueError as e:
        messagebox.showwarning("警告", str(e))


def add_danmu(room_id, danmu_entry, config):
    """添加常用弹幕"""
    danmu = danmu_entry.get()
    if danmu and room_id in config["common_rooms"]:
        config["common_rooms"][room_id]["danmus"].append(danmu)
        save_config(config)
        update_danmu_listbox(config["common_rooms"][room_id]["danmus"])
        danmu_entry.delete(0, tk.END)
    elif not room_id in config["common_rooms"]:
        messagebox.showwarning("警告", "请选择一个有效的直播间！")
    elif not danmu:
        messagebox.showwarning("警告", "请输入弹幕内容！")


def delete_selected_danmu(config):
    """删除选中的常用弹幕"""
    selected_index = danmu_listbox.curselection()
    if selected_index:
        room_id = room_id_entry.get()
        if room_id in config["common_rooms"]:
            danmus = config["common_rooms"][room_id]["danmus"]
            index = selected_index[0]
            if 0 <= index < len(danmus):
                del danmus[index]
                save_config(config)
                update_danmu_listbox(danmus)
                messagebox.showinfo("成功", "弹幕已删除！")
            else:
                messagebox.showwarning("警告", "无效的选择！")
        else:
            messagebox.showwarning("警告", "请选择一个有效的直播间！")
    else:
        messagebox.showwarning("警告", "请选择要删除的弹幕！")


def delete_selected_room(config):
    """删除选中的直播间及其对应的信息"""
    global selected_room_id
    if selected_room_id is None:
        messagebox.showwarning("警告", "请选择一个有效的直播间！")
        return
    
    if selected_room_id in config["common_rooms"]:
        del config["common_rooms"][selected_room_id]
        save_config(config)
        update_common_rooms_display(config)
        messagebox.showinfo("成功", f"房间 {selected_room_id} 及其弹幕信息已删除！")
        clear_input_fields()
        selected_room_id = None
    else:
        messagebox.showwarning("警告", "请选择一个有效的直播间！")


def clear_input_fields():
    """清空输入字段"""
    room_id_entry.delete(0, tk.END)
    csrf_entry.delete(0, tk.END)
    csrf_token_entry.delete(0, tk.END)
    sessdata_entry.delete(0, tk.END)
    message_entry.delete('1.0', tk.END)
    update_danmu_listbox([])


def update_danmu_listbox(danmus):
    """更新弹幕列表框"""
    danmu_listbox.delete(0, tk.END)
    for danmu in danmus:
        danmu_listbox.insert(tk.END, danmu)
    
    # 绑定单击事件
    danmu_listbox.bind("<Button-1>", lambda event: copy_danmu_to_message(event))


def copy_danmu_to_message(event):
    """将选中的弹幕复制到弹幕内容框"""
    selected_index = danmu_listbox.curselection()
    if selected_index:
        selected_danmu = danmu_listbox.get(selected_index)
        message_entry.delete('1.0', tk.END)
        message_entry.insert('1.0', selected_danmu)


def resize_window(event, window, background_photo):
    """调整窗口大小以适应背景图片"""
    bg_width, bg_height = background_photo.width(), background_photo.height()
    window.geometry(f"{bg_width}x{bg_height}")


def show_danmu_mode_help():
    """显示弹幕模式帮助窗口"""
    help_window = Toplevel()
    help_window.title("弹幕模式说明")

    # 加载帮助图片
    help_image_path = "photos/danmu_modes_help.png"
    help_image = Image.open(help_image_path)
    help_photo = ImageTk.PhotoImage(help_image)

    # 创建标签显示图片
    label = tk.Label(help_window, image=help_photo)
    label.image = help_photo  # 保持对图片的引用，防止被垃圾回收
    label.pack()

    # 设置窗口固定大小为图片尺寸
    img_width, img_height = help_image.size
    help_window.geometry(f"{img_width}x{img_height}")

    # 设置窗口最大和最小尺寸为图片尺寸
    help_window.minsize(img_width, img_height)
    help_window.maxsize(img_width, img_height)


def apply_theme(theme_name):
    for button in [
        toggle_button, 
        save_button, 
        time_step_set_button, 
        font_size_set_button, 
        mode_set_button, 
        help_button, 
        add_danmu_button, 
        delete_danmu_button, 
        delete_room_button,
        ]:
        button.config(bg=themes[theme_name]["color"])
     
    for label in [
        common_rooms_label,
        room_id_label,
        csrf_label,
        csrf_token_label,
        sessdata_label,
        message_label,
        danmu_color_label,
        time_step_label,
        font_size_label,
        mode_label,
        danmu_list_label,
        add_danmu_label
        ]:
        label.config(bg=themes[theme_name]["color"])

    #更新背景图片
    background_image = Image.open(themes[theme_name]["background"])
    background_photo = ImageTk.PhotoImage(background_image)
    background_label.config(image=background_photo)
    background_label.image = background_photo  # 保持对图片的引用，防止被垃圾回收


def change_theme(config, theme_name):
    """切换主题"""    
    try:
        current_theme = theme_name
        config["settings"]["theme"] = current_theme
        save_config(config)
        apply_theme(current_theme)
        messagebox.showinfo("成功", "主题切换成功！")
    except ValueError as e:
        messagebox.showwarning("警告", str(e))


#按钮背景图片
class ImageButton(tk.Button):
    def __init__(self, master=None, image_path=None, command=None, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.image_path = image_path
        self.command = command
        self.photo = ImageTk.PhotoImage(Image.open(self.image_path))
        self.config(image=self.photo, bd=0, highlightthickness=0, relief='flat')
        self.bind("<Button-1>", self.on_click)

    def on_click(self, event):
        if self.command:
            self.command()


def main():
    """主函数，初始化GUI"""
    global common_rooms_frame, room_id_entry, message_entry, csrf_entry, csrf_token_entry, sessdata_entry, time_step_entry, font_size_entry, mode_entry, danmu_entry, danmu_listbox, selected_room_id, delete_room_button, save_button, toggle_button, color_button, time_step_set_button, font_size_set_button, mode_set_button, help_button, add_danmu_button, delete_danmu_button, common_rooms_label, room_id_label, csrf_label, csrf_token_label, sessdata_label, message_label, danmu_color_label, time_step_label, font_size_label, mode_label, danmu_list_label, add_danmu_label, background_label
    
    config = load_config()
    current_theme = config["settings"]["theme"]

    # 创建窗口
    window = tk.Tk()
    window.title("Bilibili 弹幕发送器")

    # 初始化全局变量
    selected_room_id = None

    # 设置窗口图标
    icon = tk.PhotoImage(file="photos/icon.png")
    window.iconphoto(True, icon)

    # 加载背景图片
    background_image_path = themes[current_theme]["background"]
    background_image = Image.open(background_image_path)
    background_photo = ImageTk.PhotoImage(background_image)

    # 获取背景图片的尺寸
    bg_width, bg_height = background_image.size

    # 设置窗口固定大小为背景图片的尺寸
    fixed_width = 800
    fixed_height = 600
    window.geometry(f"{fixed_width}x{fixed_height}")
    
    # 禁止用户调整窗口大小
    window.resizable(False, False)

    # 设置窗口最大和最小尺寸为固定值
    window.minsize(fixed_width, fixed_height)
    window.maxsize(fixed_width, fixed_height)

    # 创建背景标签
    background_label = tk.Label(window, image=background_photo)
    background_label.image = background_photo  # 保持对图片的引用，防止被垃圾回收
    background_label.place(x=0, y=0, relwidth=1, relheight=1)

    # 监听窗口大小改变事件
    window.bind('<Configure>', lambda event: resize_window(event, window, background_photo))

    # 添加鼠标拖动功能
    def on_drag_start(event):
        window._drag_start_x = event.x_root
        window._drag_start_y = event.y_root

    def on_drag_motion(event):
        delta_x = event.x_root - window._drag_start_x
        delta_y = event.y_root - window._drag_start_y
        new_x = window.winfo_x() + delta_x
        new_y = window.winfo_y() + delta_y
        window.geometry(f"+{new_x}+{new_y}")
        window._drag_start_x = event.x_root
        window._drag_start_y = event.y_root

    # 将鼠标左键按下事件绑定到on_drag_start
    background_label.bind("<ButtonPress-1>", on_drag_start)
    # 将鼠标左键移动事件绑定到on_drag_motion
    background_label.bind("<B1-Motion>", on_drag_motion)

    # 常用直播间显示
    common_rooms_label = tk.Label(window, text="常用直播间:", bg=themes[current_theme]["color"])
    common_rooms_label.grid(row=0, column=0, padx=5, pady=5, sticky="w")
    common_rooms_frame = tk.Frame(window, bg='white')
    common_rooms_frame.grid(row=1, column=0, rowspan=5, padx=5, pady=5, sticky="nsew")
    update_common_rooms_display(config)

    # 删除直播间按钮
    delete_room_button = tk.Button(window, text="删除直播间", command=lambda: delete_selected_room(config), bg=themes[current_theme]["color"])
    delete_room_button.grid(row=6, column=0, padx=5, pady=5, sticky="ew")

    # 直播间ID输入
    room_id_label = tk.Label(window, text="直播间ID:", bg=themes[current_theme]["color"])
    room_id_label.grid(row=0, column=1, padx=5, pady=5, sticky="w")
    room_id_entry = tk.Entry(window)
    room_id_entry.grid(row=0, column=2, padx=5, pady=5, sticky="ew")

    # CSRF输入
    csrf_label = tk.Label(window, text="CSRF:", bg=themes[current_theme]["color"])
    csrf_label.grid(row=1, column=1, padx=5, pady=5, sticky="w")
    csrf_entry = tk.Entry(window)
    csrf_entry.grid(row=1, column=2, padx=5, pady=5, sticky="ew")

    # CSRF_TOKEN输入
    csrf_token_label = tk.Label(window, text="CSRF_TOKEN:", bg=themes[current_theme]["color"])
    csrf_token_label.grid(row=2, column=1, padx=5, pady=5, sticky="w")
    csrf_token_entry = tk.Entry(window)
    csrf_token_entry.grid(row=2, column=2, padx=5, pady=5, sticky="ew")

    # SESSDATA输入
    sessdata_label = tk.Label(window, text="COOKIE:", bg=themes[current_theme]["color"])
    sessdata_label.grid(row=3, column=1, padx=5, pady=5, sticky="w")
    sessdata_entry = tk.Entry(window)
    sessdata_entry.grid(row=3, column=2, padx=5, pady=5, sticky="ew")

    # 保存配置按钮
    def save_inputs():
        nonlocal config
        room_id = room_id_entry.get()
        csrf = csrf_entry.get()
        csrf_token = csrf_token_entry.get()
        sessdata = sessdata_entry.get()
        
        if room_id and csrf and csrf_token and sessdata:
            config["common_rooms"][room_id] = {"csrf": csrf, "csrf_token": csrf_token, "sessdata": sessdata, "danmus": list(danmu_listbox.get(0, tk.END))}
            if len(config["common_rooms"]) > MAX_COMMON_ROOM:
                oldest_room_id = next(iter(config["common_rooms"]))
                del config["common_rooms"][oldest_room_id]
            save_config(config)
            update_common_rooms_display(config)
            messagebox.showinfo("保存成功", "配置信息已保存！")
        else:
            messagebox.showwarning("警告", "请填写所有必要的字段！")

    save_button = tk.Button(window, text="保存配置", command=save_inputs, bg=themes[current_theme]["color"])
    save_button.grid(row=4, column=1, columnspan=2, pady=5, sticky="ew")

    # 弹幕内容输入
    message_label = tk.Label(window, text="弹幕内容:", bg=themes[current_theme]["color"])
    message_label.grid(row=5, column=1, padx=5, pady=5, sticky="w")
    message_entry = tk.Text(window, height=2, width=30)
    message_entry.grid(row=5, column=2, padx=5, pady=5, sticky="ew")

    # 开始/停止发送按钮
    toggle_button = tk.Button(
        window,
        text="开始发送",
        command=lambda: toggle_sending(
            room_id_entry.get(),
            message_entry.get('1.0', tk.END).strip(),
            csrf_entry.get(),
            csrf_token_entry.get(),
            sessdata_entry.get(),
            toggle_button,
            config
        ),
        bg=themes[current_theme]["color"]
    )
    toggle_button.grid(row=6, column=1, columnspan=2, pady=5, sticky="ew")

    # 弹幕颜色选择
    danmu_color_label = tk.Label(window, text="弹幕颜色:", bg=themes[current_theme]["color"])
    danmu_color_label.grid(row=0, column=3, padx=5, pady=5, sticky="w")
    color_button = tk.Button(window, text="", bg=config["settings"]["color"], width=10, command=lambda: choose_color(color_button, config))
    color_button.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

    # 弹幕发送间隔输入
    time_step_label = tk.Label(window, text="发送间隔 (秒):", bg=themes[current_theme]["color"])
    time_step_label.grid(row=1, column=3, padx=5, pady=5, sticky="w")
    time_step_entry = tk.Entry(window)
    time_step_entry.grid(row=1, column=4, padx=5, pady=5, sticky="ew")
    time_step_entry.insert(0, str(config["settings"]["time_step"]))

    # 设置发送间隔按钮
    time_step_set_button = tk.Button(window, text="设置间隔", command=lambda: set_time_step(time_step_entry, config), bg=themes[current_theme]["color"])
    time_step_set_button.grid(row=1, column=5, padx=5, pady=5, sticky="ew")

    # 字体大小输入
    font_size_label = tk.Label(window, text="字体大小:", bg=themes[current_theme]["color"])
    font_size_label.grid(row=2, column=3, padx=5, pady=5, sticky="w")
    font_size_entry = tk.Entry(window)
    font_size_entry.grid(row=2, column=4, padx=5, pady=5, sticky="ew")
    font_size_entry.insert(0, str(config["settings"]["font_size"]))

    # 设置字体大小按钮
    font_size_set_button = tk.Button(window, text="设置字体大小", command=lambda: set_font_size(font_size_entry, config), bg=themes[current_theme]["color"])
    font_size_set_button.grid(row=2, column=5, padx=5, pady=5, sticky="ew")

    # 弹幕模式输入
    mode_label = tk.Label(window, text="弹幕模式 (1-3):", bg=themes[current_theme]["color"])
    mode_label.grid(row=3, column=3, padx=5, pady=5, sticky="w")
    mode_entry = tk.Entry(window)
    mode_entry.grid(row=3, column=4, padx=5, pady=5, sticky="ew")
    mode_entry.insert(0, str(config["settings"]["mode"]))

    # 设置弹幕模式按钮
    mode_set_button = tk.Button(window, text="设置模式", command=lambda: set_mode(mode_entry, config), bg=themes[current_theme]["color"])
    mode_set_button.grid(row=3, column=5, padx=5, pady=5, sticky="ew")

    # 显示弹幕模式帮助按钮
    help_button = tk.Button(window, text="查看模式说明", command=show_danmu_mode_help, bg=themes[current_theme]["color"])
    help_button.grid(row=3, column=6, padx=5, pady=5, sticky="ew")

    # 常用弹幕列表
    danmu_list_label = tk.Label(window, text="常用弹幕:", bg=themes[current_theme]["color"])
    danmu_list_label.grid(row=4, column=3, padx=5, pady=5, sticky="w")
    danmu_listbox = tk.Listbox(window, height=10, width=30)
    danmu_listbox.grid(row=5, column=3, columnspan=3, padx=5, pady=5, sticky="nsew")

    # 添加常用弹幕输入
    add_danmu_label = tk.Label(window, text="添加常用弹幕:", bg=themes[current_theme]["color"])
    add_danmu_label.grid(row=6, column=3, padx=5, pady=5, sticky="w")
    danmu_entry = tk.Entry(window)
    danmu_entry.grid(row=6, column=4, padx=5, pady=5, sticky="ew")

    # 添加常用弹幕按钮
    add_danmu_button = tk.Button(window, text="添加弹幕", command=lambda: add_danmu(room_id_entry.get(), danmu_entry, config), bg=themes[current_theme]["color"])
    add_danmu_button.grid(row=6, column=5, padx=5, pady=5, sticky="ew")
    
    # 删除常用弹幕按钮
    delete_danmu_button = tk.Button(window, text="删除弹幕", command=lambda: delete_selected_danmu(config), bg=themes[current_theme]["color"])
    delete_danmu_button.grid(row=6, column=6, padx=5, pady=5, sticky="ew")

    # 主题切换按钮
    theme_buttons_frame = tk.Frame(window)
    theme_buttons_frame.grid(row=3, column=6, rowspan=4, columnspan=1, padx=5, pady=5, sticky="ew")

    sxwz_button = ImageButton(theme_buttons_frame, image_path="photos/button_sxwz.png", command=lambda: change_theme(config, "sxwz"))
    sxwz_button.pack(side=tk.TOP, padx=5, pady=5)

    queenie_button = ImageButton(theme_buttons_frame, image_path="photos/button_queenie.png", command=lambda: change_theme(config, "queenie"))
    queenie_button.pack(side=tk.TOP, padx=5, pady=5)

    bekki_button = ImageButton(theme_buttons_frame, image_path="photos/button_bekki.png", command=lambda: change_theme(config, "bekki"))
    bekki_button.pack(side=tk.TOP, padx=5, pady=5)

    lian_button = ImageButton(theme_buttons_frame, image_path="photos/button_lian.png", command=lambda: change_theme(config, "lian"))
    lian_button.pack(side=tk.TOP, padx=5, pady=5)

    yoyi_button = ImageButton(theme_buttons_frame, image_path="photos/button_yoyi.png", command=lambda: change_theme(config, "yoyi"))
    yoyi_button.pack(side=tk.TOP, padx=5, pady=5)

    # 配置网格权重，使某些列和行能够扩展
    window.grid_rowconfigure((0, 1, 2, 3, 4, 5, 6, 7, 8), weight=1)
    window.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6), weight=1)

    # 运行窗口
    window.mainloop()


if __name__ == "__main__":
    main()
