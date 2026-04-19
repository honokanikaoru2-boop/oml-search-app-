import json
import re
import os
import urllib.request
from datetime import datetime, timedelta
from html.parser import HTMLParser

DATA_FILE = os.path.join(os.path.dirname(__file__), "data.json")
URL = "https://www.oml-inc.jp/information/"


class OMLParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self._in_li = False
        self._in_time = False
        self._in_a = False
        self._in_p = False
        self._current = {}
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "li":
            self._in_li = True
            self._current = {}
        elif tag == "time" and self._in_li:
            self._in_time = True
            self._current["date"] = ""
        elif tag == "a" and self._in_li and "href" in attrs:
            href = attrs["href"]
            if ".pdf" in href.lower():
                self._in_a = True
                self._current["pdf"] = href
                self._current["_link_text"] = ""
        elif tag == "p" and self._in_li:
            self._in_p = True
            self._current["summary"] = ""

    def handle_endtag(self, tag):
        if tag == "li" and self._in_li:
            self._in_li = False
            if self._current.get("pdf") and self._current.get("date"):
                self.items.append(dict(self._current))
            self._current = {}
        elif tag == "time":
            self._in_time = False
        elif tag == "a":
            self._in_a = False
        elif tag == "p":
            self._in_p = False

    def handle_data(self, data):
        if self._in_time:
            self._current["date"] = self._current.get("date", "") + data.strip()
        elif self._in_a:
            self._current["_link_text"] = self._current.get("_link_text", "") + data
        elif self._in_p:
            self._current["summary"] = self._current.get("summary", "") + data.strip()


def detect_category(title):
    if re.search(r"新規受託|受託再開", title):
        return "新規受託"
    if re.search(r"受託中止|一時中止", title):
        return "受託中止"
    if re.search(r"内容変更|測定方法|試薬", title):
        return "内容変更"
    if re.search(r"実施料|診療報酬", title):
        return "実施料"
    if re.search(r"容器変更|採血容器", title):
        return "容器変更"
    if re.search(r"業務日程|受託日程|年末年始|祝日|休日|日程", title):
        return "受託日程"
    return "その他"


def parse_link_text(text):
    text = text.strip()
    m = re.match(r"\[?(No\.[^\]）］\s]+)[）\]］]\s*(.*)", text)
    if m:
        return m.group(1), m.group(2).strip()
    return "—", text


def scrape():
    req = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        html = resp.read().decode("utf-8", errors="replace")

    parser = OMLParser()
    parser.feed(html)

    with open(DATA_FILE, encoding="utf-8") as f:
        existing = json.load(f)

    existing_pdfs = {item["pdf"] for item in existing}

    new_items = []
    for item in parser.items:
        if item["pdf"] in existing_pdfs:
            continue
        no, title = parse_link_text(item.get("_link_text", ""))
        entry = {
            "date": item["date"],
            "no": no,
            "title": title,
            "category": detect_category(title),
            "summary": item.get("summary", ""),
            "keywords": "",
            "pdf": item["pdf"],
        }
        new_items.append(entry)

    # 新規追加
    merged = new_items + existing

    # 日付順ソート（新しい順）
    def date_key(item):
        try:
            return datetime.strptime(item["date"], "%Y.%m.%d")
        except Exception:
            return datetime.min
    merged.sort(key=date_key, reverse=True)

    # 5年以上前のデータを除外
    cutoff = datetime.now() - timedelta(days=365 * 5)
    before = len(merged)
    merged = [i for i in merged if date_key(i) >= cutoff or date_key(i) == datetime.min]
    removed = before - len(merged)

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(merged, f, ensure_ascii=False, indent=2)

    if new_items:
        print(f"{len(new_items)} 件追加しました: {[i['no'] for i in new_items]}")
    else:
        print("新しい情報はありません。")
    if removed:
        print(f"{removed} 件の古いデータを削除しました（5年超）。")
    print(f"合計 {len(merged)} 件保持中。")


if __name__ == "__main__":
    scrape()
