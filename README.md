# 🌍 Country Info API

## Description:
- A Flask-based REST API that fetches data from external sources, 
processes it, stores it in MySQL, and provides endpoints for querying, refreshing, and visualizing country data.

## 🚀 Features

- Auto-fetch countries and exchange rates from external APIs

- Store or update countries in MySQL

- Case-insensitive search and filters

- Global refresh timestamp tracking

- Summary image generation (top GDP countries)

- Clean JSON error handling and validation

## 🧱 Tech Stack
- Flask Framework
- SQLAlchemy (ORM)
- MySQL (Database)
Requests (HTTP calls)
- Matplotlib (Summary image generation)

## ⚙️ Setup
### 1️⃣ Clone the repository
  - git clone https://github.com/yourusername/country-info-api.git
  - cd country-info-api

### 2️⃣ Create .env file
  - To set your MySQL credentials

### 3️⃣ Install dependencies
  - pip install -r requirements.txt

### 4️⃣ Run the server
  - python app.py

  - Server runs at
  👉 http://127.0.0.1:5000

## 🧩 API Endpoints
### 🔹 POST /countries/refresh
  - Fetches all countries from external APIs, calculates estimated GDP, and updates or inserts them in the database.

  - Updates global last_refreshed_at timestamp

  - Regenerates cache/summary.png with top 5 GDP countries

### 🔹 GET /countries
  - Query the database for countries by region or population.

### 🔹 GET /countries/image

  - Returns the generated summary image showing:
    - Total number of countries
    - Top 5 by estimated GDP
    - Last refresh timestamp
    - Saved at 👉 cache/summary.png

  ## 🧠 Notes
  - _You can switch from SQLite (for local testing) to MySQL for production._



