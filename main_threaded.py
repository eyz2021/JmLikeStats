###最终版本

import matplotlib.pyplot as plt
from jmcomic import *
from tqdm import tqdm
import threading
from queue import Queue

# 1. 配置JM客户端并登录
#disable_jm_log()
#option = JmOption.default()
option = create_option_by_file('option.yml')
client = option.new_jm_client()
username = '你的用户名'
client.login(username, '你的密码')

# 2. 获取所有收藏的本子ID
favos = []
print("正在获取收藏的本子ID...")
for page in client.favorite_folder_gen():
    for aid, _ in page.iter_id_title():
        favos.append(aid)
    for folder_id, folder_name in page.iter_folder_id_name():
        print(f'收藏夹id: {folder_id}, 收藏夹名称: {folder_name}')

total_albums = len(favos)
print(f"共获取到 {total_albums} 个本子ID")

# 3. 多线程获取标签
tags_dict = {}
tags_lock = threading.Lock()  # 用于保护共享字典的线程锁

def tag_worker(queue, pbar):
    """线程工作函数：处理队列中的本子ID，获取标签并统计"""
    # 每个线程创建独立的客户端避免冲突
    thread_client = option.new_jm_client()
    while not queue.empty():
        aid = queue.get()
        try:
            # 获取本子详情
            page = thread_client.search_site(search_query=aid)
            album: JmAlbumDetail = page.single_album
            
            # 线程安全地更新标签字典
            with tags_lock:
                for tag in album.tags:
                    if tag in tags_dict:
                        tags_dict[tag] += 1
                    else:
                        tags_dict[tag] = 1
            pbar.update(1)  # 更新进度条
        finally:
            queue.task_done()  # 标记任务完成

# 初始化任务队列
tag_queue = Queue()
for aid in favos:
    tag_queue.put(aid)

# 启动多线程获取标签
print("\n多线程获取本子标签中...")
with tqdm(total=total_albums, desc="获取标签进度") as pbar:
    # 根据任务量设置线程数（最多8个线程）
    thread_count = min(8, tag_queue.qsize())
    threads = []
    
    for _ in range(thread_count):
        t = threading.Thread(target=tag_worker, args=(tag_queue, pbar))
        t.daemon = True  # 守护线程：主程序退出时自动结束
        t.start()
        threads.append(t)
    
    # 等待所有标签获取完成
    tag_queue.join()

# 4. 柱状图生成核心函数
def generate_bar_chart(data_dict, top_n=20, chart_title="数据统计柱状图", 
                       x_label="数量", y_label="类别", fig_size=(12, 8)):
    """生成水平柱状图可视化字典键值对"""
    # 解决中文字体显示问题
    plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]
    plt.rcParams["axes.unicode_minus"] = False
    
    if not data_dict:
        print("警告：字典为空，请先填充数据！")
        return
    
    # 排序并截取前top_n个
    sorted_data = sorted(data_dict.items(), key=lambda x: x[1], reverse=True)[:top_n]
    categories, values = zip(*sorted_data)
    
    # 创建柱状图
    plt.figure(figsize=fig_size)
    bars = plt.barh(categories, values, color="#87CEEB", edgecolor="#4682B4", alpha=0.8)
    
    # 添加数值标签
    for bar in bars:
        bar_width = bar.get_width()
        plt.text(bar_width + max(values)*0.01,
                 bar.get_y() + bar.get_height()/2,
                 str(int(bar_width)),
                 va="center", ha="left", fontsize=10)
    
    # 设置轴标签和标题
    plt.xlabel(x_label, fontsize=12, fontweight="bold")
    plt.ylabel(y_label, fontsize=12, fontweight="bold")
    plt.title(chart_title, fontsize=14, fontweight="bold", pad=20)
    
    # 调整布局
    plt.gca().invert_yaxis()
    plt.tight_layout()
    plt.show()

# 5. 调用函数生成图表
generate_bar_chart(
    tags_dict, 
    chart_title=f"{username}的jmcomic本子标签统计 (共{total_albums}本)"
)