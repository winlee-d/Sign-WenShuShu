import logging
import os
import re
import time
import traceback
import sys
import requests
from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager


def send(push_token, title, text):
    # http://www.pushplus.plus/send?token=XXXXX&title=XXX&content=XXX&template=html
    requests.get(f"https://www.pushplus.plus/send?token={push_token}&title={title}&content={text}&template=html")


def hide_user(user):
    user = str(user)
    if re.match(r'\d{11}', user):  # 匹配11位纯数字
        return user[:3] + '****' + user[7:]
    elif re.match(r'\S+@\S+\.\S+', user):  # 匹配邮箱格式
        at_index = user.find('@')
        return user[:2] + '*' * (at_index - 2) + user[at_index:]
    else:
        return user


def sign_wss(user, password, token, msgs : list, show_user_string : str):
    chrome_options = Options()
    chrome_options.add_argument('disable-infobars')  # 取消显示信息栏（Chrome 正在受到自动软件的控制）
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")  # 禁用 Chrome 的自动化控制检测
    chrome_options.binary_location = "C:\Program Files\Google\Chrome\Application\chrome.exe"

    # 浏览器不提供可视化页面. linux下如果系统不支持可视化不加这条会启动失败
    if not debug_flag:
        chrome_options.add_argument('--headless')
    # 以最高权限运行
    chrome_options.add_argument('--no-sandbox')
    chrome_options.add_argument('--disable-dev-shm-usage')
    b = webdriver.Chrome(options=chrome_options)

    b.get('https://www.wenshushu.cn/signin')
    time.sleep(2)
    b.refresh()
    b.implicitly_wait(10)
    print("正在登陆...")
    b.find_element(by=By.XPATH, value='//*[contains(text(),"密码登录")]').click()
    time.sleep(1)
    b.find_element(by=By.XPATH, value='//*[@placeholder="手机号 / 邮箱"]').send_keys(user)
    time.sleep(1)
    b.find_element(by=By.XPATH, value='//*[@placeholder="密码"]').send_keys(password)
    time.sleep(1)
    b.find_element(by=By.XPATH, value='//*[@type="submit"]').click()
    time.sleep(1)

    b.implicitly_wait(10)
    b.refresh()
    time.sleep(1)

    try:
        print("关闭广告和新手任务中...")
        if b.find_element(by=By.CLASS_NAME, value="btn_close"):
            b.find_element(by=By.CLASS_NAME, value="btn_close").click()
        time.sleep(1)
    except NoSuchElementException:
        pass

    b.implicitly_wait(10)
    print("{user} 正在打卡...".format(user=show_user_string))
    b.find_element(by=By.CLASS_NAME, value="icondaka").click()
    time.sleep(1)

    b.implicitly_wait(10)
    time.sleep(2)
    
    # 获取页面源码
    html = b.page_source

    if ('今日已打卡' in html or '打卡成功' in html):
        html = html.replace('\n', '')
        names = re.compile('class="m-title5">(.*?)</div>').findall(html)
        values = re.compile('class="re-num m-text9">(.*?)</div>').findall(html)
        result = ''
        for i in range(len(names)):
            if (names[i] == '手气不好'):
                continue
            result += names[i] + '：' + values[i] + '</br>'
            print('%s:%s' % (names[i], values[i].strip()))
        msg = (show_user_string + '文叔叔签到成功,', result)
    else:
        msg = (show_user_string + '文叔叔签到失败,', html)
        print(html)
    msgs.append(msg)

    b.close()

if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='UTF-8')

    users = os.environ.get('USER')
    password = os.environ.get('PASSWORD')
    push_token = os.environ.get('PUSH_MESSAGE')
    show_user = os.environ.get('SHOW_USER')  # 0: 完全不显示（默认），1：显示部分（例如：131****1234），2：完全显示
    debug_flag = os.environ.get('DEBUG')
    if show_user is None:
        show_user = 0

    if users is None:
        exit()
    if password is None:
        exit()
    if push_token is None:
        push_token = ""
    msgs = []
    if debug_flag is None:
        debug_flag = False
    else:
        debug_flag = True

    for user in users.split(';'):
        show_user_string = ''
        if str(show_user) == '1':
            show_user_string = hide_user(user)
        elif str(show_user) == '2':
            show_user_string = user
        retry = 0
        while retry < 5:
            success = True
            try:
                sign_wss(user, password, push_token, msgs, show_user_string)
            except Exception as e:
                print("签到{user}账户时出现异常：{error_message}".format(user=show_user_string, error_message=traceback.format_exc()))
                print("已重试次数： " + str(retry + 1))
                success = False
            finally:
                retry = retry + 1
            if success:
                break

    push_text = ''
    for msg in msgs:
        push_text = push_text + msg[0] + msg[1]

    send(push_token, '文叔叔签到结果', push_text)
