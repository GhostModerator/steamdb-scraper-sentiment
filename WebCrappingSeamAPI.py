import requests
import pandas as pd
import time
from datetime import datetime
import os
import calendar
import json
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 配置参数
API_KEY = 'xxxxxxx' # steamdb API key
APP_ID = '730'  # cs2 ID
START_DATE = '2024-11-01'
END_DATE = '2024-12-11'  # 目标日期范围
OUTPUT_CSV = r'D:\Neko\steam\cs2_reviews.csv'
REVIEWS_PER_PAGE = 1000  # 每页抓取的评论数量（已增加）
MAX_PAGES = 100  # 调整后的最大抓取页数
MAX_COMMENTS_PER_DAY = 100  # 每天最多处理的评论数量
STATE_FILE = 'state.json'  # 状态保存文件

# 将日期转换为Unix时间戳（UTC）
def date_to_timestamp(date_str):
    try:
        dt = datetime.strptime(date_str, '%Y-%m-%d')
        return calendar.timegm(dt.timetuple())
    except ValueError as e:
        print(f"日期格式错误: {e}")
        exit(1)

start_timestamp = date_to_timestamp(START_DATE)
end_timestamp = date_to_timestamp(END_DATE)

print(f"Start Date: {START_DATE} => Timestamp: {start_timestamp}")
print(f"End Date: {END_DATE} => Timestamp: {end_timestamp}")

# 初始化数据结构
daily_data = {}
daily_count = {}  # 记录每天已处理的评论数量

# 读取状态
def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            state = json.load(f)
            return state.get('cursor', '*'), state.get('daily_count', {}), state.get('current_page', 0)
    return '*', {}, 0

cursor, daily_count, current_page = load_state()

# 保存状态
def save_state(cursor, daily_count, current_page):
    state = {
        'cursor': cursor,
        'daily_count': daily_count,
        'current_page': current_page
    }
    with open(STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f)

# 创建一个会重试的会话
session = requests.Session()
retry = Retry(
    total=5,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["HEAD", "GET", "OPTIONS"]
)
adapter = HTTPAdapter(max_retries=retry)
session.mount("https://", adapter)
session.mount("http://", adapter)

# 设置请求参数
params = {
    'json': 1,
    'key': API_KEY,
    'language': 'all',
    'filter': 'all',
    'num_per_page': REVIEWS_PER_PAGE,
    'cursor': cursor,
    'review_type': 'all',
    'purchase_type': 'all'
}

# 确保输出目录存在
output_dir = os.path.dirname(OUTPUT_CSV)
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

print("开始抓取评论数据...")

total_reviews_processed = 0  # 初始化总评论计数
all_days_reached_limit = False  # 标记是否所有天数都已达到评论限制

# 初始化 tqdm 进度条
pbar = tqdm(total=MAX_PAGES, desc="抓取评论页数", unit="页", initial=current_page)

