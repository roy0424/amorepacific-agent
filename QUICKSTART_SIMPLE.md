# 초간단 시작 가이드 ⚡

> 개발자가 아니어도 5분 안에 시작 가능!

---

## 1️⃣ 설치 (최초 1회)

**Mac/Linux:**
```bash
./setup.sh
```

**Windows:**
```bash
setup.bat
```

---

## 2️⃣ 실행 (단 한 줄!)

```bash
# Mac/Linux
source .venv/bin/activate
python scripts/start_all.py

# Windows
.venv\Scripts\activate.bat
python scripts\start_all.py
```

**이게 끝입니다!** 🎉

---

## 3️⃣ 확인

1. 브라우저에서 http://localhost:4200 열기
2. 실시간으로 데이터 수집 확인
3. 1시간마다 자동으로 Amazon 데이터 수집됨

---

## 4️⃣ 데이터 다운로드

```bash
# 새 터미널 열고
source .venv/bin/activate  # Mac/Linux
python scripts/export_data.py --format excel

# Excel 파일 생성됨!
open data/exports/amazon_data_*.xlsx  # Mac
explorer data\exports\amazon_data_*.xlsx  # Windows
```

---

## 🛑 종료

```
Ctrl+C
```

---

## 📚 더 자세히 알고 싶다면

- **팀원용 가이드:** `TEAMGUIDE.md`
- **개발자 가이드:** `QUICKSTART.md`
- **Prefect 가이드:** `PREFECT_GUIDE.md`

---

**그게 전부입니다! Happy Coding! 🚀**