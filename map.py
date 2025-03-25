import tkinter as tk
from tkinter import ttk, messagebox
import cv2
import numpy as np
from PIL import Image, ImageGrab, ImageTk
import threading
import time

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
        
        # 创建界面布局
        self.create_widgets()
        
        # 初始化OpenCV参数
        self.screen_region = (633,645, 140, 94)  # 截图区域
        
    def create_widgets(self):
        # 主容器
        main_frame = ttk.Frame(self.root, width=700, height=400)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 图像显示区域
        self.canvas = tk.Canvas(main_frame, width=500, height=400, bg='#2E2E2E')
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
        
    def initialize(self):
        """初始化画布并截取基准图"""
        try:
            # 创建500x400画布
            canvas = np.zeros((400, 500, 3), dtype=np.uint8)
            
            # 截取屏幕区域
            screen_img = ImageGrab.grab(bbox=(
                self.screen_region[0],
                self.screen_region[1],
                self.screen_region[0] + self.screen_region[2],
                self.screen_region[1] + self.screen_region[3]
            ))
            screen_cv = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2BGR)
            
            # 居中放置
            h, w = screen_cv.shape[:2]
            x = (500 - w) // 2
            y = (400 - h) // 2
            canvas[y:y+h, x:x+w] = screen_cv
            
            # 保存并显示
            self.current_big_image = canvas
            cv2.imwrite('base_image.bmp', canvas)
            self.update_canvas()
            self.log("初始化成功", 'success')
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
                # 截取模板图
                screen_img = ImageGrab.grab(bbox=(
                    self.screen_region[0],
                    self.screen_region[1],
                    self.screen_region[0] + self.screen_region[2],
                    self.screen_region[1] + self.screen_region[3]
                ))
                self.template = cv2.cvtColor(np.array(screen_img), cv2.COLOR_RGB2BGR)
                
                # 执行匹配和合并
                self.match_and_merge()
                self.update_canvas()
                
            except Exception as e:
                self.log(f"处理错误: {str(e)}", 'error')
                
            # 控制循环间隔
            elapsed = (time.time() - start_time) * 1000
            sleep_time = max(0, self.interval.get() - elapsed)
            time.sleep(sleep_time / 1000)
            
    def match_and_merge(self):
        """执行模板匹配和图像合并"""
        # 裁剪模板（保持原逻辑）
        cropped = self.template[5:-5, 5:-5]
        
        # 模板匹配
        result = cv2.matchTemplate(self.current_big_image, cropped, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        
        # 新增置信度检查
        if max_val < 0.5:
            self.log(f"低匹配置信度 {max_val:.2f}，跳过合并", 'error')
            return
        
        # 计算原始模板应放置的坐标（关键修复）
        original_x = max_loc[0] - 5  # 补偿左裁剪
        original_y = max_loc[1] - 5  # 补偿上裁剪
        
        # 合并图像（带边界保护）
        merged = self.current_big_image.copy()
        h, w = self.template.shape[:2]
        
        # 计算有效区域
        x1 = max(original_x, 0)
        y1 = max(original_y, 0)
        x2 = min(original_x + w, merged.shape[1])
        y2 = min(original_y + h, merged.shape[0])
        
        # 计算模板有效区域
        tx = 0 if original_x >=0 else abs(original_x)
        ty = 0 if original_y >=0 else abs(original_y)
        tw = x2 - x1
        th = y2 - y1
        
        # 执行安全合并
        if tw > 0 and th > 0:
            merged[y1:y2, x1:x2] = self.template[ty:ty+th, tx:tx+tw]
            self.current_big_image = merged
            self.log(f"成功合并 (X:{x1}-{x2} Y:{y1}-{y2})", 'success')
        else:
            self.log("无效合并区域，跳过", 'error')
        
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