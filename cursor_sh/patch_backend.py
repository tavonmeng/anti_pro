import re

auth_file = 'backend/app/api/auth.py'
with open(auth_file, 'r', encoding='utf-8') as f:
    content = f.read()

# Add VerifySmsRequest schema after SendSmsRequest if it's there, or just at the top of file after imports
if 'class VerifySmsRequest(BaseModel):' not in content:
    content = content.replace('from pydantic import BaseModel, EmailStr', 
                              'from pydantic import BaseModel, EmailStr\n\nclass VerifySmsRequest(BaseModel):\n    phone: str\n    code: str')

if 'from app.services.sms_service import send_sms_verify_code' in content and 'verify_sms_code' not in content:
    content = content.replace('send_sms_verify_code', 'send_sms_verify_code, verify_sms_code')

if '@router.post("/verify-sms"' not in content:
    # insert before @router.post("/register"
    new_route = '''
@router.post("/verify-sms", response_model=ApiResponse[bool])
async def api_verify_sms(data: VerifySmsRequest):
    """验证短信验证码"""
    is_valid = await verify_sms_code(data.phone, data.code)
    if not is_valid:
        raise HTTPException(status_code=400, detail="验证码错误或已过期")
    return ApiResponse(code=200, message="验证成功", data=True)

'''
    content = content.replace('@router.post("/register"', new_route + '@router.post("/register"')

with open(auth_file, 'w', encoding='utf-8') as f:
    f.write(content)
print("Patch backend ok")
