import os, random, time, threading, math
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
load_dotenv()
app=FastAPI(title='MarketLens')
IST=ZoneInfo('Asia/Kolkata')
STOCKS=[('RELIANCE','Reliance Industries','2885',2954.6),('TCS','Tata Consultancy Services','11536',4128.5),('HDFCBANK','HDFC Bank','1333',1684.2),('INFY','Infosys','1594',1892.4),('SBIN','State Bank of India','3045',812.7),('ICICIBANK','ICICI Bank','4963',1276.5)]
INTERVALS={'1m':('ONE_MINUTE',1,3),'5m':('FIVE_MINUTE',5,7),'15m':('FIFTEEN_MINUTE',15,20),'1h':('ONE_HOUR',60,60),'1d':('ONE_DAY',1440,200)}
MODE=os.getenv('MARKET_MODE','demo')
lock=threading.RLock(); client=None; session_day=None; cache={}
def broker():
    global client,session_day
    today=datetime.now(IST).date()
    if client is None or session_day!=today:
        from SmartApi import SmartConnect
        import pyotp
        if not all(os.getenv(k) for k in ['ANGEL_API_KEY','ANGEL_CLIENT_CODE','ANGEL_PIN','ANGEL_TOTP_SECRET']): raise HTTPException(503,'Fill in Angel One credentials in .env and restart.')
        obj=SmartConnect(api_key=os.environ['ANGEL_API_KEY'],timeout=15)
        try: result=obj.generateSession(os.environ['ANGEL_CLIENT_CODE'],os.environ['ANGEL_PIN'],pyotp.TOTP(os.environ['ANGEL_TOTP_SECRET']).now())
        except Exception: raise HTTPException(502,'Angel One login failed. Check your credentials and connection.')
        if not result or not result.get('status'): raise HTTPException(502,'Angel One rejected login. Check PIN and TOTP secret.')
        client,session_day=obj,today
    return client

def checked(result):
    global client
    if not result or not result.get('status'):
        client=None
        raise HTTPException(502,'Angel One request failed. Check API permissions, session and rate limits.')
    return result.get('data')

@app.get('/api/status')
def status(): return {'mode':MODE,'refresh_seconds':5}
@app.get('/api/quotes')
def quotes():
    with lock:
        if MODE!='live': return [{'symbol':s,'name':n,'price':round(p*(1+0.0003*math.sin(time.time()/15+i)),2),'change':round((i%3-0.7)*0.83,2)} for i,(s,n,t,p) in enumerate(STOCKS)]
        if time.time()-cache.get('quotes_time',0)<5: return cache['quotes']
        try: data=checked(broker().getMarketData('FULL',{'NSE':[s[2] for s in STOCKS]})) or {}
        except HTTPException: raise
        except Exception: raise HTTPException(502,'Could not fetch Angel One prices.')
        by_token={str(q['symbolToken']):q for q in data.get('fetched',[])}
        out=[{'symbol':s,'name':n,'price':by_token[t]['ltp'],'change':by_token[t].get('percentChange',0)} for s,n,t,p in STOCKS if t in by_token]
        if not out: raise HTTPException(502,'Angel One returned no quotes.')
        cache.update(quotes=out,quotes_time=time.time()); return out
@app.get('/api/candles')
def candles(symbol:str='RELIANCE',interval:str='5m'):
    stock=next((s for s in STOCKS if s[0]==symbol),None)
    if not stock or interval not in INTERVALS: raise HTTPException(400,'Unsupported symbol or interval')
    code,minutes,days=INTERVALS[interval]
    if MODE!='live':
        rng=random.Random(symbol+interval); price=stock[3]*0.985; out=[]; end=int(time.time()//(minutes*60))*minutes*60
        for i in range(100):
            o=price; price=max(1,price+rng.uniform(-0.002,0.0025)*stock[3])
            out.append({'time':end-(99-i)*minutes*60,'open':o,'high':max(o,price)+rng.random()*stock[3]*0.001,'low':min(o,price)-rng.random()*stock[3]*0.001,'close':price,'volume':rng.randint(1000,90000)})
        return out
    with lock:
        key=(symbol,interval)
        if key in cache and time.time()-cache[key][0]<30: return cache[key][1]
        now=datetime.now(IST)
        params={'exchange':'NSE','symboltoken':stock[2],'interval':code,'fromdate':(now-timedelta(days=days)).strftime('%Y-%m-%d %H:%M'),'todate':now.strftime('%Y-%m-%d %H:%M')}
        try: rows=checked(broker().getCandleData(params)) or []
        except HTTPException: raise
        except Exception: raise HTTPException(502,'Could not fetch Angel One candle history.')
        out=[]
        for r in rows:
            dt=datetime.fromisoformat(r[0]); dt=dt.replace(tzinfo=IST) if dt.tzinfo is None else dt
            out.append(dict(zip(['time','open','high','low','close','volume'],[int(dt.timestamp()),*r[1:6]])))
        out=sorted({r['time']:r for r in out}.values(),key=lambda x:x['time'])[-160:]
        cache[key]=(time.time(),out); return out
app.mount('/',StaticFiles(directory=Path(__file__).resolve().parents[1]/'dist',html=True),name='frontend')
