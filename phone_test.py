"""
Gemini Client — Termux(Android) CLI 테스트용
Kivy 불필요, requests + smtplib만 사용
"""
import json, os, smtplib, ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import requests

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

def load_config():
    try:
        with open(CONFIG_FILE) as f:
            return json.load(f)
    except Exception:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def setup():
    print("\n=== 초기 설정 ===")
    return {
        "gemini_api_key":  input("Gemini API 키: ").strip(),
        "gmail_sender":    input("Gmail 발신자: ").strip(),
        "gmail_password":  input("Gmail 앱 비밀번호: ").strip(),
        "gmail_receiver":  input("수신자 이메일: ").strip(),
    }

def call_gemini(api_key, prompt):
    resp = requests.post(
        GEMINI_API_URL,
        params={"key": api_key},
        json={"contents": [{"parts": [{"text": prompt}]}]},
        timeout=120,
    )
    resp.raise_for_status()
    parts = resp.json()["candidates"][0]["content"]["parts"]
    return "".join(p.get("text", "") for p in parts).strip()

def send_email(cfg, prompt, response):
    subject = f"[Gemini] {prompt[:40]}{'...' if len(prompt)>40 else ''}"
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = cfg["gmail_sender"]
    msg["To"]      = cfg["gmail_receiver"]
    msg.attach(MIMEText(f"[질문]\n{prompt}\n\n[응답]\n{response}", "plain", "utf-8"))
    ctx = ssl.create_default_context()
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.ehlo(); s.starttls(context=ctx)
        s.login(cfg["gmail_sender"], cfg["gmail_password"])
        s.sendmail(cfg["gmail_sender"], cfg["gmail_receiver"], msg.as_string())

def main():
    cfg = load_config()
    if not all(cfg.get(k) for k in ["gemini_api_key","gmail_sender","gmail_password","gmail_receiver"]):
        cfg = setup()
        save_config(cfg)

    print(f"\n준비 완료 — 수신자: {cfg['gmail_receiver']}")
    print("종료: Ctrl+C\n")

    while True:
        try:
            prompt = input("질문 > ").strip()
            if not prompt:
                continue
            print("Gemini 응답 수신 중...")
            response = call_gemini(cfg["gemini_api_key"], prompt)
            print(f"\n[응답]\n{response}\n")
            print("이메일 발송 중...")
            send_email(cfg, prompt, response)
            print(f"완료 — {cfg['gmail_receiver']}로 발송됨\n")
        except KeyboardInterrupt:
            print("\n종료")
            break
        except Exception as e:
            print(f"오류: {e}\n")

if __name__ == "__main__":
    main()
