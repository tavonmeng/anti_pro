import os
import re

files_to_update = [
    "cursor_sh/src/views/Login.vue",
    "cursor_sh/src/views/AdminLogin.vue",
    "cursor_sh/src/views/Register.vue"
]

NEW_STYLE = """
<style lang="scss" scoped>
.minimal-background {
  position: absolute;
  top: 0; left: 0; right: 0; bottom: 0;
  background-color: #000;
  z-index: 1;
}

div[class$="-container"] {
  width: 100%;
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: #000;
  font-family: 'Outfit', 'PingFang SC', sans-serif;
  color: #fff;
}

div[class$="-wrapper"] {
  position: relative;
  z-index: 10;
  width: 90%;
  max-width: 480px;
  background: #000;
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.5);
  overflow: hidden;
}

div[class$="-content"] {
  padding: 50px 40px;
}

div[class$="-header"] {
  text-align: center;
  margin-bottom: 40px;
}

.logo-icon, .lock-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border-radius: 50%;
  color: #000;
}

.logo-svg {
  width: 36px;
  height: 36px;
  stroke: #000 !important;
}
.logo-svg circle, .logo-svg path {
  stroke: #000 !important;
}

h1[class$="-title"] {
  font-size: 32px;
  font-weight: 800;
  color: #fff;
  margin: 0 0 8px 0;
  letter-spacing: 1px;
  background: none;
  -webkit-text-fill-color: #fff;
}

p[class$="-subtitle"] {
  font-size: 14px;
  color: rgba(255, 255, 255, 0.6);
  margin: 0;
  letter-spacing: 1px;
}

.security-notice {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 16px;
  margin-top: 10px;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 20px;
  font-size: 12px;
  color: #fff;
}

form[class$="-form"] {
  width: 100%;
}

.input-wrapper {
  position: relative;
  width: 100%;
}

.tech-input, .admin-input {
  :deep(.el-input__wrapper) {
    background: transparent;
    border: none;
    border-bottom: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 0;
    box-shadow: none !important;
    padding: 0 10px;
    transition: all 0.3s ease;
    
    &:hover, &.is-focus {
      border-bottom-color: #fff;
    }
  }
  
  :deep(.el-input__inner) {
    color: #fff;
    height: 48px;
    font-size: 16px;
    &::placeholder {
      color: rgba(255, 255, 255, 0.3);
      font-weight: 300;
    }
  }
}

.input-icon {
  color: #fff;
  font-size: 18px;
  opacity: 0.7;
}

.input-border {
  display: none;
}

button[class$="-button"] {
  width: 100%;
  height: 52px;
  font-size: 16px;
  font-weight: 600;
  background: #fff;
  border: none;
  border-radius: 60px;
  color: #000;
  transition: transform 0.3s ease, background 0.3s ease;
  margin-top: 10px;
  
  &:hover {
    background: #e0e0e0;
    transform: translateY(-2px);
  }
  
  &:active {
    transform: translateY(0);
  }
}

.button-icon {
  margin-left: 8px;
  font-size: 18px;
}

div[class$="-footer"] {
  margin-top: 30px;
  text-align: center;
}

.footer-text, .security-tips, .back-link {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.4);
  margin: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.footer-link, .back-link .el-link {
  font-size: 14px;
  color: #fff;
  margin-left: 5px;
  text-decoration: underline;
  cursor: pointer;
  
  &:hover {
    color: #ccc;
  }
}

@media (max-width: 768px) {
  div[class$="-content"] {
    padding: 40px 30px;
  }
  h1[class$="-title"] {
    font-size: 28px;
  }
}
</style>
"""

def update_file(filepath):
    # Read original
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    
    # 1. Replace style block entirely
    # The regex matches <style lang="scss" scoped> ... </style>
    style_pattern = re.compile(r'<style lang="scss" scoped>.*?</style>', re.DOTALL)
    if style_pattern.search(content):
        content = style_pattern.sub(NEW_STYLE.strip(), content)
    
    # 2. Replace the HTML background structure
    # Because different files have different tech backgrounds, we use a generic removal script.
    # Replace the <div class="tech-background"> ... </div> with <div class="minimal-background"></div>
    bg_pattern = re.compile(r'<div class="tech-background">.*?</div>\s*</div>\s*<div class="tech-glow"></div>\s*</div>', re.DOTALL)
    content = bg_pattern.sub('<div class="minimal-background"></div>', content)
    
    # Alternatively for simpler substitution without strict DOTALL match (because div nesting):
    # Let's just find <div class="tech-background"> and replace it up to <div class="xxx-wrapper">
    wrapper_match = re.search(r'<div class="([a-z-]+)-wrapper">', content)
    if wrapper_match:
        wrapper_tag = wrapper_match.group(0)
        content = re.sub(r'<div class="tech-background">.*?' + wrapper_tag, r'<div class="minimal-background"></div>\n\n    ' + wrapper_tag, content, flags=re.DOTALL)
    
    # 3. Remove gradient definition from SVGs to make it pure black/white compatible
    content = re.sub(r'<defs>.*?</defs>', '', content, flags=re.DOTALL)
    content = re.sub(r'stroke="url\(#gradient\)"', 'stroke="#000"', content)
    
    # 4. Strip out any getParticleStyle reference from script setup
    content = re.sub(r'const getParticleStyle[\s\S]*?return \{[\s\S]*?\}\n\}', '', content)

    # 5. Fix Login.vue specifically
    if 'Login.vue' in filepath:
        content = content.replace('      <div class="tech-glow"></div>\n    </div>', '')
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Updated {filepath}")

for fp in files_to_update:
    if os.path.exists(fp):
        update_file(fp)
    else:
        print(f"File not found: {fp}")
