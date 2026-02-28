"""
Gemini Client — Mac 테스트용 (tkinter)
════════════════════════════════════════════════════════════════════════════════
android_app/main.py 와 동일한 기능을 tkinter로 구현한 Mac 전용 테스트 앱입니다.
실제 배포용은 android_app/main.py (Kivy) 입니다.
════════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import smtplib
import ssl
import threading
import tkinter as tk
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from tkinter import messagebox

import requests

# ── 설정 파일 경로 ─────────────────────────────────────────────────────────────
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587


# ── 설정 저장/불러오기 ─────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict) -> None:
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


# ── Gemini API 호출 ────────────────────────────────────────────────────────────

def call_gemini(api_key: str, prompt: str, timeout: int = 120) -> str:
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 8192},
    }
    resp = requests.post(
        GEMINI_API_URL,
        params={"key": api_key},
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()
    candidates = data.get("candidates", [])
    if not candidates:
        error_msg = data.get("error", {}).get("message", "응답 없음")
        raise ValueError(f"Gemini 응답 없음: {error_msg}")
    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


# ── 이메일 발송 ────────────────────────────────────────────────────────────────

def send_email(sender: str, password: str, receiver: str, prompt: str, response: str) -> None:
    subject = f"[Gemini] {prompt[:40]}{'...' if len(prompt) > 40 else ''}"
    plain = f"[질문]\n{prompt}\n\n[Gemini 응답]\n{response}"
    html = f"""<html><body>
