# GOM Pipeline 🏺

**Hệ Thống Điều Phối & Giám Sát Quy Trình Sản Xuất Xưởng Gốm**

Một giải pháp phần mềm B2B (Business-to-Business) giúp số hóa toàn bộ quy trình sản xuất của xưởng gốm sứ. GOM Pipeline giải quyết triệt để các bài toán thường gặp trong xưởng thủ công: nhập liệu rườm rà, sai lệch dữ liệu do thao tác đồng thời (race conditions), và luồng xử lý hàng lỗi kém linh hoạt.

---

## ✨ Tính năng nổi bật

| Tính năng | Mô tả |
|---|---|
| **Kanban Board real-time** | Dashboard hiển thị toàn bộ mẻ gốm theo 7 công đoạn, cập nhật tức thì qua WebSocket |
| **AI phân tích đơn hàng** | Dùng Google Gemini 3.6 Flash tự động bóc tách thông số kỹ thuật (loại men, nhiệt độ nung, số lượng đất sét...) từ mô tả văn bản tự nhiên |
| **Xử lý hàng lỗi (Rework/Split)** | Tách mẻ con, quay lại công đoạn trước — giới hạn tối đa 2 lần rework để tránh lặp vô hạn |
| **Telegram Bot tích hợp** | Thông báo tự động khi chuyển công đoạn, báo sự cố; thợ xác nhận trực tiếp qua inline-button |
| **Optimistic Concurrency** | Sử dụng `expected_stage` để chống race condition khi nhiều người thao tác đồng thời |
| **Background Queue Worker** | Xử lý đơn hàng bất đồng bộ qua hàng đợi (concurrency = 2), không block API response |
| **Regex Fallback** | Khi không có API key Gemini, hệ thống tự động fallback sang regex parser |

---

## 🏗 Kiến trúc hệ thống

```mermaid
graph LR
    subgraph Frontend
        A[React + Vite<br/>Kanban Dashboard]
    end

    subgraph Backend
        B[FastAPI<br/>REST API + WebSocket Hub]
        C[Workflow Engine<br/>State Machine 7 bước]
        D[Queue Worker<br/>Async Job Processing]
        E[AI Agent<br/>Gemini / Regex Fallback]
    end

    subgraph External
        F[(SQLite / PostgreSQL)]
        G[Google Gemini API]
        H[Telegram Bot API]
    end

    A -- HTTP + WS --> B
    B --> C
    B --> D
    D --> E
    E --> G
    B --> H
    C --> F
    D --> F
```

**Luồng hoạt động chính:**

1. Người dùng nhập mô tả đơn hàng bằng ngôn ngữ tự nhiên trên Dashboard
2. API trả về `202 Accepted` ngay lập tức, đẩy job vào **Queue Worker**
3. Worker gọi **AI Agent** (Gemini) để bóc tách thông số → cập nhật DB
4. **WebSocket Hub** broadcast sự kiện `BATCH_CREATED` → Dashboard tự động refresh
5. **Telegram Bot** gửi thông báo đơn hàng mới kèm inline-button cho thợ xác nhận

---

## 🛠 Tech Stack

| Layer | Công nghệ |
|---|---|
| **Backend** | Python 3.9+, FastAPI, SQLAlchemy (Async), Uvicorn |
| **Frontend** | React 18 (Vite), CSS3 Variables, Phosphor Icons, Axios |
| **Database** | PostgreSQL 16 (Docker) — chuyển đổi qua `.env` |
| **AI** | Google Gemini 3.6 Flash (NLP) + Regex fallback |
| **Bot** | Python-Telegram-Bot v21+ (Async) |
| **DevOps** | Docker Compose |

---

## 📁 Cấu trúc dự án

```
pipelinegom/
├── README.md                   # Tài liệu dự án
├── requirements.txt            # Python dependencies
├── .env.example                # Template biến môi trường
├── .gitignore                  # Git ignore rules
├── docker-compose.yml          # PostgreSQL container (tùy chọn)
│
├── backend/                    # FastAPI Backend
│   ├── main.py                 # App chính — REST API + WebSocket + Lifespan
│   ├── config.py               # Đọc biến môi trường (.env)
│   ├── database.py             # SQLAlchemy models (Batch, StageLog) + engine
│   ├── schemas.py              # Pydantic request/response schemas
│   ├── workflow.py             # State machine — advance, rework, flag_issue
│   ├── worker.py               # Async queue worker — xử lý đơn hàng nền
│   ├── ai_agent.py             # AI Agent — Gemini parser + regex fallback
│   └── telegram_bot.py         # Telegram Bot — thông báo + inline callback
│
└── frontend/                   # React Frontend
    ├── index.html              # HTML entry point
    ├── package.json            # Node.js dependencies
    ├── vite.config.js          # Vite config (proxy API → backend)
    └── src/
        ├── main.jsx            # React entry point
        ├── App.jsx             # App chính — layout + state management
        ├── App.css             # App-level styles
        ├── index.css           # Design system — CSS variables + components
        ├── components/
        │   ├── KanbanBoard.jsx # Board Kanban 7 cột công đoạn
        │   ├── BatchCard.jsx   # Card hiển thị thông tin mẻ gốm
        │   ├── OrderForm.jsx   # Form nhập đơn hàng mới
        │   ├── ActivityLog.jsx # Bảng lịch sử hoạt động
        │   ├── StatsBar.jsx    # Thanh thống kê tổng quan
        │   └── Notifications.jsx # Toast notifications
        └── hooks/
            └── useWebSocket.js # Hook kết nối WebSocket real-time
```

