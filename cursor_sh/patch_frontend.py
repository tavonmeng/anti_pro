import re

file_path = 'src/components/OrderConfirmationDialog.vue'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Change string '我已知晓' to '确认同意制作'
content = content.replace('我已知晓', '确认同意制作')


# Update handleConfirm to call verifySms
old_confirm = '''const handleConfirm = async () => {
  if (!confirmFormRef.value) return

  await confirmFormRef.value.validate(async (valid) => {
    if (valid) {
      confirming.value = true
      try {
        emit('confirm', {
          email: confirmForm.value.email,
          phone: confirmForm.value.phone
        })
      } finally {
        confirming.value = false
      }
    }
  })
}'''

new_confirm = '''const handleConfirm = async () => {
  if (!confirmFormRef.value) return

  await confirmFormRef.value.validate(async (valid) => {
    if (valid) {
      confirming.value = true
      try {
        // 请求后端校验验证码
        await authApi.verifySms(confirmForm.value.phone, confirmForm.value.smsCode)
        
        emit('confirm', {
          email: confirmForm.value.email,
          phone: confirmForm.value.phone
        })
      } catch (error: any) {
        ElMessage.error(error.message || '验证码错误或已过期')
      } finally {
        confirming.value = false
      }
    }
  })
}'''

if old_confirm in content:
    content = content.replace(old_confirm, new_confirm)
else:
    print("Warning: old handleConfirm not found, maybe slightly different formatting.")
    print("Fallback to regex replacement...")
    # fallback
    import re
    content = re.sub(
        r"confirming.value = true\s+try \{\s+emit\('confirm'",
        "confirming.value = true\n      try {\n        await authApi.verifySms(confirmForm.value.phone, confirmForm.value.smsCode)\n        emit('confirm'",
        content
    )
    content = re.sub(
        r"\}\s+finally\s+\{",
        "} catch (error: any) {\n        ElMessage.error(error.message || '验证码错误或已过期')\n      } finally {",
        content
    )

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Patch frontend ok")
