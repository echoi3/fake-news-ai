"""페이크 뉴스 30초: 스틸 → Veo 3.1 lite image-to-video (OpenRouter) → 뉴스 그래픽·자막·리빌 카드 → out/fake_news_30s.mp4"""
import json, os, pathlib, subprocess, sys, time, urllib.request, concurrent.futures as cf
sys.stdout.reconfigure(line_buffering=True)
ROOT = pathlib.Path(__file__).parent
CLIPS, OUT, TMP = ROOT/"clips", ROOT/"out", ROOT/"out"/"tmp"
for d in (CLIPS, OUT, TMP): d.mkdir(exist_ok=True)
KEY = os.environ["OPENROUTER_API_KEY"]; MODEL = os.environ.get("VIDEO_MODEL", "google/veo-3.1-lite")
RAW = "https://raw.githubusercontent.com/echoi3/fake-news-ai/main/stills/shot{}.png"
W, H, FPS = 1280, 720, 24
FONT = "/System/Library/Fonts/AppleSDGothicNeo.ttc"

BASE = ("Realistic Korean TV footage, natural motion, cinematic. Start exactly from the first frame image and keep faces, "
        "clothes and setting identical. Dialogue in Korean, Seoul accent, lip-synced. ")
SHOTS = [  # (샷, 생성초, 사용초, 프롬프트)
    (1, 6, 6, "Live news studio. The anchor looks into the camera and reads urgently in Korean: \"속보입니다. 내일 전국 모든 학교가 휴교합니다. 기록적인 폭설 때문입니다.\" Subtle studio ambience, slight camera push-in."),
    (2, 4, 4, "Classroom. The students erupt in celebration, jumping and high-fiving, one boy shouts in Korean: \"내일 학교 안 가!\" Loud joyful chaos, chairs scraping."),
    (3, 4, 4, "Living room. The mother on the phone says cheerfully in Korean: \"부장님, 저 내일 연차 쓸게요. 애가 휴교래요.\" She nods and smiles, TV flickering behind."),
    (4, 4, 4, "Night street. The academy owner finishes taping the sign on the door, steps back, sighs and mutters in Korean: \"휴교면 휴강이지, 뭐.\" Street noise, neon buzz."),
    (5, 4, 4, "Phone close-up. The thumb scrolls fast as the news screenshot gets forwarded again and again, new messages popping in rapidly. Rapid notification sounds, no dialogue."),
    (6, 4, 4, "Empty classroom morning. The teacher slowly sips his coffee, looks around at the empty desks, blinks, and says flatly in Korean: \"...휴교 아닌데.\" Wall clock ticking, silence."),
    (7, 4, 4, "The glitching broadcast. The anchor's distorted face tries to speak in Korean through static: \"이 뉴스는... 가짜입니다.\" Heavy digital glitch, signal tearing, static noise bursts, then signal cuts out."),
]
SUBS = [(6.3, 9.8, "내일 학교 안 가!"), (10.3, 13.8, "부장님, 저 내일 연차 쓸게요"), (14.3, 17.8, "휴교면 휴강이지, 뭐"),
        (18.3, 21.8, "3분 만에 12만 명에게 전달"), (22.3, 25.8, "…휴교 아닌데")]