---

## 🗺 Quy Trình 6 Bước Liên Hoàn (State Machine)

Toàn bộ các mẻ (Batch) bắt buộc đi theo đường ống một chiều (tuyến tính), trừ khi thực hiện **Tách mẻ / Rework**:

```
FORMING → DRYING → PAINTING → GLAZING → FIRING → QC → COMPLETED
  🏺        ☀️        🎨         ✨        🔥       ✅       📦
```

| # | Stage | Tên tiếng Việt | Mô tả |
|---|---|---|---|
| 1 | `FORMING` | Tạo hình mộc | Nặn, chuốt, tạo khuôn sản phẩm thô |
| 2 | `DRYING` | Phơi sấy & Sửa mộc | Phơi khô tự nhiên hoặc sấy, sửa lại bề mặt |
| 3 | `PAINTING` | Vẽ họa tiết | Vẽ tay hoặc in hoa văn lên mộc |
| 4 | `GLAZING` | Tráng men | Nhúng hoặc phun men lên sản phẩm |
| 5 | `FIRING` | Vào lò nung | Nung ở nhiệt độ phù hợp (900–1280°C) |
| 6 | `QC` | Kiểm định & Đóng gói | Kiểm tra chất lượng, phân loại, đóng gói |
| 7 | `COMPLETED` | Hoàn thành | Kết thúc vòng đời sản phẩm |

> **Rework:** Khi phát hiện lỗi, có thể tách một phần hoặc toàn bộ mẻ quay về công đoạn trước (tối đa 2 lần/mẻ con).

---

## 🚀 Cài Đặt & Khởi Chạy

### Yêu cầu hệ thống

- **Python** 3.9+
- **Node.js** 18+
- **Docker** & **Docker Compose** — chạy PostgreSQL

### 1. Clone & cấu hình môi trường

```bash
git clone https://github.com/HungRed1303/gompipeline.git
cd gompipeline

# Tạo file .env từ template
cp .env.example .env
```

Mở file `.env` và điền thông tin:

```env
# Google Gemini API (https://aistudio.google.com/app/apikey)
GEMINI_API_KEY="AIzaSy..."

# Telegram Bot (lấy từ @BotFather)
TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
TELEGRAM_CHAT_ID="-100XXXXXXX"

# Database — PostgreSQL (qua Docker)
DATABASE_URL="postgresql+asyncpg://gom:gom123@localhost:5432/gom_pipeline"
```

### 2. Khởi động PostgreSQL (Docker)

```bash
docker compose up -d
```

> Container `gom_postgres` sẽ tự tạo database `gom_pipeline` với user `gom` / password `gom123` trên port `5432`.

### 3. Chạy Backend (FastAPI)

```bash
# Cài dependencies (file requirements.txt ở thư mục gốc)
pip install -r requirements.txt

# Khởi động server
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

> 📖 Swagger UI (Tài liệu API tương tác) có sẵn tại: `http://localhost:8000/docs`
>
> Database tự động tạo bảng khi backend khởi động lần đầu (qua `init_db()`).

### 4. Chạy Frontend (React)

```bash
cd frontend
npm install
npm run dev
```

> 🌐 Truy cập Dashboard tại: `http://localhost:5173`

---

## 📡 API Endpoints

| Method | Endpoint | Mô tả |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `POST` | `/api/orders` | Tạo đơn hàng mới (trả 202, xử lý nền) |
| `GET` | `/api/batches` | Danh sách tất cả mẻ gốm |
| `GET` | `/api/batches/{id}` | Chi tiết 1 mẻ gốm |
| `POST` | `/api/batches/{id}/advance` | Chuyển sang công đoạn tiếp theo |
| `POST` | `/api/batches/{id}/issue` | Báo sự cố |
| `POST` | `/api/batches/{id}/rework` | Tách mẻ / rework về công đoạn trước |
| `GET` | `/api/logs` | Lịch sử hoạt động (có filter) |
| `WS` | `/ws` | WebSocket real-time updates |

---

*GOM Pipeline — Chuyển đổi số sản xuất thực dụng.* 🏺
