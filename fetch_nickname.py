"""
抖音 / 小红书 昵称抓取工具
支持: 抖音视频页/主页、小红书笔记/用户页

用法:
  python fetch_nickname.py <URL>
  python fetch_nickname.py "https://v.douyin.com/uuYlnTMjBm0/"
  python fetch_nickname.py "https://www.xiaohongshu.com/explore/xxx"
  python fetch_nickname.py "http://xhslink.com/o/6rVhjBWdrUv"
"""

import sys
import io
import re
import asyncio
import requests

# 强制UTF-8输出（解决Windows终端乱码）
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


# ═══════════════════════════════════════════════════════════════
#  工具函数
# ═══════════════════════════════════════════════════════════════

def is_douyin(url):
    return 'douyin.com' in url.lower()

def is_xiaohongshu(url):
    return any(x in url.lower() for x in ['xiaohongshu.com', 'xhslink.com', 'xhs.cn'])


# ═══════════════════════════════════════════════════════════════
#  清洗逻辑
# ═══════════════════════════════════════════════════════════════

def clean_douyin_title(title):
    """清洗抖音主页/视频页标题"""
    if not title:
        return None
    t = title.strip()
    if ' - ' in t:
        t = t.split(' - ')[0].strip()
    for suffix in ['的抖音作品', '的抖音', '的主页']:
        if t.endswith(suffix):
            t = t[:-len(suffix)]
            break
    if t == '-':
        return ''
    return t.strip()


def clean_douyin_desc(desc):
    """从 description 提取抖音昵称 (格式: 视频标题 - 昵称于20260317发布在抖音...)"""
    if not desc:
        return None
    t = desc.strip()
    if ' - ' not in t:
        return None
    last = t.rsplit(' - ', 1)[1].strip()
    last = re.sub(r'于\d+发布在抖音.*', '', last)
    return last if last else None


def clean_xiaohongshu_title(title):
    """清洗小红书标题"""
    if not title:
        return None
    t = title.strip()
    # 小红书标题通常在 "标题 - 作者名" 或 "标题 | 作者名" 格式中
    for sep in [' - ', ' | ']:
        if sep in t:
            parts = t.split(sep)
            if len(parts) >= 2:
                # 取最后一段作为昵称（去掉"赞和收藏"等噪音词）
                candidate = parts[-1].strip()
                candidate = re.sub(r'\d+赞$', '', candidate)
                if candidate:
                    return candidate
            break
    return t.strip()


# ═══════════════════════════════════════════════════════════════
#  requests 快速抓（普通网页）
# ═══════════════════════════════════════════════════════════════

def fetch_html_requests(url, timeout=10):
    # 使用移动端UA，避免被重定向或拒绝
    headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        resp.encoding = 'utf-8' # 强制utf-8
        return resp.text, resp.url
    except Exception:
        return None, None


def extract_douyin_from_html(html):
    """从HTML提取抖音昵称"""
    if not html:
        return None
        
    # 优先从 description 中提取（视频页包含作者信息）
    m = re.search(r'<meta[^>]+(?:name|property)=["\'](?:og:)?description["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        desc = m.group(1)
        nick = clean_douyin_desc(desc)
        if nick: return nick
        
    m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+(?:name|property)=["\'](?:og:)?description["\']', html, re.I)
    if m:
        desc = m.group(1)
        nick = clean_douyin_desc(desc)
        if nick: return nick

    # 其次 og:title
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return clean_douyin_title(m.group(1))
    m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html, re.I)
    if m:
        return clean_douyin_title(m.group(1))
    # dd-title
    m = re.search(r'dd-title=["\']([^"\']+)["\']', html)
    if m:
        return clean_douyin_title(m.group(1))
    # <title>
    m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    if m:
        return clean_douyin_title(m.group(1))
    return None


