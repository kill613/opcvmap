import sys
import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QPushButton,
                            QFileDialog, QVBoxLayout, QHBoxLayout, QWidget,
                            QMessageBox, QScrollArea, QSplitter, QTextEdit, QComboBox)
from PyQt5.QtCore import Qt, QTimer, QRect
from PyQt5.QtGui import QImage, QPixmap
from PIL import ImageGrab

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.fixed_rect = QRect(611, 700, 140, 94)
        self.current_big_image = None
        self.current_template = None
        self.merge_mode = "覆盖模式"
        self.log_counter = 0
        
        # 初始化界面
        self.init_ui()
        self.setup_timer()

    def init_ui(self):
        self.setWindowTitle("智能图像拼接系统")
        self.setGeometry(100, 100, 1200, 800)
        self.create_widgets()
        self.setup_layout()  # 确保调用布局方法
        self.connect_signals()

    def create_widgets(self):
        """控件创建"""
        self.btn_init_big = QPushButton("初始化基准图")
        self.btn_start = QPushButton("开始拼接")
        self.btn_stop = QPushButton("停止")
        self.btn_save = QPushButton("保存结果")
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["覆盖模式", "保留模式"])

        self.big_image_label = QLabel()
        self.big_image_label.setAlignment(Qt.AlignCenter)
        self.big_scroll = QScrollArea()
        self.big_scroll.setWidget(self.big_image_label)
        
        self.small_image_label = QLabel()
        self.small_image_label.setAlignment(Qt.AlignCenter)
        self.small_image_label.setFixedSize(200, 150)
        self.small_image_label.setStyleSheet("border: 2px solid #666;")

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMinimumHeight(200)
        self.setup_log_style()

    def setup_layout(self):
        """布局设置（新增关键方法）"""
        # 主布局
        main_splitter = QSplitter(Qt.Horizontal)
        
        # 左侧布局
        left_widget = QWidget()
        left_layout = QVBoxLayout()
        left_layout.addWidget(self.big_scroll)
        left_widget.setLayout(left_layout)
        
        # 右侧布局
        right_splitter = QSplitter(Qt.Vertical)
        right_splitter.addWidget(self.small_image_label)
        right_splitter.addWidget(self.log_text)

        main_splitter.addWidget(left_widget)
        main_splitter.addWidget(right_splitter)

        # 控制栏布局
        control_layout = QHBoxLayout()
        control_layout.addWidget(self.btn_init_big)
        control_layout.addWidget(self.mode_combo)
        control_layout.addWidget(self.btn_start)
        control_layout.addWidget(self.btn_stop)
        control_layout.addWidget(self.btn_save)

        # 主容器布局
        main_layout = QVBoxLayout()
        main_layout.addLayout(control_layout)
        main_layout.addWidget(main_splitter)

        container = QWidget()
        container.setLayout(main_layout)
        self.setCentralWidget(container)

    def setup_timer(self):
        """定时器配置"""
        self.screenshot_timer = QTimer()
        self.screenshot_timer.setInterval(100)
        self.screenshot_timer.timeout.connect(self.capture_template)

    def setup_log_style(self):
        """日志样式"""
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                font-family: Consolas;
                font-size: 10pt;
            }
        """)

    # 其他方法保持不变（connect_signals, capture_template等）

    def connect_signals(self):
        """信号连接"""
        self.btn_init_big.clicked.connect(self.capture_initial_big_image)
        self.btn_start.clicked.connect(self.start_process)
        self.btn_stop.clicked.connect(self.stop_process)
        self.btn_save.clicked.connect(self.save_result)
        self.mode_combo.currentTextChanged.connect(self.update_merge_mode)

    def update_merge_mode(self, mode):
        """更新合并模式"""
        self.merge_mode = mode
        self.add_log(f"切换合并模式: {mode}", "INFO")

    def add_log(self, message, status="INFO"):
        """日志记录"""
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.log_counter += 1
        
        color_map = {
            "SUCCESS": "#4CAF50",
            "WARNING": "#FFC107",
            "ERROR": "#F44336",
            "INFO": "#2196F3"
        }
        color = color_map.get(status, "#2196F3")
        
        log_entry = f"""
        <div style='margin: 2px 0;'>
            <span style='color: #757575;'>[{self.log_counter}] {timestamp}</span>
            <span style='color: {color};'>[{status}]</span>
            {message}
        </div>
        """
        self.log_text.append(log_entry)
        self.log_text.verticalScrollBar().setValue(
            self.log_text.verticalScrollBar().maximum()
        )

    def capture_initial_big_image(self):
        """初始化基准图"""
        try:
            screen = ImageGrab.grab(bbox=(
                self.fixed_rect.x(),
                self.fixed_rect.y(),
                self.fixed_rect.x() + self.fixed_rect.width(),
                self.fixed_rect.y() + self.fixed_rect.height()
            ))
            self.current_big_image = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
            self.update_big_display()
            self.add_log("基准图初始化成功", "SUCCESS")
        except Exception as e:
            self.add_log(f"初始化失败: {str(e)}", "ERROR")
            QMessageBox.critical(self, "错误", f"初始化失败:\n{str(e)}")

    def capture_template(self):
        """模板捕获与处理"""
        try:
            screen = ImageGrab.grab(bbox=(
                self.fixed_rect.x(),
                self.fixed_rect.y(),
                self.fixed_rect.x() + self.fixed_rect.width(),
                self.fixed_rect.y() + self.fixed_rect.height()
            ))
            self.current_template = cv2.cvtColor(np.array(screen), cv2.COLOR_RGB2BGR)
            self.update_small_display()
            
            if self.current_big_image is None:
                return

            result = cv2.matchTemplate(self.current_big_image, self.current_template, cv2.TM_CCOEFF_NORMED)
            _, max_val, _, max_loc = cv2.minMaxLoc(result)
            
            if max_val > 0.65:
                # 动态扩展画布（修复坐标计算）
                new_width = max(self.current_big_image.shape[1], max_loc[0] + w)
                new_height = max(self.current_big_image.shape[0], max_loc[1] + h)
                
                # 创建新画布时保持数据类型一致
                if new_width > self.current_big_image.shape[1] or new_height > self.current_big_image.shape[0]:
                    expanded = np.zeros((new_height, new_width, 3), dtype=np.uint8)
                    expanded[:self.current_big_image.shape[0], :self.current_big_image.shape[1]] = self.current_big_image
                    self.current_big_image = expanded  # 这里必须重新赋值整个数组

                # 使用正确的切片范围
                y_start = max_loc[1]
                y_end = y_start + h
                x_start = max_loc[0]
                x_end = x_start + w
                
                # 执行像素级合并
                if self.merge_mode == "覆盖模式":
                    self.current_big_image[y_start:y_end, x_start:x_end] = self.current_template
                else:
                    # 使用位运算加速mask计算
                    roi = self.current_big_image[y_start:y_end, x_start:x_end]
                    mask = cv2.inRange(roi, (0,0,0), (0,0,0)) | cv2.inRange(roi, (255,255,255), (255,255,255))
                    self.current_big_image[y_start:y_end, x_start:x_end] = cv2.bitwise_or(
                        cv2.bitwise_and(self.current_template, self.current_template, mask=mask),
                        cv2.bitwise_and(roi, roi, mask=~mask)
                    )

                # 强制更新显示
                self.update_big_display()
                cv2.imwrite("debug.png", self.current_big_image)  # 调试用

    def update_big_display(self):
        if self.current_big_image is not None:
            # 确保数组是连续内存
            current_big_image = np.ascontiguousarray(self.current_big_image)
            h, w, ch = current_big_image.shape
            bytes_per_line = ch * w
            q_img = QImage(current_big_image.data, w, h, bytes_per_line, QImage.Format_BGR888)
            pixmap = QPixmap.fromImage(q_img)
            self.big_image_label.setPixmap(pixmap)
            self.big_image_label.resize(pixmap.size())
            # 强制刷新
            self.big_image_label.repaint()

    def update_small_display(self):
        """更新模板显示"""
        if self.current_template is not None:
            h, w = self.current_template.shape[:2]
            bytes_per_line = 3 * w
            q_img = QImage(self.current_template.data, w, h, bytes_per_line, QImage.Format_BGR888)
            pixmap = QPixmap.fromImage(q_img).scaled(
                self.small_image_label.size(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            self.small_image_label.setPixmap(pixmap)

    def start_process(self):
        """启动处理"""
        if self.current_big_image is None:
            QMessageBox.warning(self, "提示", "请先初始化基准图")
            return
        self.screenshot_timer.start()
        self.add_log("启动自动处理流程", "SUCCESS")

    def stop_process(self):
        """停止处理"""
        self.screenshot_timer.stop()
        self.add_log("已停止自动处理", "INFO")

    def save_result(self):
        """保存结果"""
        if self.current_big_image is None:
            return
        path, _ = QFileDialog.getSaveFileName(self, "保存结果", "", "PNG文件 (*.png)")
        if path:
            cv2.imwrite(path, self.current_big_image)
            self.add_log(f"已保存结果到: {path}", "SUCCESS")

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
