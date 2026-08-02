from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import yfinance as yf
import requests
import pandas as pd
from datetime import datetime

app = FastAPI()

# 允許前端跨域請求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# 開源參議員交易資料庫 URL
SENATE_URL = "https://senate-stock-watcher-data.s3-us-west-2.amazonaws.com/aggregate/all_transactions.json"

@app.get("/api/market/{ticker}")
def get_market_data(ticker: str):
    """獲取指定標的 (如 AAPL, XAUUSD=X) 的 K 線資料"""
    try:
        stock = yf.Ticker(ticker)
        hist = stock.history(period="1y")
        
        data = []
        for index, row in hist.iterrows():
            data.append({
                "time": index.strftime('%Y-%m-%d'),
                "open": round(row['Open'], 2),
                "high": round(row['High'], 2),
                "low": round(row['Low'], 2),
                "close": round(row['Close'], 2)
            })
        return {"status": "success", "data": data}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/trades/{ticker}")
def get_senate_trades(ticker: str):
    """獲取指定股票的參議員交易紀錄，並轉換為圖表 Marker 格式"""
    try:
        response = requests.get(SENATE_URL)
        transactions = response.json()
        
        markers = []
        for t in transactions:
            if t.get('ticker') == ticker:
                # 判斷買賣方向以決定標記顏色與形狀
                trade_type = t.get('type', '').lower()
                if 'purchase' in trade_type:
                    color = '#26a69a' # 綠色
                    position = 'belowBar'
                    shape = 'arrowUp'
                    text = f"買入 ({t.get('senator')})"
                else:
                    color = '#ef5350' # 紅色
                    position = 'aboveBar'
                    shape = 'arrowDown'
                    text = f"賣出 ({t.get('senator')})"
                
                # 將日期格式轉換為時間戳或 YYYY-MM-DD
                raw_date = t.get('transaction_date')
                if raw_date and len(raw_date.split('/')) == 3:
                    m, d, y = raw_date.split('/')
                    formatted_date = f"{y}-{m.zfill(2)}-{d.zfill(2)}"
                    
                    markers.append({
                        "time": formatted_date,
                        "position": position,
                        "color": color,
                        "shape": shape,
                        "text": text
                    })
        
        # 依照時間排序
        markers = sorted(markers, key=lambda x: x['time'])
        return {"status": "success", "data": markers}
    except Exception as e:
        return {"status": "error", "message": str(e)}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
