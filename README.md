# 個人網站

單頁、精簡的學術／求職個人網站，版面參考 academicpages 風格：左側個人欄，右側依序是
About / News / Education / Experience / Projects / Publications / Awards。

內容全部放在 `content/*.yml`，用 Python 產生靜態 HTML 到 `dist/`，直接丟上 GitHub Pages。

**日常維護只有一件事：改 YAML，跑一次 build。** 不用碰 HTML 或 CSS。

---

## 快速開始

第一次先安裝套件：

```bash
pip install -r requirements.txt
```

之後每次要看結果：

```bash
python build.py --serve
```

打開 http://localhost:8000。改完 YAML 後 Ctrl+C 停掉、再跑一次即可。
只想產檔不開伺服器就跑 `python build.py`，結果在 `dist/`。

---

## 檔案在哪裡

| 路徑 | 做什麼 |
|---|---|
| `content/site.yml` | 姓名、頭銜、聯絡連結、About、Skills、News、Certificates、獎項 |
| `content/experience.yml` | 學歷 + 經歷 |
| `content/projects.yml` | 專案（**最常改的就是這個**） |
| `content/publications.yml` | 論文，自動依年份分組 |
| `static/img/` | 大頭照、專案縮圖 |
| `static/files/` | CV PDF |
| `static/css/style.css` | 外觀。顏色與間距在最上面的 `:root` |
| `templates/index.html` | 版面結構，平常不用動 |
| `build.py` | 產生器 |
| `dist/` | 產出結果，**不要手動改**，每次 build 都會重蓋 |

YAML 規則只有兩條：縮排用空格不要用 Tab，冒號後面要有一個空格。
任何欄位留空 `""` 就會自動從網頁上消失。整個區塊沒內容（例如 `news: []`）該區塊和上方的導覽連結也會一起消失。

---

## 常見操作

### 新增一個專案

打開 `content/projects.yml`，複製一整段貼在最上面，改內容：

```yaml
- title: 專案名稱
  year: "2025"
  summary: 一到三句話：做什麼、你負責什麼、難點在哪。
  tags: [Python, PyTorch]
  image: img/my-project.png      # 選填，圖片先放進 static/img/
  links:
    - label: Code
      url: https://github.com/yourhandle/repo
  featured: true                 # 改 false 就隱藏但保留資料
```

專案會**自動依 `year` 由新到舊排序**（"Sep–Oct 2024"、"2022–23" 這類寫法也認得），同一年內照檔案順序。

### 放圖片集與示範影片

在專案加上 `images`（點縮圖會開原圖）和 `videos`。短片自己放檔案，長片或有旁白的用 YouTube：

```yaml
  images:
    - src: img/pcb.png
      caption: PCB layout
    - src: img/photo.jpg
      caption: Assembled car
  videos:
    - src: files/demo.mp4          # 檔案放 static/files/
      poster: img/demo-thumb.jpg   # 選填，播放前的縮圖
      caption: Demo
    - src: https://youtu.be/XXXXXXXXXXX
      caption: Walkthrough
```

只有一支影片時也可以簡寫成 `video: files/demo.mp4` 加 `poster:`。

自架檔案建議壓到 10MB 以內，用 ffmpeg：

```bash
ffmpeg -i input.mp4 -vf scale=960:-2 -c:v libx264 -crf 28 -an -movflags +faststart static/files/demo.mp4
```

（`-an` 去掉音軌，`-crf` 越大檔案越小、畫質越差，28 通常夠用）

### 新增一篇論文

打開 `content/publications.yml`，加一段。`year` 決定分在哪一組；
`authors` 裡出現你在 `site.yml` 的 `name` 會自動粗體：

```yaml
- title: 論文題目
  authors: "Your Name, A. Coauthor"
  venue: "In Some Conference **(ABC 2025)**"
  year: "2025"
  links:
    - label: paper
      url: https://arxiv.org/abs/xxxx
    - label: code
      url: https://github.com/...
```

### 新增學歷或經歷

`content/experience.yml` 的 `education:` 或 `work:` 底下加一段，新的放上面。

### 放大頭照、CV

- 照片放 `static/img/photo.jpg`，在 `site.yml` 設 `photo: img/photo.jpg`
- 履歷放 `static/files/resume.pdf`，在 `site.yml` 設 `cv: files/resume.pdf`，左側會出現 Resume 下載按鈕

### 改顏色、字體、寬度

只改 `static/css/style.css` 最上面 `:root` 的變數：`--accent`（連結色）、`--fg`／`--bg`、
`--measure`（內文欄寬）、`--sidebar`（左欄寬）。深色模式在下面的 `prefers-color-scheme: dark` 區塊。

---

## 檢查

build 時若 YAML 指到不存在的圖片或 PDF，會印出：

```
  ! missing file - site.photo: static/img/photo.jpg
```

路徑一律相對於 `static/`，寫 `img/photo.jpg`，不是 `static/img/photo.jpg`。

---

## 發佈到 GitHub Pages

發佈後網站由 GitHub 代管，**電腦不用開著**。每次 push，GitHub Actions 會自己跑
`build.py` 並把 `dist/` 發佈到 `https://hoogashaga.github.io/`。

第一次設定：

1. 到 https://github.com/new 建一個 **public** repo，名稱一定要是 `Hoogashaga.github.io`（不要勾 README）。
2. 在專案資料夾執行：

```bash
git init
git add .
git commit -m "Initial site"
git branch -M main
git remote add origin https://github.com/Hoogashaga/Hoogashaga.github.io.git
git push -u origin main
```

   第一次 push 會跳出 GitHub 登入視窗，登入即可。

3. 到 repo 的 **Settings → Pages → Build and deployment → Source** 選 **GitHub Actions**。
4. 等 **Actions** 分頁的工作跑完（約一分鐘），打開 https://hoogashaga.github.io/。

日常更新就三行：

```bash
git add . && git commit -m "Update projects" && git push
```

`dist/` 在 `.gitignore` 裡不會被 commit，GitHub 那邊會自己重新 build。

---

## 隱藏式訪客統計

GitHub Pages 沒有伺服器記錄，要看人數得掛分析服務。這裡用 **GoatCounter**：
免費、開源、不用 cookie、網頁上看不出任何東西，只有你登入後台才看得到。

1. 到 https://www.goatcounter.com/signup 註冊，取一個代碼（例如 `orionchen`）。
2. 在 `content/site.yml` 填 `goatcounter: orionchen`，push。
3. 之後到 `https://orionchen.goatcounter.com` 看：訪客數、來源網站、國家、裝置、看了哪個區塊。

能看到的是「多少人、從哪來」。**任何分析工具都無法知道訪客是誰**，沒有登入就無法識別個人，
這是隱私法規的底線，也沒有正當的方法繞過。
