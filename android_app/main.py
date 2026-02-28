"""
Gemini Client — Android 독립 실행 앱 (Kivy)
════════════════════════════════════════════════════════════════════════════════
모든 처리를 Android 폰에서 직접 수행합니다:
  1. 프롬프트 입력 (폰에서 직접)
  2. Gemini API 호출 (Mac 서버 불필요)
  3. 응답 표시
  4. 지정된 이메일로 자동 발송

초기 설정 (최초 실행 시):
  - Gemini API 키
  - Gmail 발신자 이메일 + 앱 비밀번호
  - 수신자 이메일
════════════════════════════════════════════════════════════════════════════════
"""

import json
import os
import smtplib
import ssl
import threading
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests
from kivy.app import App
from kivy.clock import Clock
from kivy.core.window import Window
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput

# ── 설정 파일 경로 (기기 내부 저장소) ─────────────────────────────────────────

CONFIG_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "config.json"
)

# Gemini REST API 엔드포인트 (gemini-1.5-flash: 빠르고 무료 할당량 풍부)
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)

# Gmail SMTP 설정
GMAIL_SMTP_HOST = "smtp.gmail.com"
GMAIL_SMTP_PORT = 587   # STARTTLS


# ── 설정 저장/불러오기 ─────────────────────────────────────────────────────────

def load_config() -> dict:
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def save_config(data: dict) -> None:
    try:
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


# ── Gemini API 호출 ────────────────────────────────────────────────────────────

