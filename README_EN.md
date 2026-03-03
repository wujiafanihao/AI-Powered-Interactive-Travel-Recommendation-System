# 🗺️ TravelAI — AI Interactive Travel Recommendation System Based on Hybrid Recommendation

> **Graduation Design Topic**: Design and Implementation of an AI Interactive Travel Recommendation System Based on Hybrid Recommendation
>
> **One-Sentence Introduction**: This is an intelligent travel recommendation website developed with Python + Vue. It can guess what scenic spots you like based on your historical behavior (collaborative filtering), recommend similar types based on the characteristics of the spots themselves (content-based recommendation), and has a built-in AI chat assistant. You can use natural language to say "I want to take my kids to play in Beijing", and the system will search for matching spots for you.

---

## 📑 Table of Contents

- [Project Introduction](#-project-introduction)
- [System Function List](#-system-function-list)
- [System Architecture Diagram](#-system-architecture-diagram)
- [Core Flowchart](#-core-flowchart)
- [Tech Stack](#-tech-stack)
- [Data Assets](#-data-assets)
- [Recommendation Algorithm Principles](#-recommendation-algorithm-principles)
- [AI Module Principles](#-ai-module-principles)
- [Pre-run Preparation](#-pre-run-preparation)
- [Deployment and Run Steps](#-deployment-and-run-steps)
- [API Interface List](#-api-interface-list)
- [Project Directory Structure Detail](#-project-directory-structure-detail)
- [FAQ](#-faq)

---

## 📖 Project Introduction

TravelAI is an intelligent recommendation system for travel users. It integrates a **three-route hybrid recommendation engine** (collaborative filtering + content-based recommendation + user-profile reranking), **hot/scenario fallback strategy**, and **LLM-based AI conversation**, forming a complete "recommendation + Q&A + feedback loop" travel service platform.

### Core Problems Solved by the System

1. **Information Overload**: With 33,174 scenic spot data points across the country, users cannot view them all. The system uses recommendation algorithms to help users filter out the most likely interesting spots from massive data.
2. **Cold Start**: What if newly registered users have no behavioral data? The system will "guess" user preferences using content-based recommendations according to the travel preferences filled out by users. As users use it more, recommendations become more accurate.
3. **Natural Interaction**: Traditional search can only input keywords. TravelAI has a built-in AI chat assistant. Users can describe their needs in natural language (such as "take the elderly to see maple leaves in Nanjing in autumn"), and the system automatically understands the intent and returns accurate results.

---

## ✅ System Function List

| Functional Module | Specific Functions | Implementation Status |
|---------|---------|:-------:|
| **User Authentication** | Registration, Login (JWT), get/update profile, profile-completion status check | ✅ |
| **Profile & Avatar** | Profile page, phone/bio/birthday fields, avatar upload (JPG/PNG ≤ 5MB), static file serving | ✅ |
| **Spot Exploration** | Spot list (pagination + city/rating filter), spot search, spot detail | ✅ |
| **Collection Management** | Collect/uncollect spots and view collection list | ✅ |
| **Spot Reviews** | Users can rate and comment on spots | ✅ |
| **Behavior Recording** | Automatically record browse/rate/collect/search behaviors | ✅ |
| **Collaborative Filtering** | "Users similar to you also liked" recommendations | ✅ |
| **Content-Based Recommendation** | Similar-spot recommendation from feature vectors | ✅ |
| **User-Profile Reranking** | 0-100 profile match score from city, season, interests, and historical preferences | ✅ |
| **Three-Route Hybrid Fusion** | Dynamic weighted fusion of CF + CB + Profile with city-priority bonus | ✅ |
| **Recommendation Feedback Loop** | Exposure/click/collect/rate feedback API for recommendation optimization | ✅ |
| **Scenario Recommendation** | 6 preset scenarios (family/senior/history/nature/photo/adventure) | ✅ |
| **Hot Recommendation (Fallback)** | High-rating fallback for sparse or empty candidate sets | ✅ |
| **AI Smart Conversation** | Multi-turn LLM chat with session history | ✅ |
| **Exclusive AI Guide** | Spot-specific AI guide drawer on spot detail page | ✅ |
| **RAG Knowledge Q&A** | Spot knowledge answering based on vector retrieval | ✅ |
| **Smart Search Assistant** | Natural language → structured conditions → SQL search cards | ✅ |
| **Intent Recognition** | Rule + LLM two-stage intent classification (search/qa/help/chat) | ✅ |
| **Frontend Interface** | Home, spot list/detail, AI chat, profile, collections, login/register | ✅ |

---

## 🏗️ System Architecture Diagram

This system adopts a classic **four-layer architecture**: Interaction Layer → Service Layer → Algorithm Layer → Data Layer, with clear interfaces communicating between layers.

```
┌─────────────────────────────────────────────────────────────────────┐
│                   🖥️ Interaction Layer (Vue 3 + Element Plus)       │
│                                                                     │
│   ┌──────────┬──────────┬───────────┬──────────┬────────────┐       │
│   │ Home Rec │ Spot Exp │ Spot Detail│ AI Chat │ My Collect │       │
│   │ Home.vue │ SpotList │ SpotDetail│ Chat.vue │Collections │       │
│   └──────────┴──────────┴───────────┴──────────┴────────────┘       │
│                                                                     │
│   Tech: Vue 3 + Vite + Element Plus + Pinia + Axios                 │
└───────────────────────────┬─────────────────────────────────────────┘
                            │ HTTP REST API (JSON)
                            │ Port: Backend 8000 → Frontend 5173
┌───────────────────────────┼─────────────────────────────────────────┐
│  ⚙️ Service Layer (FastAPI) ▼                                       │
│                                                                     │
│   ┌──────────┬──────────┬───────────┬──────────┐                    │
│   │ User Auth│ Spot Svc │ Recomm Svc│ AI Chat  │                    │
│   │ auth.py  │ spots.py │recommend  │ chat.py  │                    │
│   │          │          │   .py     │          │                    │
│   └──────────┴──────────┴───────────┴──────────┘                    │
│                                                                     │
│   Tech: FastAPI + JWT(python-jose) + bcrypt + Pydantic              │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────────┐
│  🧠 Algorithm Layer        ▼                                        │
│                                                                     │
│   ┌───────────────┬─────────────────┬─────────────────────┐        │
│   │ Collab Filter │ Content Recomm  │ Hybrid Strategy     │        │
│   │ collaborative │ content_based   │ hybrid_recommender  │        │
│   │ _filter.py    │ .py             │ .py                 │        │
│   └───────────────┴─────────────────┴─────────────────────┘        │
│   ┌───────────────┬─────────────────┬─────────────────────┐        │
│   │ LLM Client    │ RAG Engine      │ Intent Recognizer   │        │
│   │ llm_client.py │ rag_engine.py   │ intent_recognizer   │        │
│   │               │                 │ .py                 │        │
│   └───────────────┴─────────────────┴─────────────────────┘        │
│                                                                     │
│   Tech: LangChain + OpenAI API + scikit-learn + numpy               │
└───────────────────────────┬─────────────────────────────────────────┘
                            │
┌───────────────────────────┼─────────────────────────────────────────┐
│  💾 Data Layer             ▼                                        │
│                                                                     │
│   ┌────────────────┬──────────────────┬────────────────────┐       │
│   │  SQLite        │  ChromaDB        │  CSV Files         │       │
│   │  travel.db     │  chroma_db/      │  citydata/         │       │
│   │  (8 Tables)    │  (Vector DB)     │  (352 City CSVs)   │       │
│   │  ~57MB         │  ~4GB            │  ~33174 Spots      │       │
│   └────────────────┴──────────────────┴────────────────────┘       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 🔄 Core Flowchart

### 1. User Recommendation Flow

```
User visits home page
    │
    ▼
System determines user type
    │
    ├── New User (Behaviors < 5)
    │       │
    │       ▼
    │   100% Content Recommendation (based on preferences chosen at registration)
    │   + Hot Recommendation Fallback
    │
    ├── Growing User (5-20 behaviors)
    │       │
    │       ▼
    │   Content Recommendation mainly + gradually add Collaborative Filtering
    │   (CF weight grows linearly from 0 to 0.4)
    │
    └── Active User (> 20 behaviors)
            │
            ▼
        Collaborative Filtering 60% + Content Recommendation 40%
        ("People with similar taste to you also liked this")
            │
            ▼
    Fusion Scoring → Sorting → Top-N → Attach Recommendation Reason → Return to Frontend
```

### 2. AI Smart Conversation Flow

```
User sends message: "I want to take my kid to play in Beijing"
    │
    ▼
Intent Recognizer (Rule + LLM Double-layer judgment)
    │
    ├── Search Intent → Smart Search Assistant
    │       │
    │       ├── LLM Extracts Conditions → {"city":"Beijing","target_group":"Family"}
    │       ├── Build SQL Query → Search matching spots from DB
    │       └── LLM Generates Rec Text → Return Spot Cards + Rec Copy
    │
    ├── QA Intent → RAG Pipeline
    │       │
    │       ├── User Question → Vectorize (Qwen3-Embedding)
    │       ├── ChromaDB Retrieves Top-5 relevant docs
    │       ├── Assemble Prompt (System prompt + Reference material + User question)
    │       └── DeepSeek-V3.2 Generates Answer
    │
    ├── Help Intent → FAQ Knowledge Base
    │       └── Search FAQ → Generate user guide answer
    │
    └── Chat Intent → Direct Conversation
            └── DeepSeek free answer
```

---

## 🛠️ Tech Stack

### Backend (Python)

| Tech | Version | Purpose |
|------|---------|---------|
| Python | 3.10+ | Programming Language |
| FastAPI | 0.115.0 | Web API Framework, auto-generates Swagger docs |
| Uvicorn | 0.30.6 | ASGI Server, runs FastAPI |
| SQLite | Built-in | Relational Database (Lightweight, no installation) |
| ChromaDB | 0.6.3 | Vector Database (Stores document embeddings) |
| LangChain | 0.3.25 | LLM Application Development Framework |
| langchain-openai | 0.3.18 | OpenAI compatible interface for LangChain |
| OpenAI SDK | 1.82.0 | Calls ModelScope's embedding API |
| scikit-learn | 1.6.1 | Machine Learning Tool (Cosine similarity calculation) |
| NumPy | 2.2.6 | Numerical Calculation (Matrix operations) |
| Pandas | 2.2.3 | Data Processing (Reads CSV) |
| python-jose | 3.3.0 | JWT Token generation and verification |
| bcrypt | 4.2.1 | Password Encryption (bcrypt hash algorithm) |
| Pydantic | 2.11.3 | Data model validation |
| python-dotenv | 1.0.1 | Reads .env environment variables |

### Frontend (JavaScript/TypeScript)

| Tech | Version | Purpose |
|------|---------|---------|
| Vue 3 | 3.5.25 | Frontend UI Framework (Reactive+Componentized) |
| Vite | 8.0.0 | Frontend Build Tool (Ultra-fast HMR) |
| Element Plus | 2.13.3 | Vue 3 UI Component Library (Forms/Tables/Dialogs etc.) |
| Pinia | 3.0.4 | Vue 3 State Management (Stores login status) |
| Vue Router | 5.0.3 | Frontend Routing (Page navigation) |
| Axios | 1.13.6 | HTTP Request Library (Calls backend API) |
| marked | 17.0.3 | Markdown Rendering (Formats AI replies) |
| TypeScript | 5.9.3 | Type-safe JavaScript |

### AI Models (Provided by ModelScope)

| Model | Purpose | Note |
|-------|---------|------|
| **DeepSeek-V3.2** | Chat/QA/Intent Recognition/Condition Extraction | Large Language Model, responsible for "understanding" and "generating" text |
| **Qwen3-Embedding-8B** | Vector Embedding | Converts text into 4096-dimensional vectors for similarity retrieval |

---

## 📊 Data Assets

### 1. Scenic Spot Data (Real Data)

Data source is Qunar spot data, stored in the `citydata/` directory.

| Metric | Value |
|--------|-------|
| City CSV Files | **352 (Covering major cities in China)** |
| Total Spot Records | **33,174** |
| Data Source | Qunar (qunar.com) |
| Database Size | ~57MB (SQLite) |

Each spot contains the following 12 fields:

| Field | Description | Example |
|-------|-------------|---------|
| Name | Spot Chinese/English name | `故宫博物院The Palace Museum` |
| Link | Source URL | `http://travel.qunar.com/...` |
| Address | Address+Phone+Website | `北京市东城区景山前街4号` |
| Intro | Spot detailed description (RAG core) | Long text |
| Open Time | Operating hours | `全年 07:30-16:00` |
| Image Link | Spot image URL | Can be used for frontend display |
| Rating | User rating | `4.0`~`5.0` (Key field for CF) |
| Suggest Time| Suggested tour duration | `3小时 - 4小时` |
| Suggest Season| Best season to visit | `春季`, `四季皆宜` |
| Ticket | Price info | JSON format |
| Tips | Precautions (RAG content) | Long text |
| Page | Crawler page number | Ignored |

### 2. Mock User Data (Script Generated)

To make data available for the recommendation algorithms, the system automatically generates mock user data:

| Data Type | Quantity | Description |
|-----------|----------|-------------|
| Mock Users | **150** | Covers various age groups (18-70), activity levels |
| Behavior Records| **~15,000** | Browse(60%)/Rate(20%)/Collect(10%)/Search(10%) |
| Collect Records | **~1,600** | Approx. 140 users have collections, avg 11 per person |
| Rating Records | **~3,000** | Avg rating 3.55 (Right-skewed, high distribution, more realistic) |
| User Reviews | **~230,000** | 3-10 reviews per spot, ratings generated based on spot rating |
| Cold Start Users| **~30** | Behaviors < 5, specifically to test cold start scenarios |

### 3. Vector Knowledge Base (ChromaDB)

| Metric | Value |
|--------|-------|
| Spot Documents | **~16,750** (Spots with complete intros) |
| System FAQs | **15** |
| Embedding Dim | **4096** |
| Embedding Model| Qwen3-Embedding-8B |

### 4. Database Table Structure (10 Tables)

| Table Name | Purpose | Important Fields |
|------------|---------|------------------|
| `users` | User info | username, password_hash, age, gender, city, travel_style |
| `spots` | Spot info | name, city, rating, description, spot_type, target_group |
| `user_behaviors` | User behavior records | user_id, spot_id, behavior_type, rating, duration |
| `user_collections` | User collections | user_id, spot_id (Composite Unique) |
| `user_similarity` | CF similarity | user_id_a, user_id_b, similarity |
| `spot_features` | Spot feature vectors | spot_id, feature_vector(28-dim), feature_labels |
| `chat_history` | AI chat history | user_id, role, content, session_id |
| `spot_comments` | User reviews | user_id, spot_id, rating, content |
| `user_profiles` | Extended user profile | preferred_season, interest_tags, preferred_budget |
| `recommend_feedback` | Recommendation feedback events | event_type, event_value, context(JSON) |

---

## 🧮 Recommendation Algorithm Principles

### 1. Collaborative Filtering (`collaborative_filter.py`)

**Core Idea**: "People with similar taste to you like this, you will probably like it too."

```
Steps:
1. Build "User-Spot Rating Matrix" → Each user's rating for each spot
2. Use Cosine Similarity to calculate the similarity degree between any two users
3. Find K=20 most similar users (K-Nearest Neighbors)
4. Use weighted average to predict the current user's rating for unrated spots
5. Sort by predicted rating, recommend Top-N
```

**Formula**:

```
                    Σ (sim(u,v) × rating(v,i))
predicted(u,i) = ────────────────────────────────
                       Σ |sim(u,v)|
```

### 2. Content-Based Recommendation (`content_based.py`)

**Core Idea**: "What type of spots you liked before, recommend similar types to you."

```
Steps:
1. Extract attributes of each spot into a 28-dimensional feature vector:
   - Spot Type (8 dim): Natural Scenery/Historical Culture/Religious/...
   - Suitable Season (4 dim): Spring/Summer/Autumn/Winter
   - Geographic Region (7 dim): North China/East China/South China/...
   - Target Group (6 dim): Family/Senior/Couple/Student/Photo/Adventure
   - Numerical Features (3 dim): Rating/Tour Duration/Price
2. Average the feature vectors of spots the user has liked → get "User Preference Vector"
3. Calculate Cosine Similarity between all spots and the user preference vector
4. Sort by similarity, recommend Top-N
```

### 3. Hybrid Recommendation Fusion (`hybrid_recommender.py`)

**Core Idea**: Three-route dynamic fusion with user-profile reranking and city-priority enhancement.

```
Fusion Formula:
score(u, i) = w_CF × score_CF(u, i)
            + w_CB × score_CB(u, i)
            + w_Profile × score_Profile(u, i)
            + city_bonus

Where:
- score_Profile = match_score / 100.0
- city_bonus = 0.08 when user's city matches spot city
- w_CF + w_CB + w_Profile = 1.0

Weight Strategy:
- New User (< 5 behaviors):   w_CF=0.00, w_CB=0.30, w_Profile=0.70
- Growing User (5-20 beh):    w_CF grows 0→0.35, w_Profile decreases 0.60→0.25, remainder to w_CB
- Active User (> 20 beh):     w_CF=0.55, w_CB=0.20, w_Profile=0.25

Fallback Strategy:
- If candidate pool is insufficient, pad with hot recommendations
- Supports 6 scenario recommendations (Family/Senior/History/Nature/Photo/Adventure)
```

### 4. Recommendation Feedback Loop (`/recommend/feedback`)

The frontend reports recommendation events in real time:
- `exposure`: recommendation card appears in viewport
- `click`: user clicks a recommendation
- `collect`: user favorites a recommended spot
- `rate`: user rates a recommended spot

These events are stored in `recommend_feedback` and can be used to optimize ranking strategy and offline evaluation later.

---

## 🤖 AI Module Principles

### 1. RAG Retrieval-Augmented Generation (`rag_engine.py`)

```
User Question → Qwen3-Embedding-8B Vectorize
    → ChromaDB Retrieves Top-5 relevant spot docs
    → Assemble Prompt (System Prompt + Reference Material + Question)
    → DeepSeek-V3.2 Generate Answer
    → Return Answer + Reference Sources
```

Significance of RAG: Makes the AI's answer "verifiable", not fabricated, but based on real spot data.

### 2. Intent Recognition (`intent_recognizer.py`)

Adopts a **Rule + LLM Double-layer Recognition** strategy:

- **Layer 1 (Rule Match)**: Checks keywords. Over 80% of requests are judged here, fast, costs no API calls.
  - Contains "recommend/fun/want to go" → Search Intent
  - Contains "what time/ticket/address" → QA Intent
  - Contains "how to register/how to collect" → System Help Intent
  - Contains "hello/thanks" → Chat Intent

- **Layer 2 (LLM Judgment)**: When rules are uncertain, calls DeepSeek to judge.

### 3. Smart Search Assistant (`intent_recognizer.py` → `SmartSearcher`)

```
"Take the elderly to see maple leaves in Nanjing in autumn"
    → LLM Extracts Conditions → {"city":"Nanjing", "season":"Autumn", "target_group":"Senior", "keywords":["maple leaves"]}
    → Build SQL Query → WHERE city='Nanjing' AND suggest_season LIKE '%Autumn%' AND ...
    → Return matching spot list
```

---

## 🔑 Pre-run Preparation

### 1. Environment Requirements

| Software | Version Required | Purpose |
|----------|------------------|---------|
| Python | 3.10 and above | Run Backend |
| Node.js | 18 and above | Build Frontend |
| Conda (Rec) | Any | Python env isolation |
| Git | Any | Code Management |

### 2. Get ModelScope API Key (Important!)

This project uses free AI model APIs provided by **ModelScope (魔塔社区)**. You need to get an API Key first.

**Steps to get it:**

1. Open [ModelScope Website](https://modelscope.cn/)
2. Click **"Login/Register"** at the top right, register an account with mobile or Alipay
3. After logging in, click your avatar at top right → **"API-Key Management"**
4. Or visit directly: https://modelscope.cn/my/myapikey
5. Click **"Create API Key"**, copy the generated Key (format is `ms-xxxx...`)
6. Paste the Key into the `LLM_API_KEY` field in the `.env` file in the project root directory

**Two models used in this project:**

| Model Name | Purpose | Note |
|------------|---------|------|
| `deepseek-ai/DeepSeek-V3.2` | LLM (Chat/QA/Intent/Extraction) | Free |
| `Qwen/Qwen3-Embedding-8B` | Embedding (Text→Vector) | Free |

> ⚠️ **Note**: ModelScope's free tier has limits, completely sufficient for daily dev/test. If you hit a rate limit (429), just wait a moment and retry.

### 3. Configure `.env` File

There's already a `.env` file in the project root. You just need to **replace the API Key with your own**:

```env
# ============================================
# TravelAI - Env Config
# ============================================

# --- AI Model Config ---
LLM_BASE_URL=https://api-inference.modelscope.cn/v1/
LLM_API_KEY=YOUR_KEY_HERE               # ← Replace with your ModelScope API Key
LLM_MODEL_NAME=deepseek-ai/DeepSeek-V3.2
EMBEDDING_MODEL_NAME=Qwen/Qwen3-Embedding-8B

# --- Database Config ---
DATABASE_PATH=data/travel.db
CHROMA_DB_PATH=data/chroma_db

# --- JWT Config ---
JWT_SECRET_KEY=travelai-secret-key-2026-xianyu-graduation
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440

# --- App Config ---
APP_HOST=0.0.0.0
APP_PORT=8000
APP_DEBUG=true
```

---

## 🚀 Deployment and Run Steps

### Step 1: Create Conda Environment and Install Backend Dependencies

```bash
# 1. Create a Conda env named xianyu
conda create -n xianyu python=3.10 -y

# 2. Activate env
conda activate xianyu

# 3. Enter project root, install Python dependencies
cd /your/path/xianyu/1
pip install -r requirements.txt
```

### Step 2: Initialize Database and Import Data

```bash
# Enter backend directory
cd backend

# 1. Init DB (Create 8 tables)
python database.py

# 2. Import spot data (Import 352 CSVs from citydata to SQLite)
python scripts/import_citydata.py
# Output: ✅ Successfully imported 33174 spot records

# 3. Generate mock user data
python scripts/generate_mock_users.py
# Output: ✅ Data generation complete

# 4. Generate mock user reviews (~230,000 reviews)
python scripts/generate_mock_comments.py
# Output: ✅ Successfully generated X reviews
```

### Step 3: Compute Recommendation Models

```bash
# Still in backend directory

# 1. Compute CF similarity matrix
python algorithms/collaborative_filter.py
# Output: ✅ Computed 11026 pairs, 124 valid

# 2. Compute Content-based feature vectors
python algorithms/content_based.py
# Output: ✅ Computed 28-dim feature vectors for 33174 spots
```

### Step 4: Build Vector Knowledge Base (Optional, needed for AI Q&A)

> ⚠️ This step requires a valid ModelScope API Key and takes time (~30-60 mins depending on network), as it sends ~16,750 spot intros to the API.

```bash
# Build ChromaDB vector knowledge base
python scripts/build_vectors.py
# A progress bar will show, wait patiently
```

> 💡 **If skipped**: Recommendations will still work fine, but the "Spot Knowledge Q&A" feature in AI Chat will degrade to using the LLM's raw knowledge (without reference materials).

### Step 5: Start Backend Service

```bash
# In backend directory, start FastAPI backend
uvicorn main:app --host 0.0.0.0 --port 8000

# For Hot Reload (dev mode), add --reload:
# uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Upon success, you'll see:

```
🚀 TravelAI Backend Service Starting...
✅ Database initialization complete
✅ All initializations complete, service ready!
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open http://localhost:8000/docs in your browser to see the Swagger API Docs.

### Step 6: Start Frontend

```bash
# Open a new terminal window, enter frontend directory
cd frontend

# 1. Install frontend dependencies
npm install

# 2. Start dev server
npm run dev
```

Visit http://localhost:5173 in your browser to experience the system.

### Quick Verification Checklist

| Item | Method | Expected Result |
|------|--------|-----------------|
| Backend running? | Browser: `http://localhost:8000/` | See JSON welcome message |
| API Docs? | Browser: `http://localhost:8000/docs` | See Swagger Docs |
| Frontend running? | Browser: `http://localhost:5173` | See Home UI |
| Register Func | Register a new user on frontend | Success & auto-login |
| Spot List | Click "Explore Spots" | See paginated, filterable list |
| AI Chat | Enter AI Chat page, type "hello" | Receive AI reply |

---

## 📡 API Interface List

All interfaces are prefixed with `/api`. Full docs available at `http://localhost:8000/docs`.

### User Auth `/api/auth`

| Method | Path | Description | Auth |
|--------|------|-------------|:----:|
| POST | `/auth/register` | Register new user | ❌ |
| POST | `/auth/login` | Login to get Token | ❌ |
| GET | `/auth/me` | Get current user info | ✅ |
| PUT | `/auth/me` | Update profile fields | ✅ |
| GET | `/auth/me/profile-status` | Check profile completeness and first-login state | ✅ |
| POST | `/auth/avatar` | Upload avatar (JPG/PNG, ≤5MB) | ✅ |

### Spot Service `/api/spots`

| Method | Path | Description | Auth |
|--------|------|-------------|:----:|
| GET | `/spots` | Spot list (Pagination+Filter) | ❌ |
| GET | `/spots/cities` | Get all city list | ❌ |
| GET | `/spots/search?q=keyword` | Search spots | ❌ |
| GET | `/spots/{id}` | Get spot details | ❌ |

### Recommendation Service `/api/recommend`

| Method | Path | Description | Auth |
|--------|------|-------------|:----:|
| GET | `/recommend` | Get personalized recommendations (with strategy weights and match score) | ✅ |
| GET | `/recommend/scene/{scene}` | Scenario recommendations | ❌ |
| POST | `/recommend/behavior` | Record user behavior | ✅ |
| GET | `/recommend/collections` | Get user collections | ✅ |
| POST | `/recommend/collect/{id}` | Collect/Uncollect | ✅ |
| POST | `/recommend/feedback` | Record recommendation feedback (exposure/click/collect/rate) | ✅ |

### AI Chat `/api/chat`

| Method | Path | Description | Auth |
|--------|------|-------------|:----:|
| POST | `/chat` | Send message to AI assistant | ✅ |
| GET | `/chat/history` | Get chat history | ✅ |

---

## 📁 Project Directory Structure Detail

```
xianyu/1/
│
├── .env                     # 🔐 Env config file (API Key, DB paths)
├── README.md                # 📖 Project documentation (Chinese version)
├── README_EN.md             # 📖 Project documentation (English version)
├── requirements.txt         # 📦 Python dependencies
│
├── citydata/                # 🗂️ Raw spot data directory
│   ├── 北京.csv             # Spot data by city
│   └── ... (352 CSV files, 33,174 spots)
│
├── backend/                 # ⚙️ Python FastAPI Backend
│   │
│   ├── main.py              # 🚪 Backend entry file
│   │
│   ├── config.py            # ⚙️ Config management module
│   │
│   ├── database.py          # 💾 Database initialization module
│   │
│   ├── models/              # 📐 Pydantic data models
│   │   ├── __init__.py
│   │   └── user.py          #    Request/Response formats
│   │
│   ├── routers/             # 🛤️ API routing modules
│   │   ├── __init__.py
│   │   ├── auth.py          # 🔐 User authentication routes
│   │   ├── spots.py         # 🏔️ Spot routes
│   │   ├── recommend.py     # ⭐ Recommendation routes
│   │   └── chat.py          # 💬 AI chat routes
│   │
│   ├── algorithms/          # 🧮 Recommendation algorithm modules
│   │   ├── __init__.py
│   │   ├── collaborative_filter.py # 🤝 CF engine
│   │   ├── content_based.py        # 📊 Content-based engine
│   │   ├── hybrid_recommender.py   # 🔀 Three-route fusion engine (CF+CB+Profile)
│   │   └── user_profile_recommender.py # 👤 Profile match scoring engine
│   │
│   ├── ai/                  # 🤖 AI Intelligent modules
│   │   ├── __init__.py
│   │   ├── llm_client.py    # 🧠 LLM Client (ModelScope encapsulation)
│   │   ├── rag_engine.py    # 📚 RAG Retrieval Augmented Gen engine
│   │   └── intent_recognizer.py # 🎯 Intent recognition & Smart Search
│   │
│   ├── scripts/             # 🔧 Initialization scripts
│   │   ├── import_citydata.py         # 📥 Spot data import script
│   │   ├── generate_mock_users.py     # 👥 Mock user generation script
│   │   ├── generate_mock_comments.py  # 💬 Mock reviews generation script
│   │   └── build_vectors.py           # 🧬 Vector KB build script
│   │
│   ├── data/                # 💿 Data storage directory
│   │   ├── travel.db        #    SQLite database file (~57MB)
│   │   └── chroma_db/       #    ChromaDB vector database dir
│   │
│   └── tests/               # 🧪 Tests directory (reserved)
│
└── frontend/                # 🖥️ Vue 3 + Vite Frontend
    │
    ├── package.json         # 📦 Frontend dependency config
    ├── vite.config.ts       # ⚡ Vite build config
    ├── tsconfig.json        # TypeScript config
    ├── index.html           # HTML entry
    │
    └── src/                 # 📂 Frontend source code
        ├── main.ts          # 🚪 Vue app entry
        ├── App.vue          # 🏠 Root component
        ├── style.css        # 🎨 Global styles
        │
        ├── router/          # 🛤️ Frontend routing config
        │   └── index.ts
        │
        ├── store/           # 📦 Pinia user state management
        │   └── user.ts
        │
        ├── api/             # 📡 API request modules
        │   ├── index.ts
        │   ├── request.ts
        │   ├── spots.ts
        │   └── chat.ts
        │
        └── views/           # 📄 Page view components
            ├── Home.vue     # 🏠 Home
            ├── Login.vue    # 🔐 Login
            ├── Register.vue # 📝 Register
            ├── Collections.vue # ⭐️ My Collections
            ├── Spot/
            │   ├── SpotList.vue    # 📋 Spot List
            │   └── SpotDetail.vue  # 📖 Spot Detail (with reviews & AI Guide)
            └── AI/
                └── Chat.vue # 💬 AI Smart Chat (with history management)
```

---

## ❓ FAQ

### Q: What is the password for the mock users?

**A**: The password for all mock users (`user_001` ~ `user_150`) is **`password123`**. You can log in with these to test the recommendation features.

### Q: Vector building is too slow, what do I do?

**A**: `build_vectors.py` needs to call the ModelScope API to process ~16,750 data points. It takes about 30-60 mins depending on network. If you don't need the "knowledge-base QA" feature in AI chat, you can skip this step, recommendations won't be affected.

### Q: API Key gives 429 error?

**A**: 429 is a rate limit error. Wait 30 seconds and retry. The script has built-in auto-retry.

### Q: Frontend shows CORS error?

**A**: The backend is configured with `allow_origins=["*"]`. If issues persist, check if the backend is running properly (visit `http://localhost:8000/`).

### Q: Where is the SQLite database file?

**A**: Located at `backend/data/travel.db`, ~57MB. If you want to reinitialize, delete this file and redo "Step 2".

### Q: How to add my own spot data?

**A**: Add new CSV files in the `citydata/` directory (following existing format), then re-run `python scripts/import_citydata.py`.

### Q: Can I use `venv` instead of Conda?

**A**: Yes. Conda is just for isolating the Python environment. You can use `venv`:

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
# .venv\Scripts\activate   # Windows
pip install -r requirements.txt
```

### Q: How to deploy in production?

**A**:

```bash
# Backend
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4

# Frontend Build
cd frontend && npm run build
# Then host the dist/ directory using Nginx
```

---

## 📄 License

This project is a graduation design work, intended solely for academic exchange and learning purposes.