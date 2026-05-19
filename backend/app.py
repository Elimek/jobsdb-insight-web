"""
JobsDB Insight Backend v3 - FastAPI Server
Accepts user-provided sol_id token from any browser.
"""
import os, sys, json, asyncio, uvicorn
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

# ─── Config ──────────────────────────────────────────────────────────────────
GRAPHQL_URL = "https://hk.jobsdb.com/graphql"
TOKEN_FILE = os.path.join(os.path.dirname(__file__), ".jobsdb_token.json")
TOKEN_FROM_ENV = os.environ.get("JOBSDB_TOKEN")

# ─── Token helpers ───────────────────────────────────────────────────────────

def load_file_token():
    """Load token saved via --init."""
    if TOKEN_FROM_ENV:
        return json.loads(TOKEN_FROM_ENV)
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE) as f:
            return json.load(f)
    return None

def make_jar(token):
    """Build cookie jar from either a raw sol_id string or structured token."""
    jar = requests.cookies.RequestsCookieJar()
    if isinstance(token, str):
        # Raw sol_id value from user
        jar.set('sol_id', token, domain='.seek.com', path='/')
        jar.set('sol_id', token, domain='.jobsdb.com', path='/')
    elif isinstance(token, dict):
        if 'sol_id' in token:
            t = token['sol_id']
            jar.set('sol_id', t['value'], domain=t.get('domain', '.seek.com'), path='/')
        if 'jobseeker_session' in token:
            t = token['jobseeker_session']
            jar.set('JobseekerSessionId', t['value'], domain=t.get('domain', '.jobsdb.com'), path='/')
    return jar

GQL_QUERY = """query { jobDetails(id: "%s") { insights { __typename ... on ApplicantCount { count } ... on ApplicantsWithResumePercentage { percentage } ... on ApplicantsWithCoverLetterPercentage { percentage } } job { id title advertiser { name } } } }"""

HEADERS = {'User-Agent': 'Mozilla/5.0', 'Content-Type': 'application/json',
           'Origin': 'https://hk.jobsdb.com', 'Referer': 'https://hk.jobsdb.com/'}

def query_graphql(job_id, jar):
    """Execute GraphQL query with given cookie jar."""
    gql = GQL_QUERY % job_id
    r = requests.post(GRAPHQL_URL, data=json.dumps({"query": gql}), cookies=jar, headers=HEADERS, timeout=15)
    data = r.json()
    
    if 'errors' in data:
        msg = data['errors'][0].get('message', '')
        if 'UNAUTHENTICATED' in msg or 'Not Authorized' in msg:
            raise HTTPException(401, 'Token 无效或已过期，请重新获取 sol_id')
        raise HTTPException(502, f'JobsDB API error: {msg}')
    
    jd = data.get('data', {}).get('jobDetails')
    if not jd or 'insights' not in jd:
        return None
    
    result = {'id': job_id}
    for ins in jd['insights']:
        t = ins.get('__typename', '')
        if t == 'ApplicantCount': result['applicants'] = ins.get('count')
        elif t == 'ApplicantsWithResumePercentage': result['resume_pct'] = ins.get('percentage')
        elif t == 'ApplicantsWithCoverLetterPercentage': result['cover_pct'] = ins.get('percentage')
    ji = jd.get('job') or {}
    result['title'] = ji.get('title')
    result['company'] = (ji.get('advertiser') or {}).get('name')
    return result


# ─── FastAPI ─────────────────────────────────────────────────────────────────

app = FastAPI(title="JobsDB Insight API", version="3.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class GQLRequest(BaseModel):
    query: str
    token: str = None

@app.post("/api/gql")
def proxy_gql(req: GQLRequest):
    """
    Universal endpoint: frontend sends GraphQL query + user's sol_id token.
    Token can be omitted if server has one configured via --init or env.
    """
    token_str = req.token or os.environ.get('JOBSDB_SOL_ID')
    if not token_str:
        # Fallback: try loaded token
        loaded = load_file_token()
        if loaded:
            jar = make_jar(loaded)
        else:
            raise HTTPException(401, '需要 sol_id token。请登录 JobsDB → F12 → Application → Cookies → 复制 sol_id')
    else:
        jar = make_jar(token_str)
    
    r = requests.post(GRAPHQL_URL, data=json.dumps({"query": req.query}), cookies=jar, headers=HEADERS, timeout=15)
    return r.json()


@app.get("/api/job")
def query_job(id: str = Query(...)):
    """Legacy: single job query using server token."""
    loaded = load_file_token()
    if not loaded:
        raise HTTPException(401, '服务器未配置 token。请使用 POST /api/gql 传入你的 sol_id')
    result = query_graphql(id, make_jar(loaded))
    if result is None:
        return {"id": id, "applicants": None, "resume_pct": None, "cover_pct": None}
    return result


@app.get("/api/batch")
def query_batch(ids: str = Query(...)):
    """Legacy: batch query using server token."""
    loaded = load_file_token()
    if not loaded:
        raise HTTPException(401, '服务器未配置 token')
    results = []
    for jid in [i.strip() for i in ids.split(',') if i.strip()]:
        try:
            results.append(query_graphql(jid, make_jar(loaded)))
        except HTTPException as e:
            results.append({"id": jid, "error": e.detail})
    return results


@app.get("/health")
def health():
    """Server health check."""
    has_server_token = load_file_token() is not None or bool(os.environ.get('JOBSDB_SOL_ID'))
    return {
        "status": "ok",
        "version": "3.0.0",
        "server_token": has_server_token,
        "mode": "universal"  # Accepts user-provided tokens from any browser
    }


# ─── CLI ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    if '--init' in sys.argv:
        print("[*] Extracting sol_id from Brave...")
        from playwright.async_api import async_playwright
        BRAVE_EXE = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
        BRAVE_PROFILE = r"C:\Users\Elimek\AppData\Local\BraveSoftware\Brave-Browser\User Data"
        async def _extract():
            async with async_playwright() as p:
                ctx = await p.chromium.launch_persistent_context(BRAVE_PROFILE, executable_path=BRAVE_EXE, headless=True, args=['--no-sandbox'])
                page = await ctx.new_page()
                await page.goto("https://hk.jobsdb.com/", wait_until='domcontentloaded', timeout=15000)
                await asyncio.sleep(1)
                token, session = None, None
                for c in await ctx.cookies():
                    if c['name'] == 'sol_id': token = c['value']
                    elif c['name'] == 'JobseekerSessionId': session = c['value']
                await ctx.close()
                return token, session
        token, session = asyncio.run(_extract())
        if token:
            with open(TOKEN_FILE, 'w') as f:
                json.dump({"sol_id": {"value": token, "domain": ".seek.com"}, "jobseeker_session": {"value": session, "domain": ".jobsdb.com"}}, f, indent=2)
            print(f"  ✅ Token saved. sol_id={token}")
        else:
            print("  ❌ Failed to extract token. Is Brave logged in to JobsDB?")
    else:
        port = int(os.environ.get("PORT", 8899))
        uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