def call_gemini(api_key: str, prompt: str, timeout: int = 120) -> str:
    """Gemini REST API로 프롬프트를 전송하고 응답 텍스트를 반환합니다."""
    payload = {
        "contents": [
            {"parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        }
    }
    resp = requests.post(
        GEMINI_API_URL,
        params={"key": api_key},
        json=payload,
        timeout=timeout,
    )
    resp.raise_for_status()
    data = resp.json()

    # 응답 텍스트 추출
    candidates = data.get("candidates", [])
    if not candidates:
        error_msg = data.get("error", {}).get("message", "응답 없음")
        raise ValueError(f"Gemini 응답 없음: {error_msg}")

    parts = candidates[0].get("content", {}).get("parts", [])
    return "".join(p.get("text", "") for p in parts).strip()


# ── 이메일 발송 ────────────────────────────────────────────────────────────────

def send_email(
    sender: str,
    password: str,
    receiver: str,
    prompt: str,
    response: str,
) -> None:
    """Gmail SMTP(STARTTLS)로 Gemini 응답을 이메일로 발송합니다."""
    subject = f"[Gemini] {prompt[:40]}{'...' if len(prompt) > 40 else ''}"

    # 본문 구성
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


# ── 설정 팝업 ──────────────────────────────────────────────────────────────────

class SettingsPopup(Popup):
    """Gemini API 키 + Gmail 설정을 입력받는 팝업."""

    def __init__(self, config: dict, on_save_callback, **kwargs):
        self._cfg      = config
        self._callback = on_save_callback

        content = BoxLayout(orientation="vertical", padding=14, spacing=8)

        def _lbl(text):
            return Label(
                text=text,
                size_hint_y=None, height=26,
                font_size="13sp",
                color=(0.85, 0.85, 0.85, 1),
                halign="left", valign="middle",
            )

        def _inp(hint, secret=False):
            ti = TextInput(
                hint_text=hint,
                size_hint_y=None, height=42,
                font_size="14sp",
                background_color=(0.07, 0.07, 0.12, 1),
                foreground_color=(0.9, 0.9, 0.9, 1),
                multiline=False,
                password=secret,
            )
            return ti

        content.add_widget(_lbl("Gemini API 키"))
        self._api_key = _inp("AIzaSy...")
        self._api_key.text = config.get("gemini_api_key", "")
        content.add_widget(self._api_key)

        content.add_widget(_lbl("Gmail 발신자 이메일"))
        self._sender = _inp("sender@gmail.com")
        self._sender.text = config.get("gmail_sender", "")
        content.add_widget(self._sender)

        content.add_widget(_lbl("Gmail 앱 비밀번호 (16자리)"))
        self._passwd = _inp("xxxx xxxx xxxx xxxx", secret=True)
        self._passwd.text = config.get("gmail_password", "")
        content.add_widget(self._passwd)

        content.add_widget(_lbl("수신자 이메일"))
        self._receiver = _inp("receiver@example.com")
        self._receiver.text = config.get("gmail_receiver", "")
        content.add_widget(self._receiver)

        # 안내 문구
        guide = Label(
            text=(
                "Gemini API 키: console.cloud.google.com\n"
                "Gmail 앱 비밀번호: myaccount.google.com/apppasswords\n"
                "(2단계 인증 활성화 필수)"
            ),
            size_hint_y=None, height=56,
            font_size="11sp",
            color=(0.55, 0.75, 0.55, 1),
            halign="left", valign="top",
        )
        guide.bind(size=guide.setter("text_size"))
        content.add_widget(guide)

        btns = BoxLayout(size_hint_y=None, height=46, spacing=8)
        save_btn   = Button(text="저장",  background_color=(0.1, 0.45, 0.91, 1))
        cancel_btn = Button(text="취소",  background_color=(0.3, 0.3, 0.3, 1))
        btns.add_widget(save_btn)
        btns.add_widget(cancel_btn)
        content.add_widget(btns)

        super().__init__(
            title="설정 (API 키 & 이메일)",
            content=content,
            size_hint=(0.92, None),
            height=520,
            **kwargs,
        )

        save_btn.bind(on_press=self._on_save)
        cancel_btn.bind(on_press=self.dismiss)

    def _on_save(self, _):
        api_key  = self._api_key.text.strip()
        sender   = self._sender.text.strip()
        passwd   = self._passwd.text.strip()
        receiver = self._receiver.text.strip()

        if not all([api_key, sender, passwd, receiver]):
            return   # 필드 미입력 시 무시

        self._cfg.update({
            "gemini_api_key":  api_key,
            "gmail_sender":    sender,
            "gmail_password":  passwd,
            "gmail_receiver":  receiver,
        })
        save_config(self._cfg)
        self.dismiss()
        self._callback(self._cfg)


# ── 메인 레이아웃 ──────────────────────────────────────────────────────────────

class GeminiLayout(BoxLayout):

    def __init__(self, **kwargs):
        super().__init__(orientation="vertical", padding=16, spacing=10, **kwargs)
        self._config = load_config()
        self._build_ui()

        # 설정 미완료 시 설정 팝업 자동 표시
        if not self._is_configured():
            Clock.schedule_once(lambda dt: self._open_settings(), 0.5)
        else:
            self._set_status("준비 완료 — 질문을 입력하세요")
            self._send_btn.disabled = False

    # ── UI 구성 ───────────────────────────────────────────────────────────────

    def _build_ui(self):
        Window.clearcolor = (0.10, 0.10, 0.16, 1)

        # ── 헤더 ──
        header = BoxLayout(size_hint_y=None, height=52, spacing=8)
        title_lbl = Label(
            text="Gemini 클라이언트",
            font_size="20sp", bold=True,
            color=(0.88, 0.88, 0.88, 1),
            halign="left", valign="middle",
        )
        title_lbl.bind(size=title_lbl.setter("text_size"))
        header.add_widget(title_lbl)

        settings_btn = Button(
            text="⚙ 설정",
            size_hint=(None, 1), width=90,
            font_size="13sp",
            background_color=(0.25, 0.25, 0.38, 1),
            color=(0.88, 0.88, 0.88, 1),
        )
        settings_btn.bind(on_press=lambda _: self._open_settings())
        header.add_widget(settings_btn)
        self.add_widget(header)

        # ── 상태 표시 ──
        self._status_lbl = Label(
            text="설정을 완료해 주세요",
            size_hint_y=None, height=30,
            font_size="13sp",
            color=(0.6, 0.6, 0.6, 1),
            halign="left", valign="middle",
        )
        self._status_lbl.bind(size=self._status_lbl.setter("text_size"))
        self.add_widget(self._status_lbl)

        # ── 질문 입력창 ──
        q_label = Label(
            text="질문 입력",
            size_hint_y=None, height=26,
            font_size="14sp", bold=True,
            color=(0.88, 0.88, 0.88, 1),
            halign="left", valign="middle",
        )
        q_label.bind(size=q_label.setter("text_size"))
        self.add_widget(q_label)

        self._input = TextInput(
            hint_text="Gemini에게 물어볼 내용을 입력하세요",
            size_hint_y=None, height=140,
            font_size="15sp",
            background_color=(0.07, 0.07, 0.12, 1),
            foreground_color=(0.9, 0.9, 0.9, 1),
            cursor_color=(0.4, 0.6, 1, 1),
            padding=(12, 10),
            multiline=True,
        )
        self.add_widget(self._input)

        # ── 전송 버튼 ──
        self._send_btn = Button(
            text="Gemini에 전송하고 메일 발송",
            size_hint_y=None, height=54,
            font_size="16sp", bold=True,
            background_color=(0.1, 0.45, 0.91, 1),
            color=(1, 1, 1, 1),
            disabled=True,
        )
        self._send_btn.bind(on_press=self._on_send)
        self.add_widget(self._send_btn)

        # ── 응답 영역 ──
        resp_header = BoxLayout(size_hint_y=None, height=34, spacing=8)
        resp_lbl = Label(
            text="Gemini 응답",
            font_size="14sp", bold=True,
            color=(0.88, 0.88, 0.88, 1),
            halign="left", valign="middle",
        )
        resp_lbl.bind(size=resp_lbl.setter("text_size"))
        resp_header.add_widget(resp_lbl)

        copy_btn = Button(
            text="복사",
            size_hint=(None, 1), width=66,
            font_size="13sp",
            background_color=(0.25, 0.25, 0.38, 1),
            color=(0.88, 0.88, 0.88, 1),
        )
        copy_btn.bind(on_press=self._copy_response)
        resp_header.add_widget(copy_btn)
        self.add_widget(resp_header)

        scroll = ScrollView()
        self._response_lbl = Label(
            text="(응답이 여기에 표시됩니다)",
            font_size="14sp",
            color=(0.78, 0.78, 0.78, 1),
            halign="left", valign="top",
            markup=True,
            size_hint_y=None,
        )
        self._response_lbl.bind(
            width=lambda *_: self._response_lbl.setter("text_size")(
                self._response_lbl, (self._response_lbl.width, None)
            ),
            texture_size=lambda *_: self._response_lbl.setter("height")(
                self._response_lbl, self._response_lbl.texture_size[1]
            ),
        )
        scroll.add_widget(self._response_lbl)
        self.add_widget(scroll)

    # ── 설정 팝업 ─────────────────────────────────────────────────────────────

    def _open_settings(self):
        def _on_saved(cfg):
            self._config = cfg
            self._set_status("설정 완료 — 질문을 입력하세요")
            self._send_btn.disabled = False

        SettingsPopup(self._config, _on_saved).open()

    def _is_configured(self) -> bool:
        required = ["gemini_api_key", "gmail_sender", "gmail_password", "gmail_receiver"]
        return all(self._config.get(k) for k in required)

    # ── 전송 ─────────────────────────────────────────────────────────────────

    def _on_send(self, _):
        prompt = self._input.text.strip()
        if not prompt:
            self._set_status("질문을 입력해주세요", error=True)
            return

        self._send_btn.disabled = True
        self._input.text = ""
        self._response_lbl.text = ""
        self._set_status("Gemini에 요청 중...")
        threading.Thread(target=self._process, args=(prompt,), daemon=True).start()

    def _process(self, prompt: str):
        cfg = self._config
        try:
            # 1단계: Gemini API 호출
            Clock.schedule_once(lambda dt: self._set_status("Gemini 응답 수신 중..."))
            response = call_gemini(cfg["gemini_api_key"], prompt)

            # UI에 응답 표시
            Clock.schedule_once(lambda dt: self._show_response(response))

            # 2단계: 이메일 발송
            Clock.schedule_once(lambda dt: self._set_status("이메일 발송 중..."))
            send_email(
                sender=cfg["gmail_sender"],
                password=cfg["gmail_password"],
                receiver=cfg["gmail_receiver"],
                prompt=prompt,
                response=response,
            )
            Clock.schedule_once(lambda dt: self._set_status(
                f"완료 — 메일 발송: {cfg['gmail_receiver']}"
            ))

        except requests.exceptions.HTTPError as e:
            status = e.response.status_code if e.response else "?"
            if status == 400:
                msg = "API 오류 400 — API 키 또는 요청 형식을 확인하세요"
            elif status == 403:
                msg = "API 오류 403 — API 키 권한 없음 또는 할당량 초과"
            else:
                msg = f"API HTTP 오류 {status}"
            Clock.schedule_once(lambda dt: self._set_status(msg, error=True))

        except requests.exceptions.ConnectionError:
            Clock.schedule_once(lambda dt: self._set_status(
                "네트워크 오류 — 인터넷 연결을 확인하세요", error=True
            ))

        except requests.exceptions.Timeout:
            Clock.schedule_once(lambda dt: self._set_status(
                "타임아웃 — 응답이 너무 오래 걸립니다. 다시 시도하세요", error=True
            ))

        except smtplib.SMTPAuthenticationError:
            Clock.schedule_once(lambda dt: self._set_status(
                "이메일 인증 실패 — Gmail 앱 비밀번호를 확인하세요", error=True
            ))

        except Exception as exc:
            Clock.schedule_once(lambda dt: self._set_status(
                f"오류: {exc}", error=True
            ))

        finally:
            Clock.schedule_once(
                lambda dt: setattr(self._send_btn, "disabled", False)
            )

    # ── UI 헬퍼 ──────────────────────────────────────────────────────────────

    def _set_status(self, msg: str, error: bool = False):
        self._status_lbl.text  = msg
        self._status_lbl.color = (1, 0.35, 0.28, 1) if error else (0.5, 0.85, 0.5, 1) if "완료" in msg else (0.6, 0.6, 0.6, 1)

    def _show_response(self, text: str):
        self._response_lbl.text = text or "(응답 없음)"

    def _copy_response(self, _):
        from kivy.core.clipboard import Clipboard
        txt = self._response_lbl.text
        if txt and txt != "(응답이 여기에 표시됩니다)":
            Clipboard.copy(txt)
            self._set_status("응답이 클립보드에 복사되었습니다")


# ── App 클래스 ────────────────────────────────────────────────────────────────

class GeminiApp(App):
    def build(self):
        self.title = "Gemini 클라이언트"
        return GeminiLayout()


if __name__ == "__main__":
    GeminiApp().run()
