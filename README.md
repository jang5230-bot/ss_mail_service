# Gemini Client

Android 폰에서 직접 Gemini AI에 질문하고, 응답을 지정된 이메일로 자동 발송하는 앱입니다.

## 아키텍처

```
Android 폰
  ├── 프롬프트 입력 (Kivy UI)
  ├── Gemini API 직접 호출  ─── gemini.googleapis.com
  ├── 응답 표시
  └── Gmail SMTP 이메일 발송  ─── smtp.gmail.com
```

Mac/PC 서버 없이 폰 단독으로 동작합니다.

---

## Android APK 설치 및 사용

### 1. 사전 준비

#### Gemini API 키 발급
1. [Google AI Studio](https://aistudio.google.com/app/apikey) 접속
2. "API 키 만들기" 클릭
3. API 키 복사 (`AIzaSy...` 형식)

#### Gmail 앱 비밀번호 발급
1. Google 계정에서 **2단계 인증** 활성화 (필수)
2. [앱 비밀번호](https://myaccount.google.com/apppasswords) 페이지 접속
3. "앱 비밀번호 만들기" → 16자리 비밀번호 복사

---

### 2. APK 빌드 (Mac/Linux에서 1회만)

```bash
# 빌드 도구 설치
pip install buildozer

# android_app 폴더로 이동
cd android_app

# APK 빌드 (최초 10~30분 소요)
buildozer android debug
```

빌드 완료 후 `android_app/bin/geminiclient-2.0-debug.apk` 생성

---

### 3. APK 설치

```bash
# USB 연결 후 설치 (개발자 옵션 + USB 디버깅 활성화 필요)
adb install bin/geminiclient-2.0-debug.apk
```

또는 APK 파일을 폰으로 전송 후 직접 설치 (알 수 없는 출처 허용 필요)

---

### 4. 앱 최초 설정

앱 실행 시 설정 화면이 자동으로 표시됩니다:

| 항목 | 설명 |
|------|------|
| Gemini API 키 | `AIzaSy...` 형식의 키 |
| Gmail 발신자 이메일 | 이메일을 보낼 Gmail 주소 |
| Gmail 앱 비밀번호 | 16자리 앱 전용 비밀번호 |
| 수신자 이메일 | 응답 메일을 받을 이메일 |

설정은 폰 내부 `config.json`에 저장되어 재실행 시 유지됩니다.

---

### 5. 사용 방법

1. 앱 실행
2. 질문 입력창에 Gemini에게 물어볼 내용 입력
3. **"Gemini에 전송하고 메일 발송"** 버튼 탭
4. 응답이 화면에 표시되고 지정된 이메일로 자동 발송

---

## Mac/PC에서 로컬 테스트

Android APK 없이 Mac에서도 테스트 가능합니다.

```bash
# 의존성 설치
pip install kivy requests certifi

# 실행 (Kivy 창이 열림)
python android_app/main.py
```

---

## Mac Playwright 버전 (선택사항)

브라우저 자동화 방식이 필요한 경우 `gemini_client.py`를 사용합니다.

```bash
# 설치
pip install -r requirements.txt
playwright install chromium

# 설정
cp .env.example .env
# .env 파일에 Gmail 정보 입력

# 실행
python gemini_client.py
```

---

## 파일 구조

```
ss_mail_service/
├── android_app/
│   ├── main.py          # Android 앱 (Kivy) — 메인 파일
│   ├── buildozer.spec   # APK 빌드 설정
│   └── requirements.txt # 의존 패키지
├── gemini_client.py     # Mac Playwright 버전 (선택)
├── server.py            # Mac Flask REST API 서버 (선택)
├── requirements.txt     # Mac 의존 패키지
└── .env.example         # 환경 변수 예시
```

---

## 문제 해결

### API 오류 403
- Gemini API 키가 올바른지 확인
- [Google AI Studio](https://aistudio.google.com/app/apikey)에서 키 재발급

### 이메일 인증 실패
- Gmail 계정의 2단계 인증이 활성화되어 있는지 확인
- 앱 비밀번호가 올바른지 확인 (계정 비밀번호 X)
- [앱 비밀번호 재발급](https://myaccount.google.com/apppasswords)

### 네트워크 오류
- 인터넷 연결 확인
- 모바일 데이터 또는 Wi-Fi 활성화
