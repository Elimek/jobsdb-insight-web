"""
JobsDB Insight Backend - FastAPI server.
提取 token + 代理 GraphQL 查询 + Web API
"""
import os, sys, json, asyncio, uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import requests

# ─── Token 管理 ─────────────────────────────────────────────────────────────
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".jobsdb_token.json")
os.makedirs(os.path.dirname(TOKEN_FILE), exist_ok=True) if os.path.dirname(TOKEN_FILE) else None

GRAPHQL_URL = "https://hk.jobsdb.com/graphql"
TOKEN_FROM_ENV = os.environ.get("JOBSDB_TOKEN")

def load_token():
    """从文件或环境变量加载 token"""
    if TOKEN_FROM_ENV:
        return json.loads(TOKEN_FROM_ENV)
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None

def extract_token():
    """提取 token（需要 Brave 浏览器登录态）"""
    from playwright.async_api import async_playwright
    BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    BRAVE_PROFILE = r"C:\Users\Elimek\AppData\Local\BraveSoftware\Brave-Browser\User Data"
    
    async def _extract():
        async with async_playwright() as p:
            ctx = await p.chromium.launch_persistent_context(
                BRAVE_PROFILE, executable_path=BRAVE_EXE, headless=True, args=['--no-sandbox']
            )
            page = await ctx.new_page()
            await page.goto("https://hk.jobsdb.com/", wait_until='domcontentloaded', timeout=15000)
            await asyncio.sleep(1)
            cookies = await ctx.cookies()
            token = {}
            for c in cookies:
                if c['name'] == 'sol_id':
                    token['sol_id'] = {'value': c['value'], 'domain': c['domain']}
                elif c['name'] == 'JobseekerSessionId':
                    token['jobseeker_session'] = {'value': c['value'], 'domain': c['domain']}
            token['extracted_at'] = asyncio.run(asyncio.to_thread(lambda: __import__('datetime').datetime.now().isoformat()))
            await ctx.close()
            return token
    
    return asyncio.run(_extract())

# ─── FastAPI ─────────────────────────────────────────────────────────────────

app = FastAPI(title="JobsDB Insight API", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/job")
def query_job(id: str = Query(..., description="JobsDB job ID")):
    """查询单个岗位"""
    token = load_token()
    if not token:
        raise HTTPException(503, "No auth token. Run --init first or set JOBSDB_TOKEN env.")
    
    jar = requests.cookies.RequestsCookieJar()
    if 'sol_id' in token:
        t = token['sol_id']
        jar.set('sol_id', t['value'], domain=t.get('domain', '.seek.com'), path='/')
    if 'jobseeker_session' in token:
        t = token['jobseeker_session']
        jar.set('JobseekerSessionId', t['value'], domain=t.get('domain', '.jobsdb.com'), path='/')
    
    gql = """query { jobDetails(id: "%s") { insights { __typename ... on ApplicantCount { count } ... on ApplicantsWithResumePercentage { percentage } ... on ApplicantsWithCoverLetterPercentage { percentage } } job { id title advertiser { name } location { label } workTypes { label } } } }""" % id
    
    headers = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json',
               'Origin': 'https://hk.jobsdb.com', 'Referer': 'https://hk.jobsdb.com/'}
    
    try:
        r = requests.post(GRAPHQL_URL, data=json.dumps({"query": gql}), cookies=jar, headers=headers, timeout=15)
        data = r.json()
        
        if 'errors' in data:
            raise HTTPException(502, f"JobsDB API error: {data['errors'][0]['message']}")
        
        job_data = data.get('data', {}).get('jobDetails', {})
        if not job_data or 'insights' not in job_data:
            return {"id": id, "applicants": None, "resume_pct": None, "cover_pct": None, "title": None, "company": None}
        
        insights = job_data['insights']
        job_info = job_data.get('job', {}) or {}
        
        result = {"id": id}
        for ins in insights:
            t = ins.get('__typename', '')
            if t == 'ApplicantCount': result['applicants'] = ins.get('count')
            elif t == 'ApplicantsWithResumePercentage': result['resume_pct'] = ins.get('percentage')
            elif t == 'ApplicantsWithCoverLetterPercentage': result['cover_pct'] = ins.get('percentage')
        result['title'] = job_info.get('title')
        result['company'] = (job_info.get('advertiser', {}) or {}).get('name')
        return result
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/api/batch")
def query_batch(ids: str = Query(..., description="Comma-separated job IDs")):
    """批量查询"""
    job_ids = [i.strip() for i in ids.split(',') if i.strip()]
    results = []
    for jid in job_ids:
        try:
            results.append(query_job(id=jid))
        except HTTPException as e:
            results.append({"id": jid, "error": e.detail})
    return results


@app.get("/health")
def health():
    return {"status": "ok", "token": load_token() is not None}


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if '--init' in sys.argv:
        print("[*] Extracting token from Brave...")
        token = extract_token()
        with open(TOKEN_FILE, 'w') as f:
            json.dump(token, f, indent=2)
        print(f"  ✅ Token saved: sol_id={token.get('sol_id', {}).get('value', 'N/A')}")
    else:
        port = int(os.environ.get("PORT", 8899))
        uvicorn.run(app, host="0.0.0.0", port=port)
