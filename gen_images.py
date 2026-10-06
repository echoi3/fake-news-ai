"""앵커 캐릭터 시트 + 샷 스틸 7장 (OpenRouter → Gemini 3 Pro Image)."""
import base64, json, os, sys, urllib.request, pathlib, time
KEY = os.environ["OPENROUTER_API_KEY"]; MODEL = "google/gemini-3-pro-image"
ROOT = pathlib.Path(__file__).parent; CH, ST = ROOT/"characters", ROOT/"stills"

def call(parts):
    body = {"model": MODEL, "messages": [{"role": "user", "content": parts}], "modalities": ["image", "text"]}
    req = urllib.request.Request("https://openrouter.ai/api/v1/chat/completions", data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {KEY}", "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r: res = json.load(r)
    imgs = res["choices"][0]["message"].get("images") or []
    if not imgs: raise RuntimeError(json.dumps(res)[:400])
    return base64.b64decode(imgs[0]["image_url"]["url"].split(",", 1)[1])

def img_part(p):
    return {"type": "image_url", "image_url": {"url": "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode()}}

BASE = "Photorealistic Korean TV still, 16:9 widescreen, cinematic, natural lighting, no text, no captions, no logos, no watermark. "
ANCHOR = ("Character reference: Korean female news anchor in her mid 30s, shoulder-length dark hair neatly styled, "
          "navy blazer over white blouse, calm professional expression, looking at camera, plain studio background, waist-up.")
SHOTS = {
    1: "Modern Korean TV news studio with a blue and white backdrop and a large blank screen behind. The anchor from the reference sits at the desk, looking straight at camera with a serious urgent expression, hands on desk. Leave the lower third of the frame clean and uncluttered.",
    2: "Korean high school classroom during break. Four students in uniforms crowd around one smartphone, faces lit up with joy, one boy throwing both arms up cheering, another shouting. Energetic, candid.",
    3: "Korean apartment living room, evening. A mother in her 40s in a cardigan stands holding a phone to her ear, other hand on hip, relieved smile, with the TV news glowing in the background out of focus.",
    4: "Night street in Seoul. The owner of a small private academy (hagwon), a man in his 50s with glasses, tapes a handwritten paper sign on the glass door; the paper is blank white. Neon signs around, slightly worried expression.",
    5: "Extreme close-up of a smartphone held in a hand, showing a Korean group chat app with many message bubbles and a screenshot thumbnail of a news broadcast being shared repeatedly; blurred thumbs scrolling. Shallow depth of field.",
    6: "Next morning. A bright, completely empty Korean high school classroom, all desks vacant. A male teacher in his 50s sits alone at the front desk, staring blankly, holding a cup of coffee. Sunlight through windows. Quiet, deadpan comedy.",
    7: "The same news studio and the same anchor from the reference, but the image is corrupted with digital glitch artifacts, RGB channel splitting, horizontal tearing and pixel blocks, as if the broadcast signal is breaking apart. The anchor's face is half distorted. Dark, eerie.",
}
only = [int(x) for x in sys.argv[1:]]
if not only or 0 in only:
    (CH/"anchor.png").write_bytes(call([{"type": "text", "text": BASE + ANCHOR}])); print("anchor ok")
ref = img_part(CH/"anchor.png")
for i, d in SHOTS.items():
    if only and i not in only: continue
    parts = [{"type": "text", "text": BASE + d}] + ([ref] if i in (1, 7) else [])
    for t in range(3):
        try: (ST/f"shot{i}.png").write_bytes(call(parts)); print("shot", i, "ok"); break
        except Exception as e: print("shot", i, "retry", t, str(e)[:200]); time.sleep(3)
