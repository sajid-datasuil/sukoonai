import yaml, time
from fastapi import Request
from fastapi.responses import JSONResponse
with open("configs/plan_meter.yaml","r",encoding="utf-8") as f:
    CFG = yaml.safe_load(f)
def _cap(plan:str)->int:
    try: return int(CFG.get("plans",{}).get(plan,{}).get("minutes_cap",15))
    except: return 15
_USAGE={}
async def gate(request:Request, call_next):
    user_id = request.headers.get("X-User-Id","anon")
    plan = request.headers.get("X-Plan","Free")
    today = time.strftime("%Y%m%d")
    used = int(_USAGE.get((user_id,today),0)); capm = _cap(plan)
    if used >= capm:
        return JSONResponse({"ok":True,"route":"abstain","answer":f"Plan cap reached for {plan}. Please upgrade to continue today.","abstain":True,"overage":{"user":user_id,"plan":plan,"cap_minutes":capm,"day":today}}, status_code=200)
    resp = await call_next(request); _USAGE[(user_id,today)] = used + 1; return resp