while True:
    if current_page >= MAX_PAGES:
        print(f"已达到最大页数限制（{MAX_PAGES}页），停止抓取。")
        break

    params['cursor'] = cursor
    try:
        response = session.get(f'https://store.steampowered.com/appreviews/{APP_ID}', params=params, timeout=10)
    except requests.exceptions.RequestException as e:
        print(f"请求时发生异常：{e}")
        break

    if response.status_code != 200:
        print(f"请求失败，状态码：{response.status_code}")
        break

    try:
        data = response.json()
    except ValueError:
        print("无法解析JSON响应。")
        break

    reviews = data.get('reviews', [])
    print(f"第 {current_page + 1} 页：抓取到 {len(reviews)} 条评论。")

    if not reviews:
        print("没有更多评论可抓取。")
        break

    # 打印每页的日期范围
    page_dates = [datetime.utcfromtimestamp(review.get('timestamp_created', 0)).strftime('%Y-%m-%d') for review in reviews]
    print(f"第 {current_page + 1} 页日期范围: {min(page_dates)} 到 {max(page_dates)}")

    for i, review in enumerate(reviews):
        review_timestamp = review.get('timestamp_created', 0)

        # 调试信息：打印部分评论的时间戳和日期
        if total_reviews_processed < 10:
            review_date_debug = datetime.utcfromtimestamp(review_timestamp).strftime('%Y-%m-%d')
            print(f"|| {total_reviews_processed + 1}: {review_date_debug}", end='|| ')
        
        # 检查评论是否在指定的日期范围内
        if review_timestamp < start_timestamp:
            print("\n已达到起始日期，停止抓取。")
            all_days_reached_limit = True
            break
        if review_timestamp > end_timestamp:
            continue  # 评论在结束日期之后，跳过

        review_date = datetime.utcfromtimestamp(review_timestamp).strftime('%Y-%m-%d')

        # 初始化当天的数据结构和计数器
        if review_date not in daily_data:
            daily_data[review_date] = {'likes': 0, 'dislikes': 0}
            daily_count[review_date] = 0

        # 检查当天是否已经达到评论处理的上限
        if daily_count[review_date] >= MAX_COMMENTS_PER_DAY:
            continue  # 跳过该评论，不再处理

        # 处理评论
        voted_up = review.get('voted_up', False)
        if voted_up:
            daily_data[review_date]['likes'] += 1
        else:
            daily_data[review_date]['dislikes'] += 1

        # 更新计数器
        daily_count[review_date] += 1
        total_reviews_processed += 1

        # 每处理100条评论，输出一次进度
        if total_reviews_processed % 100 == 0:
            print(f"\n已处理 {total_reviews_processed} 条评论...")

    if all_days_reached_limit:
        break

    # 检查是否需要停止
    last_review_timestamp = reviews[-1].get('timestamp_created', 0)
    print(f"\n第 {current_page + 1} 页最后一条评论的时间戳: {last_review_timestamp} ({datetime.utcfromtimestamp(last_review_timestamp).strftime('%Y-%m-%d')})")

    if last_review_timestamp < start_timestamp:
        print("已达到起始日期，停止抓取。")
        break

    # 获取下一页的游标
    cursor = data.get('cursor', '')
    if not cursor or cursor == '*':
        print("没有更多的游标，停止抓取。")
        break

    print(f"获取下一页的游标: {cursor}")
    current_page += 1
    pbar.update(1)

    # 为避免触发速率限制，暂停一段时间
    time.sleep(0.1)  # 已减少暂停时间

    # 检查是否所有天数都已达到评论处理的上限
    # 仅在 daily_data 不为空时进行检查
    if daily_data:
        all_days_reached_limit = True
        for date in daily_data:
            if daily_count[date] < MAX_COMMENTS_PER_DAY:
                all_days_reached_limit = False
                break
    else:
        all_days_reached_limit = False

    if all_days_reached_limit:
        print("所有指定日期的评论已达到上限，停止抓取。")
        break

    # 保存当前状态

pbar.close()

# 处理和计算 sentiment_score
print("\n处理数据并计算 sentiment_score...")
records = []
for date, counts in daily_data.items():
    likes = counts['likes']
    dislikes = counts['dislikes']
    sentiment_score = likes / (likes + dislikes) if (likes + dislikes) != 0 else 'Infinity'
    records.append({
        '日期': date,
        '点赞': likes,
        '踩': dislikes,
        'sentiment_score': sentiment_score
    })

# 打印 daily_data 和 records 以进行调试
print("daily_data:", daily_data)
print("records:", records)

if not records:
    print("没有任何记录被处理。请检查抓取逻辑。")
else:
    # 创建 DataFrame 并排序
    df = pd.DataFrame(records)
    print("DataFrame 列名:", df.columns.tolist())
    print("DataFrame 内容:\n", df.head())

    try:
        df.sort_values('日期', inplace=True)
    except KeyError as e:
        print(f"排序时发生错误：{e}")
        print("DataFrame 的列名为:", df.columns.tolist())
        exit(1)

    # 输出到 CSV
    print(f"将数据写入CSV文件：{OUTPUT_CSV}")
    df.to_csv(OUTPUT_CSV, index=False, encoding='utf-8-sig')

    print(f"完成！总共处理了 {total_reviews_processed} 条评论。")

