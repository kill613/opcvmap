import cv2
import numpy as np
import pyautogui
import time

# 配置参数
X, Y, W, H = 584, 625, 140, 100         # 截图区域
MAP_WIN_POS = (1800, 800)               # 拼接图显示位置
CROP_X, CROP_Y, CROP_W, CROP_H = 10, 10, 88, 46  # 裁剪区域
BIG_IMAGE_SIZE = 512                    # 拼接画布尺寸
MATCH_THRESHOLD = 0.8                   # 匹配置信度阈值

def capture_screenshot():
    """安全截图：返回独立副本的BGR图像"""
    screenshot = pyautogui.screenshot(region=(X, Y, W, H))
    # 显式深拷贝（避免numpy数组共享缓冲区）
    return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR).copy() 

def deep_merge(base_img, new_img, offset_x, offset_y):
    """
    防变形合并（所有操作基于深拷贝）
    - base_img: 基础画布（深拷贝副本）
    - new_img: 新图像（深拷贝副本）
    - 返回: 合并后的新图像副本
    """
    # 创建基础画布的独立副本
    merged = base_img.copy()
    
    h, w = new_img.shape[:2]
    x_start = max(0, offset_x)
    y_start = max(0, offset_y)
    x_end = min(merged.shape[1], offset_x + w)
    y_end = min(merged.shape[0], offset_y + h)
    
    # 计算有效区域
    valid_w = x_end - x_start
    valid_h = y_end - y_start
    if valid_w <=0 or valid_h <=0: 
        return merged
    
    # 深拷贝目标区域和新图像区域
    target_region = merged[y_start:y_end, x_start:x_end].copy()
    src_x = max(-offset_x, 0)
    src_y = max(-offset_y, 0)
    new_region = new_img[src_y:src_y+valid_h, src_x:src_x+valid_w].copy()
    
    # 仅合并空白区域（避免覆盖已有内容）
    mask = np.all(target_region == 255, axis=2)
    target_region[mask] = new_region[mask]
    
    # 将修改后的区域写回副本
    merged[y_start:y_end, x_start:x_end] = target_region
    return merged

def main():
    cv2.namedWindow('big_image', cv2.WINDOW_AUTOSIZE)
    cv2.moveWindow('big_image', *MAP_WIN_POS)

    # 初始化画布（深拷贝保障数据隔离）
    prev_image = np.full((BIG_IMAGE_SIZE, BIG_IMAGE_SIZE, 3), 255, dtype=np.uint8)
    prev_image = prev_image.copy()  # 确保初始画布独立
    
    # 初始化第一帧（深拷贝操作）
    index_template = capture_screenshot()
    h, w = index_template.shape[:2]
    x_center = (BIG_IMAGE_SIZE - w) // 2
    y_center = (BIG_IMAGE_SIZE - h) // 2
    prev_image[y_center:y_center+h, x_center:x_center+w] = index_template.copy()

    while True:
        start_time = time.time()
        # 捕获新帧（自动深拷贝）
        new_img = capture_screenshot()
        
        # 提取模板（深拷贝+防篡改）
        template = new_img[CROP_Y:CROP_Y+CROP_H, CROP_X:CROP_X+CROP_W].copy()
        marked_img = new_img.copy()  # 标注用副本
        cv2.circle(marked_img, (CROP_X + CROP_W//2, CROP_Y + CROP_H//2), 2, (0,255,0), -1)

        # 模板匹配
        result = cv2.matchTemplate(prev_image, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        print(f"Confidence: {max_val:.2f}")

        if max_val < MATCH_THRESHOLD:
            print("[Skip] Low match confidence")
            continue

        # 计算偏移量（基于深拷贝数据）
        match_center_x = max_loc[0] + CROP_W // 2
        match_center_y = max_loc[1] + CROP_H // 2
        new_center_x = CROP_X + CROP_W // 2
        new_center_y = CROP_Y + CROP_H // 2
        offset_x = match_center_x - new_center_x
        offset_y = match_center_y - new_center_y

        # 安全合并（生成全新画布）
        prev_image = deep_merge(prev_image, new_img, offset_x, offset_y)

        # 显示结果（始终操作副本）
        cv2.imshow('big_image', prev_image.copy())
        cv2.imshow('new_frame', marked_img)

        # 动态延迟
        elapsed = time.time() - start_time
        delay = max(1, int((0.3 - elapsed) * 1000))
        if cv2.waitKey(delay) & 0xFF == 27:
            break

    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()