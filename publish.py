# publish.py — 폴더 안의 사진(1~10장)과 caption.txt를 인스타에 올립니다
import os, sys, glob, time, urllib.parse, requests

API = "https://graph.instagram.com/v21.0"
USER = os.environ["IG_USER_ID"]
TOKEN = os.environ["IG_ACCESS_TOKEN"]
BASE = os.environ["IMG_BASE"].rstrip("/")
folder = sys.argv[1].strip("/")


def call(path, **data):
    data["access_token"] = TOKEN
    r = requests.post(f"{API}/{path}", data=data, timeout=60).json()
    if "error" in r:
        e = r["error"]
        sys.exit(f"오류(#{e.get('code')}): {e.get('message')}")
    return r["id"]


if os.path.exists(f"{folder}/posted.txt"):
    sys.exit(f"{folder}는 이미 올린 폴더예요. 다시 올리려면 posted.txt를 지우세요")

photos = sorted(p for p in glob.glob(f"{folder}/*") if p.lower().endswith((".jpg", ".jpeg")))[:10]
if not photos:
    sys.exit(f"{folder} 폴더에 JPG 사진이 없어요")
cap_file = f"{folder}/caption.txt"
caption = open(cap_file, encoding="utf-8").read() if os.path.exists(cap_file) else ""
urls = [BASE + "/" + urllib.parse.quote(p.replace("\\", "/")) for p in photos]

if len(urls) == 1:
    box = call(f"{USER}/media", image_url=urls[0], caption=caption)
else:
    kids = [call(f"{USER}/media", image_url=u, is_carousel_item="true") for u in urls]
    box = call(f"{USER}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)

# 인스타가 사진을 다 받아 갈 때까지 기다립니다
for _ in range(20):
    state = requests.get(f"{API}/{box}", params={"fields": "status_code", "access_token": TOKEN}, timeout=30).json()
    if state.get("status_code") in ("FINISHED", "ERROR"):
        break
    time.sleep(3)

post_id = call(f"{USER}/media_publish", creation_id=box)
open(f"{folder}/posted.txt", "w").write(post_id)  # 두 번 올라가지 않게 표시
print("게시 완료! 게시물 번호:", post_id)
