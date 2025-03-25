import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageGrab, ImageTk
import threading
import time
import win32gui
import win32con

class ImageProcessingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("循环图像处理软件")
        
        # 初始化变量
        self.is_running = False
        self.current_big_image = None
        self.template = None
        self.interval = tk.IntVar(value=100)
        self.log_counter = 0
        self.target_hwnd = None
        self.capture_region = (580, 598, 126, 92)  # 窗口客户区截图区域
        
        # 创建界面布局
        self.create_widgets()
        
        # 初始化窗口绑定
        self.bind_game_window()
        self.bg_color = (255, 255, 255)  # 白色背景

    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self.root, width=710, height=510)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图像显示区域
        self.canvas = tk.Canvas(main_frame, width=500, height=400, bg='#fff')
        self.canvas.pack(side=tk.LEFT)
        
        # 控制面板
        control_frame = ttk.Frame(main_frame, width=200)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        # 控制按钮
        ttk.Button(control_frame, text="初始化", command=self.initialize).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="开始", command=self.start).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="停止", command=self.stop).pack(pady=5, fill=tk.X)
        ttk.Button(control_frame, text="保存", command=self.save_image).pack(pady=5, fill=tk.X)
        
        # 间隔控制
        ttk.Label(control_frame, text="循环间隔(ms):").pack(pady=5)
        ttk.Entry(control_frame, textvariable=self.interval).pack()
        
        # 日志区域
        self.log_text = tk.Text(control_frame, height=15, width=24, state=tk.DISABLED)
        self.log_text.pack(pady=5)
        self.log_text.tag_config('info', foreground='blue')
        self.log_text.tag_config('success', foreground='green')
        self.log_text.tag_config('error', foreground='red')

    def bind_game_window(self):
        """绑定到龙之谷怀旧服窗口"""
        self.target_hwnd = win32gui.FindWindow(None, "龙之谷怀旧服")
        if not self.target_hwnd:
            self.log("未找到游戏窗口，请先启动游戏！", 'error')
            return False
        
        self.log("已绑定游戏窗口", 'success')
        return True

    def get_window_snapshot(self):
        """获取窗口客户区指定区域的截图"""
        if not self.target_hwnd or not win32gui.IsWindowVisible(self.target_hwnd):
            if not self.bind_game_window():
                return None
            
        try:
            # 获取窗口客户区坐标
            client_rect = win32gui.GetClientRect(self.target_hwnd)
            client_left, client_top, client_right, client_bottom = client_rect
            
            # 转换为屏幕坐标
            (abs_left, abs_top) = win32gui.ClientToScreen(self.target_hwnd, (client_left, client_top))
            (abs_right, abs_bottom) = win32gui.ClientToScreen(self.target_hwnd, (client_right, client_bottom))
            
            # 计算目标区域
            x, y, w, h = self.capture_region
            region = (
                abs_left + x,
                abs_top + y,
                abs_left + x + w,
                abs_top + y + h
            )
            
            # 截取屏幕区域
            return ImageGrab.grab(bbox=region)
        except Exception as e:
            self.log(f"截图失败: {str(e)}", 'error')
            return None

    def initialize(self):
        """初始化画布并截取基准图"""
        try:
            # 创建500x400画布
            canvas = np.full((400, 500, 3), self.bg_color, dtype=np.uint8)
            
            # 获取窗口截图
            screen_img = self.get_window_snapshot()
            if screen_img is None:
                return
                
            screen_cv = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2BGR)
            
            # 获取截图尺寸
            h, w = screen_cv.shape[:2]
            
            # 计算精确中心坐标
            x_center = 250  # 画布中心X
            y_center = 200  # 画布中心Y
            x_start = x_center - w // 2
            y_start = y_center - h // 2
            
            # 边界保护
            x_start = max(0, x_start)
            y_start = max(0, y_start)
            x_end = min(500, x_start + w)
            y_end = min(400, y_start + h)
            
            # 调整有效区域
            canvas[y_start:y_end, x_start:x_end] = screen_cv[
                0:(y_end - y_start), 
                0:(x_end - x_start)
            ]
            
            # 保存并显示
            self.current_big_image = canvas
            cv2.imwrite('base_image.bmp', canvas)
            self.update_canvas()
            self.log(f"基准图已中心放置 (X:{x_start}-{x_end} Y:{y_start}-{y_end})", 'success')
        except Exception as e:
            self.log(f"初始化失败: {str(e)}", 'error')
            
    def start(self):
        """启动处理循环"""
        if self.current_big_image is None:
            messagebox.showwarning("警告", "请先初始化!")
            return
            
        self.is_running = True
        self.log("开始处理循环", 'info')
        threading.Thread(target=self.processing_loop, daemon=True).start()
        
    def stop(self):
        """停止处理循环"""
        self.is_running = False
        self.log("已停止处理", 'info')
        
    def save_image(self):
        """保存当前图像"""
        if self.current_big_image is not None:
            filename = f"result_{int(time.time())}.bmp"
            cv2.imwrite(filename, self.current_big_image)
            self.log(f"已保存: {filename}", 'success')
            
    def processing_loop(self):
        """处理循环主逻辑"""
        while self.is_running:
            start_time = time.time()
            
            try:
                # 截取完整模板图
                screen_img = self.get_window_snapshot()
                if screen_img is None:
                    continue
                    
                full_template = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2BGR)
                
                # 截取ROI区域（模板图中的9,7,48,41区域）
                roi_in_template = full_template[7:48, 9:57]  # y从7到48，x从9到57
                
                # 执行匹配和合并
                if self.match_and_merge(full_template, roi_in_template):
                    self.update_canvas()
                
            except Exception as e:
                self.log(f"处理错误: {str(e)}", 'error')
                
            # 控制循环间隔
            elapsed = (time.time() - start_time) * 1000
            sleep_time = max(0, self.interval.get() - elapsed)
            time.sleep(sleep_time / 1000)

    def match_and_merge(self, full_template, roi_template):
        """执行模板匹配和完整模板合并"""
        # 参数说明：
        # full_template: 完整模板图（需要合并的部分）
        # roi_template: 用于匹配的ROI区域
        
        # 执行模板匹配
        result = cv2.matchTemplate(self.current_big_image, roi_template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        # 置信度检查（根据ROI尺寸调整）
        if max_val < 0.7:
            self.log(f"匹配失败 {max_val:.2f} < 0.7", 'error')
            return False
        
        # 计算完整模板的放置位置（关键逻辑）
        # ROI在模板图中的位置偏移量（9,7）
        roi_offset_x = 9  # ROI在模板图中的x起点
        roi_offset_y = 7  # ROI在模板图中的y起点
        
        # 计算完整模板应放置的位置
        template_h, template_w = full_template.shape[:2]
        target_x = max_loc[0] - roi_offset_x  # 大图上的x坐标
        target_y = max_loc[1] - roi_offset_y  # 大图上的y坐标
        
        # 边界保护计算
        # 有效目标区域（在大图中）
        x1 = max(target_x, 0)
        y1 = max(target_y, 0)
        x2 = min(target_x + template_w, self.current_big_image.shape[1])
        y2 = min(target_y + template_h, self.current_big_image.shape[0])
        
        # 对应的模板区域
        temp_x = max(0 - target_x, 0)
        temp_y = max(0 - target_y, 0)
        temp_w = x2 - x1
        temp_h = y2 - y1
        
        if temp_w <= 0 or temp_h <= 0:
            self.log("无效合并区域，跳过", 'error')
            return False
        
        # 执行图像合并
        try:
            # 获取模板的有效区域
            template_region = full_template[temp_y:temp_y+temp_h, temp_x:temp_x+temp_w]
            
            # 合并到当前大图
            self.current_big_image[y1:y2, x1:x2] = template_region
            self.log(f"成功合并完整模板 (X:{x1}-{x2} Y:{y1}-{y2})", 'success')
            return True
        except Exception as e:
            self.log(f"合并失败: {str(e)}", 'error')
            return False
        
    def update_canvas(self):
        """更新画布显示"""
        if self.current_big_image is not None:
            img = cv2.cvtColor(self.current_big_image, cv2.COLOR_BGR2RGB)
            img = ImageTk.PhotoImage(Image.fromarray(img))
            self.canvas.create_image(0, 0, anchor=tk.NW, image=img)
            self.canvas.image = img  # 保持引用
            
    def log(self, message, tag='info'):
        """记录日志"""
        self.log_counter += 1
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"{self.log_counter}. {message}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app = ImageProcessingApp(root)
    root.mainloop()