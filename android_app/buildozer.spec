[app]
title           = Gemini Client
package.name    = geminiclient
package.domain  = org.geminiclient
source.dir      = .
source.include_exts = py,png,jpg,kv,atlas,json
version         = 2.0

# 의존 패키지
# certifi: HTTPS SSL 인증서 (Gemini API 호출 필수)
requirements = python3,kivy==2.3.0,requests,certifi,charset-normalizer,urllib3,idna

# 앱 아이콘 (선택 — icon.png 파일을 android_app/ 에 넣으면 적용)
# icon.filename = %(source.dir)s/icon.png

orientation     = portrait
fullscreen      = 0

[buildozer]
log_level = 2

[app:android]
android.permissions     = INTERNET
android.api             = 33
android.minapi          = 21
android.ndk             = 25b
android.ndk_api         = 21
android.archs           = arm64-v8a, armeabi-v7a
android.allow_backup    = True
android.release_artifact = apk
