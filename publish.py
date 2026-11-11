# publish.py — 폴더 안의 사진(1~10장) 또는 영상 1개(릴스)와 caption.txt를 인스타에 올립니다
import os, sys, glob, time, urllib.parse, requests

USER = os.environ["IG_USER_ID"].strip()
TOKEN = os.environ["IG_ACCESS_TOKEN"].strip()
# EAA로 시작하는 토큰(통합 로그인·Facebook 로그인)은 graph.facebook.com,
# IGAA로 시작하는 토큰(Instagram 로그인)은 graph.instagram.com 으로 보내요
API = "https://graph.facebook.com/v21.0" if TOKEN.startswith("EAA") else "https://graph.instagram.com/v21.0"
BASE = os.environ["IMG_BASE"].rstrip("/")
folder = sys.argv[1].strip("/")


def call(path, **data):
    data["access_token"] = TOKEN
    r = requests.post(f"{API}/{path}", data=data, timeout=60).json()
    if "error" in r:
        e = r["error"]
        sys.exit(f"오류(#{e.get('code')}): {e.get('message')}")
    return r["id"]


def url_of(p):
    return BASE + "/" + urllib.parse.quote(p.replace("\\", "/"))


def wait_ready(box, tries, gap):
    """인스타가 사진·영상을 다 받아 갈 때까지 기다립니다"""
    for _ in range(tries):
        state = requests.get(f"{API}/{box}", params={"fields": "status_code,status", "access_token": TOKEN},
                             timeout=30).json()
        code = state.get("status_code")
        if code == "FINISHED":
            return
        if code == "ERROR":
            sys.exit(f"오류(영상/사진 처리 실패): {state.get('status', '')}")
        time.sleep(gap)
    if tries < 60:
        return  # 사진은 예전처럼 그냥 게시를 시도해요
    sys.exit("오류: 인스타가 파일을 처리하는 데 너무 오래 걸려요. 잠시 뒤 다시 실행하세요")


if os.path.exists(f"{folder}/posted.txt"):
    sys.exit(f"{folder}는 이미 올린 폴더예요. 다시 올리려면 posted.txt를 지우세요")

cap_file = f"{folder}/caption.txt"
caption = open(cap_file, encoding="utf-8").read() if os.path.exists(cap_file) else ""
videos = sorted(p for p in glob.glob(f"{folder}/*") if p.lower().endswith((".mp4", ".mov")))
photos = sorted(p for p in glob.glob(f"{folder}/*") if p.lower().endswith((".jpg", ".jpeg")))[:10]

if videos:
    # 릴스: 영상 1개. 피드에도 같이 보여요
    extra = {"cover_url": url_of(f"{folder}/cover.jpg")} if os.path.exists(f"{folder}/cover.jpg") else {}
    box = call(f"{USER}/media", media_type="REELS", video_url=url_of(videos[0]),
               caption=caption, share_to_feed="true", **extra)
    wait_ready(box, 60, 10)  # 영상은 처리에 시간이 걸려요 (최대 10분)
else:
    if not photos:
        sys.exit(f"{folder} 폴더에 JPG 사진이나 MP4 영상이 없어요")
    urls = [url_of(p) for p in photos]
    if len(urls) == 1:
        box = call(f"{USER}/media", image_url=urls[0], caption=caption)
    else:
        kids = [call(f"{USER}/media", image_url=u, is_carousel_item="true") for u in urls]
        box = call(f"{USER}/media", media_type="CAROUSEL", children=",".join(kids), caption=caption)
    wait_ready(box, 20, 3)

post_id = call(f"{USER}/media_publish", creation_id=box)
open(f"{folder}/posted.txt", "w").write(post_id)  # 두 번 올라가지 않게 표시
print("게시 완료! 게시물 번호:", post_id)