def api(method, url, body=None):
    req = urllib.request.Request(url, data=json.dumps(body).encode() if body else None, method=method,
                                 headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r: return json.load(r)


def gen(i, gdur, prompt):
    out = CLIPS/f"shot{i}.mp4"
    if out.exists(): print(f"shot {i}: exists"); return
    body = {"model": MODEL, "prompt": BASE + prompt, "duration": gdur, "resolution": "720p", "aspect_ratio": "16:9",
            "generate_audio": True,
            "frame_images": [{"type": "image_url", "image_url": {"url": RAW.format(i)}, "frame_type": "first_frame"}]}
    try: job = api("POST", "https://openrouter.ai/api/v1/videos", body)
    except urllib.error.HTTPError as e: print(f"shot {i}: submit failed {e.code}: {e.read()[:400]}"); return
    print(f"shot {i}: submitted {job['id']}"); t0 = time.time()
    while time.time() - t0 < 1500:
        time.sleep(15); st = api("GET", job["polling_url"])
        if st["status"] == "completed":
            req = urllib.request.Request(st["unsigned_urls"][0], headers={"Authorization": f"Bearer {KEY}"})
            with urllib.request.urlopen(req, timeout=600) as r: out.write_bytes(r.read())
            print(f"shot {i}: done {out.stat().st_size//1024} KB, cost={st.get('usage',{}).get('cost')}"); return
        if st["status"] in ("failed", "cancelled", "expired"): print(f"shot {i}: {st['status']}: {st.get('error')}"); return
    print(f"shot {i}: timeout")


# ---------- 그래픽 ----------
def font(sz, idx=0):
    from PIL import ImageFont; return ImageFont.truetype(FONT, sz, index=idx)

def text_center(d, xy, txt, f, fill, stroke=0, sfill=(0,0,0,255)):
    x0,y0,x1,y1 = d.textbbox((0,0), txt, font=f); d.text((xy[0]-(x1-x0)//2-x0, xy[1]-(y1-y0)//2-y0), txt, font=f, fill=fill, stroke_width=stroke, stroke_fill=sfill)

def png_subtitle(txt, path):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W,H), (0,0,0,0)); d = ImageDraw.Draw(im)
    text_center(d, (W//2, H-95), txt, font(56), (255,255,255,255), stroke=5); im.save(path)

def png_news(headline, sub, path):
    """뉴스 하단 띠: 속보 탭 + 헤드라인 + 채널 로고 + 티커"""
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W,H), (0,0,0,0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((40, 40, 300, 92), 8, fill=(200, 20, 30, 235)); text_center(d, (170, 66), "뉴스나우 24", font(30), (255,255,255,255))
    d.rounded_rectangle((330, 40, 440, 92), 8, fill=(255,255,255,235)); text_center(d, (385, 66), "LIVE", font(28), (200,20,30,255))
    d.rectangle((0, 548, W, 630), fill=(255,255,255,240)); d.rectangle((0, 548, 190, 630), fill=(200,20,30,255))
    text_center(d, (95, 589), "속보", font(44), (255,255,255,255))
    d.text((215, 560), headline, font=font(44), fill=(20,20,30,255))
    d.rectangle((0, 630, W, 672), fill=(20,30,60,245)); d.text((20, 638), sub, font=font(26), fill=(230,230,240,255))
    d.rectangle((0, 672, W, H), fill=(10,10,20,255)); d.text((20, 684), "기상청 「내일 새벽 최대 40cm 폭설」  ·  전국 초·중·고 1만 2천 곳 휴교  ·  학원·유치원도 휴원 권고  ·  출근길 대란 예상", font=font(24), fill=(200,200,210,255))
    im.save(path)

def png_card(lines, path, alpha=215):
    from PIL import Image, ImageDraw
    im = Image.new("RGBA", (W,H), (0,0,0,alpha)); d = ImageDraw.Draw(im)
    y = H//2 - 40*(len(lines)-1)
    for k, (txt, sz, col) in enumerate(lines): text_center(d, (W//2, y + k*84), txt, font(sz), col)
    im.save(path)


def ff(a): subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *a], check=True)

def assemble():
    norm = []
    for i, _, use, _ in SHOTS:
        src = CLIPS/f"shot{i}.mp4"
        if not src.exists(): sys.exit(f"shot{i}.mp4 없음")
        dst = TMP/f"n{i}.mp4"
        ff(["-i", str(src), "-t", str(use), "-vf", f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,fps={FPS}",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "48000", "-ac", "2", str(dst)]); norm.append(dst)
    (TMP/"c.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in norm))
    raw = TMP/"raw.mp4"; ff(["-f", "concat", "-safe", "0", "-i", str(TMP/"c.txt"), "-c", "copy", str(raw)])
    overlays = []  # (png, start, end)
    png_news("내일 전국 모든 학교 휴교", "기록적 폭설 예보… 교육 당국 「안전 최우선」", TMP/"news.png"); overlays.append((TMP/"news.png", 0, 6))
    for n, (s, e, t) in enumerate(SUBS): p = TMP/f"s{n}.png"; png_subtitle(t, p); overlays.append((p, s, e))
    png_news("내일 전국 모든 학교 휴교", "기록적 폭설 예보… 교육 당국 「안전 최우선」", TMP/"news2.png"); overlays.append((TMP/"news2.png", 26, 27.6))
    png_card([("이 뉴스는 AI가 30초 만에 만들었습니다.", 54, (255,255,255,255)), ("앵커도, 교실도, 학생도 실제로 없습니다.", 40, (220,220,230,255)),
              ("12만 명이 믿었습니다.", 40, (255,90,90,255))], TMP/"card.png"); overlays.append((TMP/"card.png", 27.6, 30.5))
    inputs, chain, prev = ["-i", str(raw)], [], "0:v"
    for k, (p, s, e) in enumerate(overlays):
        inputs += ["-i", str(p)]; chain.append(f"[{prev}][{k+1}:v]overlay=0:0:enable='between(t,{s},{e})'[v{k}]"); prev = f"v{k}"
    final = OUT/"fake_news_30s.mp4"
    ff([*inputs, "-filter_complex", ";".join(chain), "-map", f"[{prev}]", "-map", "0:a", "-c:v", "libx264", "-crf", "18",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", str(final)])
    print("FINAL:", final)

if __name__ == "__main__":
    if "--assemble-only" not in sys.argv:
        with cf.ThreadPoolExecutor(7) as ex: list(ex.map(lambda s: gen(s[0], s[1], s[3]), SHOTS))
    assemble()