<h3 style="color:#1a73e8">Gemini 응답</h3>
<p><b>질문:</b><br>{prompt.replace(chr(10), '<br>')}</p>
<hr>
<p><b>응답:</b><br>{response.replace(chr(10), '<br>')}</p>
</body></html>"""

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"]    = sender
    msg["To"]      = receiver
    msg.attach(MIMEText(plain, "plain", "utf-8"))
    msg.attach(MIMEText(html,  "html",  "utf-8"))

    context = ssl.create_default_context()
    with smtplib.SMTP(GMAIL_SMTP_HOST, GMAIL_SMTP_PORT) as server:
        server.ehlo()
        server.starttls(context=context)
        server.login(sender, password)
        server.sendmail(sender, receiver, msg.as_string())


# ── 색상 버튼 (Mac에서 tk.Button bg 색상 무시 문제 우회) ──────────────────────

class ColorButton(tk.Label):
    """
    Mac tkinter에서 tk.Button은 bg 색상이 적용되지 않습니다.
    tk.Label + 클릭 바인딩으로 색상이 완전히 적용되는 버튼을 구현합니다.
    """
    def __init__(self, parent, text, command, bg, fg="#ffffff",
                 font=("Arial", 12), padx=12, pady=6, **kwargs):
        self._bg_normal   = bg
        self._bg_hover    = self._lighten(bg)
        self._bg_disabled = "#555555"
        self._fg_normal   = fg
        self._fg_disabled = "#999999"
        self._command     = command
        self._disabled    = False

        super().__init__(
            parent, text=text, bg=bg, fg=fg,
            font=font, padx=padx, pady=pady,
            cursor="hand2", **kwargs
        )
        self.bind("<Enter>",        self._on_enter)
        self.bind("<Leave>",        self._on_leave)
        self.bind("<ButtonPress-1>",  self._on_press)
        self.bind("<ButtonRelease-1>", self._on_release)

    @staticmethod
    def _lighten(hex_color: str) -> str:
        """색상을 약간 밝게"""
        h = hex_color.lstrip("#")
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        r = min(255, r + 30)
        g = min(255, g + 30)
        b = min(255, b + 30)
        return f"#{r:02x}{g:02x}{b:02x}"

    def config_state(self, disabled: bool):
        self._disabled = disabled
        if disabled:
            self.config(bg=self._bg_disabled, fg=self._fg_disabled, cursor="")
        else:
            self.config(bg=self._bg_normal, fg=self._fg_normal, cursor="hand2")

    def _on_enter(self, _):
        if not self._disabled:
            self.config(bg=self._bg_hover)

    def _on_leave(self, _):
        if not self._disabled:
            self.config(bg=self._bg_normal)

    def _on_press(self, _):
        if not self._disabled:
            self.config(bg=self._bg_disabled)

    def _on_release(self, _):
        if not self._disabled:
            self.config(bg=self._bg_normal)
            self._command()


# ── 설정 다이얼로그 ────────────────────────────────────────────────────────────

class SettingsDialog(tk.Toplevel):
    def __init__(self, parent, config: dict):
        super().__init__(parent)
        self.title("설정")
        self.resizable(False, False)
        self.grab_set()
        self.config_result = None

        BG = "#1a1a2e"
        self.configure(bg=BG)
        pad = {"padx": 14, "pady": 3}

        def lbl(text):
            lb = tk.Label(self, text=text, bg=BG, fg="#cccccc",
                          font=("Arial", 11), anchor="w")
            lb.pack(fill="x", **pad)

        def ent(show=""):
            e = tk.Entry(self, font=("Arial", 12), bg="#0d0d1a", fg="#e0e0e0",
                         insertbackground="white", relief="flat",
                         highlightthickness=1, highlightcolor="#4455aa",
                         highlightbackground="#333355", show=show)
            e.pack(fill="x", padx=14, pady=(0, 4))
            # macOS pbpaste로 클립보드 직접 접근 (Cmd+V 대체)
            def _paste(ev, w=e):
                import subprocess
                try:
                    txt = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
                    try:
                        w.delete(tk.SEL_FIRST, tk.SEL_LAST)
                    except tk.TclError:
                        pass
                    w.insert(tk.INSERT, txt)
                except Exception:
                    pass
                return "break"
            def _select_all(ev, w=e):
                w.select_range(0, tk.END)
                w.icursor(tk.END)
                return "break"
            e.bind("<Command-v>", _paste)
            e.bind("<Command-a>", _select_all)
            return e

        lbl("Gemini API 키")
        self.e_api = ent()
        self.e_api.insert(0, config.get("gemini_api_key", ""))

        lbl("Gmail 발신자 이메일")
        self.e_sender = ent()
        self.e_sender.insert(0, config.get("gmail_sender", ""))

        lbl("Gmail 앱 비밀번호 (16자리)")
        self.e_passwd = ent(show="*")
        self.e_passwd.insert(0, config.get("gmail_password", ""))

        lbl("수신자 이메일")
        self.e_recv = ent()
        self.e_recv.insert(0, config.get("gmail_receiver", ""))

        tk.Label(self,
            text="Gemini API 키: aistudio.google.com/app/apikey\nGmail 앱 비밀번호: myaccount.google.com/apppasswords",
            bg=BG, fg="#66aa66", font=("Arial", 10), justify="left",
        ).pack(fill="x", padx=14, pady=(6, 4))

        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=14, pady=10)
        ColorButton(btn_frame, "저장", self._save,
                    bg="#1a73e8", font=("Arial", 12, "bold"),
                    padx=20, pady=7).pack(side="left", padx=(0, 8))
        ColorButton(btn_frame, "취소", self.destroy,
                    bg="#555555", font=("Arial", 12),
                    padx=20, pady=7).pack(side="left")

        self.geometry("430x370")
        self.e_api.focus_set()

    def _save(self):
        api_key  = self.e_api.get().strip()
        sender   = self.e_sender.get().strip()
        passwd   = self.e_passwd.get().strip()
        receiver = self.e_recv.get().strip()
        if not all([api_key, sender, passwd, receiver]):
            messagebox.showwarning("입력 오류", "모든 항목을 입력해주세요.", parent=self)
            return
        self.config_result = {
            "gemini_api_key": api_key,
            "gmail_sender":   sender,
            "gmail_password": passwd,
            "gmail_receiver": receiver,
        }
        self.destroy()


# ── 메인 앱 ───────────────────────────────────────────────────────────────────

class GeminiApp:
    def __init__(self, root: tk.Tk):
        self.root   = root
        self.config = load_config()
        root.title("Gemini 클라이언트 (Mac 테스트)")
        root.configure(bg="#1a1a2e")
        root.geometry("640x700")
        root.minsize(500, 600)
        self._build_ui()

        if not self._is_configured():
            root.after(300, self._open_settings)
        else:
            self._set_status("준비 완료 — 질문을 입력하세요", ok=True)
            self.send_btn.config_state(disabled=False)

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        BG   = "#1a1a2e"
        FG   = "#e0e0e0"
        DARK = "#0d0d1a"

        # 헤더
        hdr = tk.Frame(self.root, bg=BG)
        hdr.pack(fill="x", padx=16, pady=(14, 4))
        tk.Label(hdr, text="Gemini 클라이언트", font=("Arial", 18, "bold"),
                 bg=BG, fg=FG).pack(side="left")
        ColorButton(hdr, "⚙ 설정", self._open_settings,
                    bg="#3a3a5a", font=("Arial", 11),
                    padx=10, pady=4).pack(side="right")

        # 상태
        self.status_var = tk.StringVar(value="설정을 완료해 주세요")
        self.status_lbl = tk.Label(self.root, textvariable=self.status_var,
                                   font=("Arial", 11), bg=BG, fg="#999999",
                                   anchor="w")
        self.status_lbl.pack(fill="x", padx=16, pady=(0, 6))

        # 질문 입력
        tk.Label(self.root, text="질문 입력", font=("Arial", 12, "bold"),
                 bg=BG, fg=FG, anchor="w").pack(fill="x", padx=16)
        self.input_box = tk.Text(self.root, height=7, font=("Arial", 13),
                                 bg=DARK, fg=FG, insertbackground="white",
                                 relief="flat", padx=10, pady=8,
                                 wrap="word")
        self.input_box.pack(fill="x", padx=16, pady=(4, 8))

        # 전송 버튼
        self.send_btn = ColorButton(
            self.root,
            text="Gemini에 전송하고 메일 발송",
            command=self._on_send,
            bg="#1a73e8",
            font=("Arial", 14, "bold"),
            padx=0, pady=12,
        )
        self.send_btn.pack(fill="x", padx=16, pady=(0, 10))
        self.send_btn.config_state(disabled=True)

        # 응답 영역
        resp_hdr = tk.Frame(self.root, bg=BG)
        resp_hdr.pack(fill="x", padx=16)
        tk.Label(resp_hdr, text="Gemini 응답", font=("Arial", 12, "bold"),
                 bg=BG, fg=FG).pack(side="left")
        ColorButton(resp_hdr, "복사", self._copy_response,
                    bg="#3a3a5a", font=("Arial", 10),
                    padx=10, pady=3).pack(side="right")

        frame = tk.Frame(self.root, bg=BG)
        frame.pack(fill="both", expand=True, padx=16, pady=(4, 16))
        scrollbar = tk.Scrollbar(frame)
        scrollbar.pack(side="right", fill="y")
        self.response_box = tk.Text(
            frame, font=("Arial", 12),
            bg=DARK, fg="#c8c8c8",
            relief="flat", padx=10, pady=8,
            wrap="word", state="disabled",
            yscrollcommand=scrollbar.set,
        )
        self.response_box.pack(fill="both", expand=True)
        scrollbar.config(command=self.response_box.yview)

    # ── 설정 ─────────────────────────────────────────────────────────────────

    def _open_settings(self):
        dlg = SettingsDialog(self.root, self.config)
        self.root.wait_window(dlg)
        if dlg.config_result:
            self.config.update(dlg.config_result)
            save_config(self.config)
            self._set_status("설정 완료 — 질문을 입력하세요", ok=True)
            self.send_btn.config_state(disabled=False)

    def _is_configured(self) -> bool:
        return all(self.config.get(k) for k in
                   ["gemini_api_key", "gmail_sender", "gmail_password", "gmail_receiver"])

    # ── 전송 ─────────────────────────────────────────────────────────────────

    def _on_send(self):
        prompt = self.input_box.get("1.0", "end").strip()
        if not prompt:
            self._set_status("질문을 입력해주세요", error=True)
            return
        self.send_btn.config_state(disabled=True)
        self.input_box.delete("1.0", "end")
        self._set_response("")
        self._set_status("Gemini 응답 수신 중...")
        threading.Thread(target=self._process, args=(prompt,), daemon=True).start()

    def _process(self, prompt: str):
        cfg = self.config
        try:
            response = call_gemini(cfg["gemini_api_key"], prompt)
            self.root.after(0, lambda: self._set_response(response))
            self.root.after(0, lambda: self._set_status("이메일 발송 중..."))

            send_email(cfg["gmail_sender"], cfg["gmail_password"],
                       cfg["gmail_receiver"], prompt, response)
            self.root.after(0, lambda: self._set_status(
                f"완료 — 메일 발송: {cfg['gmail_receiver']}", ok=True))

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            if status == 400:
                msg = "API 오류 400 — API 키 또는 요청을 확인하세요"
            elif status == 403:
                msg = "API 오류 403 — API 키 권한 없음 또는 할당량 초과"
            else:
                msg = f"API HTTP 오류 {status}"
            self.root.after(0, lambda: self._set_status(msg, error=True))

        except requests.exceptions.ConnectionError:
            self.root.after(0, lambda: self._set_status(
                "네트워크 오류 — 인터넷 연결을 확인하세요", error=True))

        except requests.exceptions.Timeout:
            self.root.after(0, lambda: self._set_status(
                "타임아웃 — 다시 시도하세요", error=True))

        except smtplib.SMTPAuthenticationError:
            self.root.after(0, lambda: self._set_status(
                "이메일 인증 실패 — Gmail 앱 비밀번호를 확인하세요", error=True))

        except Exception as exc:
            self.root.after(0, lambda: self._set_status(f"오류: {exc}", error=True))

        finally:
            self.root.after(0, lambda: self.send_btn.config_state(disabled=False))

    # ── UI 헬퍼 ──────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, error: bool = False, ok: bool = False):
        self.status_var.set(msg)
        if error:
            self.status_lbl.config(fg="#ff5555")
        elif ok:
            self.status_lbl.config(fg="#55cc55")
        else:
            self.status_lbl.config(fg="#aaaaaa")

    def _set_response(self, text: str):
        self.response_box.config(state="normal")
        self.response_box.delete("1.0", "end")
        self.response_box.insert("1.0", text or "(응답이 여기에 표시됩니다)")
        self.response_box.config(state="disabled")

    def _copy_response(self):
        text = self.response_box.get("1.0", "end").strip()
        if text and text != "(응답이 여기에 표시됩니다)":
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self._set_status("응답이 클립보드에 복사되었습니다", ok=True)


# ── 실행 ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    root = tk.Tk()
    app = GeminiApp(root)
    root.mainloop()