def extract_xiaohongshu_from_html(html):
    """从HTML提取小红书昵称"""
    if not html:
        return None

    # og:title (格式: 标题 - 作者)
    m = re.search(r'<meta[^>]+property=["\']og:title["\'][^>]+content=["\']([^"\']+)["\']', html, re.I)
    if m:
        return clean_xiaohongshu_title(m.group(1))
    m = re.search(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:title["\']', html, re.I)
    if m:
        return clean_xiaohongshu_title(m.group(1))
    # <title>
    m = re.search(r'<title[^>]*>([^<]+)</title>', html, re.I)
    if m:
        t = clean_xiaohongshu_title(m.group(1))
        # 小红书SSR会返回"小红书"，我们需要过滤掉它
        if t and t not in ['小红书', '小红书 - 你的生活兴趣社区']:
            return t
    return None


# ═══════════════════════════════════════════════════════════════
#  Playwright 动态抓（抖音/小红书/CF验证页面）
# ═══════════════════════════════════════════════════════════════

async def fetch_douyin_with_playwright(url, timeout=25):
    """用Playwright抓取抖音昵称"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 移动端UA效果更好
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            viewport={'width': 375, 'height': 812}
        )
        page = await context.new_page()
        await page.goto(url, timeout=timeout * 1000, wait_until='domcontentloaded')
        await asyncio.sleep(4)  # 等CF验证+JS渲染

        # 1) description 标签（视频页特有，格式: 视频标题 - 昵称于日期发布在抖音...）
        selectors = [
            'meta[property="og:description"]',
            'meta[name="description"]'
        ]
        for sel in selectors:
            try:
                elem = await page.query_selector(sel)
                if elem:
                    desc = await elem.get_attribute('content') or ''
                    nickname = clean_douyin_desc(desc)
                    if nickname:
                        await browser.close()
                        return nickname
            except Exception:
                pass

        # 2) og:title 或 <title>
        title = await page.title()
        await browser.close()
        return clean_douyin_title(title)


async def fetch_xiaohongshu_with_playwright(url, timeout=25):
    """用Playwright抓取小红书昵称"""
    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # 强制使用移动端UA，避免桌面端直接重定向到login
        context = await browser.new_context(
            user_agent='Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
            viewport={'width': 375, 'height': 812}
        )
        page = await context.new_page()
        await page.goto(url, timeout=timeout * 1000, wait_until='domcontentloaded')
        await asyncio.sleep(4)  # 小红书JS渲染较慢

        content = await page.content()
        nickname = extract_xiaohongshu_from_html(content)
        if nickname:
            await browser.close()
            return nickname

        # 回退: 从页面元素获取
        try:
            name_el = await page.query_selector('[class*="author-username"]')
            if name_el:
                n = await name_el.inner_text()
                if n:
                    await browser.close()
                    return n.strip()
        except Exception:
            pass

        await browser.close()
        return None


# ═══════════════════════════════════════════════════════════════
#  主入口
# ═══════════════════════════════════════════════════════════════

def fetch_nickname(url):
    """
    根据URL特征自动判断平台，分别抓取昵称
    """
    print(f"[抓取] {url}", file=sys.stderr, flush=True)

    is_dou = is_douyin(url)
    is_xhs = is_xiaohongshu(url)

    if is_dou:
        # ── 抖音 ──
        # 1) requests快速尝试
        html, _ = fetch_html_requests(url)
        if html:
            nickname = extract_douyin_from_html(html)
            if nickname:
                return nickname, 'requests'

        # 2) Playwright
        print("[抖音] 使用Playwright...", file=sys.stderr, flush=True)
        nickname = asyncio.run(fetch_douyin_with_playwright(url))
        if nickname:
            return nickname, 'playwright'

    elif is_xhs:
        # ── 小红书 ──
        # 1) requests快速尝试
        html, _ = fetch_html_requests(url)
        if html:
            nickname = extract_xiaohongshu_from_html(html)
            if nickname:
                return nickname, 'requests'

        # 2) Playwright
        print("[小红书] 使用Playwright...", file=sys.stderr, flush=True)
        nickname = asyncio.run(fetch_xiaohongshu_with_playwright(url))
        if nickname:
            return nickname, 'playwright'

    else:
        # ── 通用网页 ──
        html, _ = fetch_html_requests(url)
        if html:
            # 尝试抖音逻辑
            nickname = extract_douyin_from_html(html)
            if nickname:
                return nickname, 'requests (douyin logic)'
            # 尝试小红书逻辑
            nickname = extract_xiaohongshu_from_html(html)
            if nickname:
                return nickname, 'requests (xhs logic)'

        # Playwright兜底
        print(f"[通用] 使用Playwright...", file=sys.stderr, flush=True)
        nickname = asyncio.run(fetch_douyin_with_playwright(url))
        if nickname:
            return nickname, 'playwright'

    return None, None


def main():
    if len(sys.argv) < 2:
        print("=" * 50)
        print("昵称抓取工具 - 支持抖音 / 小红书")
        print("用法: python fetch_nickname.py <URL>")
        print("示例: python fetch_nickname.py \"https://v.douyin.com/uuYlnTMjBm0/\"")
        print("示例: python fetch_nickname.py \"https://www.xiaohongshu.com/explore/xxx\"")
        print("=" * 50)
        url = input("请输入网址: ").strip()
        if not url:
            return
    else:
        url = sys.argv[1].strip()

    nickname, method = fetch_nickname(url)

    if nickname:
        print(f"\n✅ 昵称: {nickname}")
        print(f"方式: {method}")
    else:
        print("\n❌ 抓取失败（页面可能需要登录，或链接已失效）")
        sys.exit(1)


if __name__ == '__main__':
    main()
