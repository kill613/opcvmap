import sys
import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton,
                            QFileDialog, QVBoxLayout, QHBoxLayout, QWidget,
                            QMessageBox, QScrollArea, QSplitter, QTextEdit)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QImage, QPixmap
from PIL import ImageGrab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # 固定截图区域参数
        self.fixed_rect = QRect(611, 700, 140, 94)
        # 初始化界面
        self.init_ui()
        # 图像存储变量
        self.current_big_image = None     # 动态更新的基准大图
        self.original_template = None     # 初始模板图像
        # 定时器设置
        self.screenshot_timer = QTimer()
        self.screenshot_timer.setInterval(50)
        self.screenshot_timer.timeout.connect(self.process_loop)
        # 状态控制
        self.is_processing = False
        self.log_counter = 0
        self.blend_alpha = 0.5  # 融合透明度

    def init_ui(self):
        """界面初始化"""
        self.setWindowTitle("动态图像融合系统")
        self.setGeometry(100, 100, 1200, 800)
        
        # 控件创建
        self.btn_init = QPushButton("初始化基准图")
        self.btn_set_template = QPushButton("设置模板")
        self.btn_start = QPushButton("开始融合")
        self.btn_stop = QPushButton("停止")
        self.btn_save = QPushButton("保存结果")
        
        # 图像显示区
        self.big_image_label = QLabel("等待初始化基准图...")
        self.big_image_label.setAlignment(Qt.AlignCenter)
        self.big_scroll = QScrollArea()
        self.big_scroll.setWidget(self.big_image_label)
        
        # 模板显示区
        self.template_label = QLabel("模板未设置")
        self.template_label.setFixedSize(200, 150)
        
        # 日志系统
        self.log_view = QTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setStyleSheet("""
            QTextEdit { 
                background: #1E1E1E; 
                color: #D4D4D4; 
                font-family: Consolas; 
                font-size: 10pt; 
            }""")

        # 布局管理
        right_panel = QSplitter(Qt.Vertical)
        right_panel.addWidget(self.template_label)
        right_panel.addWidget(self.log_view)
        
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.addWidget(self.big_scroll)
        main_splitter.addWidget(right_panel)
        
        control_bar = QHBoxLayout()
        control_bar.addWidget(self.btn_init)
        control_bar.addWidget(self.btn_set_template)
        control_bar.addWidget(self.btn_start)
        control_bar.addWidget(self.btn_stop)
        control_bar.addWidget(self.btn_save)
        
        main_layout = QVBoxLayout()
        main_layout.addLayout(control_bar)
        main_layout.addWidget(main_splitter)
        
        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)
        
        # 信号连接
        self.btn_init.clicked.connect(self.init_base_image)
        self.btn_set_template.clicked.connect(self.set_template)
        self.btn_start.clicked.connect(self.start_fusion)
        self.btn_stop.clicked.connect(self.stop_fusion)
        self.btn_save.clicked.connect(self.save_result)

    def log(self, message, status="INFO"):
        """日志记录系统"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_counter += 1
        
        # 状态颜色映射
        color = {
            "INFO": "#2196F3",
            "SUCCESS": "#4CAF50",
            "WARNING": "#FFC107",
            "ERROR": "#F44336"
        }.get(status, "#2196F3")
        
        # 日志条目格式
        log_entry = f"""
        <div style="margin:2px 0;">
            <span style="color:#757575;">[{self.log_counter}] {timestamp}</span>
            <span style="color:{color};">[{status}]</span>
            {message}
        </div>
        """
        
        # 容量控制
        if self.log_counter > 200:
            self.log_view.clear()
            self.log_counter = 0
            
        self.log_view.append(log_entry)
        self.log_view.verticalScrollBar().setValue(
            self.log_view.verticalScrollBar().maximum()
        )

    def init_base_image(self):
        """初始化基准图像"""
        try:
            # 截取预设区域
            screen = ImageGrab.grab(bbox=(
                self.fixed_rect.x(),
                self.fixed_rect.y(),
                self.fixed_rect.x() + self.fixed_rect.width(),
                self.fixed_rect.y() + self.fixed_rect.height()
            ))
            self.current_big_image = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
            self.update_display()
            self.log("基准图初始化成功", "SUCCESS")
        except Exception as e:
            self.log(f"基准图初始化失败: {str(e)}", "ERROR")

    def set_template(self):
        """设置匹配模板"""
        try:
            screen = ImageGrab.grab(bbox=(
                self.fixed_rect.x(),
                self.fixed_rect.y(),
                self.fixed_rect.x() + self.fixed_rect.width(),
                self.fixed_rect.y() + self.fixed_rect.height()
            ))
            self.original_template = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
            
            # 更新模板显示
            h, w = self.original_template.shape[:2]
            bytes_per_line = 3 * w
            q_img = QImage(self.original_template.data, w, h, bytes_per_line, QImage.Format_BGR888)
            pixmap = QPixmap.fromImage(q_img).scaled(200, 150, Qt.KeepAspectRatio)
            self.template_label.setPixmap(pixmap)
            
            self.log(f"模板设置成功 {w}x{h}", "SUCCESS")
        except Exception as e:
            self.log(f"模板设置失败: {str(e)}", "ERROR")

    def start_fusion(self):
        """启动融合流程"""
        if self.current_big_image is None:
            self.log("请先初始化基准图", "WARNING")
            return
        if self.original_template is None:
            self.log("请先设置模板", "WARNING")
            return
            
        self.is_processing = True
        self.screenshot_timer.start()
        self.log("启动自动融合流程", "SUCCESS")

    def stop_fusion(self):
        """停止融合流程"""
        self.is_processing = False
        self.screenshot_timer.stop()
        self.log("已停止融合流程", "INFO")

    def process_loop(self):
        """核心处理循环"""
        try:
            # 实时获取当前模板
            screen = ImageGrab.grab(bbox=(
                self.fixed_rect.x(),
                self.fixed_rect.y(),
                self.fixed_rect.x() + self.fixed_rect.width(),
                self.fixed_rect.y() + self.fixed_rect.height()
            ))
            current_template = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
            
            # 执行模板匹配
            result = cv2.matchTemplate(self.current_big_image, current_template, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.95:
                # 获取匹配区域参数
                tpl_h, tpl_w = current_template.shape[:2]
                match_x, match_y = max_loc
                
                # 执行透明度融合
                roi = self.current_big_image[match_y:match_y+tpl_h, match_x:match_x+tpl_w]
                blended = cv2.addWeighted(roi, 1-self.blend_alpha, current_template, self.blend_alpha, 0)
                self.current_big_image[match_y:match_y+tpl_h, match_x:match_x+tpl_w] = blended
                
                # 更新显示
                self.update_display()
                
                # 动态扩展大图（示例逻辑）
                # 如果匹配位置在边缘，自动扩展画布
                new_h = max(self.current_big_image.shape[0], match_y + tpl_h + 10)
                new_w = max(self.current_big_image.shape[1], match_x + tpl_w + 10)
                if new_h > self.current_big_image.shape[0] or new_w > self.current_big_image.shape[1]:
                    new_canvas = np.zeros((new_h, new_w, 3), dtype=np.uint8)
                    new_canvas[:self.current_big_image.shape[0], :self.current_big_image.shape[1]] = self.current_big_image
                    self.current_big_image = new_canvas
                
                self.log(
                    f"融合成功 | 相似度: {max_val:.2f} | 位置: ({match_x}, {match_y}) | "
                    f"新尺寸: {self.current_big_image.shape[1]}x{self.current_big_image.shape[0]}",
                    "SUCCESS"
                )
            else:
                self.log(f"未达到匹配阈值 | 当前最大相似度: {max_val:.2f}", "INFO")
                
        except Exception as e:
            self.stop_fusion()
            self.log(f"处理失败: {str(e)}", "ERROR")

    def update_display(self):
        """更新大图显示"""
        h, w = self.current_big_image.shape[:2]
        bytes_per_line = 3 * w
        q_img = QImage(self.current_big_image.data, w, h, bytes_per_line, QImage.Format_BGR888)
        pixmap = QPixmap.fromImage(q_img)
        self.big_image_label.setPixmap(pixmap)
        self.big_image_label.resize(pixmap.size())

    def save_result(self):
        """保存最终结果"""
        if self.current_big_image is None:
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "保存图像", "", "PNG文件 (*.png)")
        if path:
            cv2.imwrite(path, self.current_big_image)
            self.log(f"结果已保存至: {path}", "SUCCESS")

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())