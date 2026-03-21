import os, glob

for file in glob.glob("cursor_sh/src/views/*.vue"):
    with open(file, "r") as f:
        c = f.read()

    # Make wrapper max-width narrower
    c = c.replace("max-width: 480px;", "max-width: 400px;")
    
    # Reduce content padding
    c = c.replace("padding: 50px 40px;", "padding: 32px 32px;")
    
    # Reduce header bottom margin
    c = c.replace("margin-bottom: 40px;", "margin-bottom: 24px;")
    
    # Reduce logo size
    c = c.replace("width: 64px;\n  height: 64px;\n  margin: 0 auto 20px;", "width: 56px;\n  height: 56px;\n  margin: 0 auto 16px;")
    
    # Reduce title size and margin
    c = c.replace("font-size: 32px;\n  font-weight: 800;\n  color: #fff;\n  margin: 0 0 8px 0;", "font-size: 26px;\n  font-weight: 800;\n  color: #fff;\n  margin: 0 0 4px 0;")
    
    # Reduce margin around security notice
    c = c.replace("margin-top: 10px;", "margin-top: 8px;")
    
    # Reduce input height
    c = c.replace("height: 48px;", "height: 44px;")
    
    # Force el-form-item margin smaller
    form_item_css = """
form[class$="-form"] {
  width: 100%;
  
  :deep(.el-form-item) {
    margin-bottom: 18px;
  }
}
"""
    c = c.replace("form[class$=\"-form\"] {\n  width: 100%;\n}", form_item_css.strip())
    
    # Make button smaller
    c = c.replace("height: 52px;", "height: 44px;")
    
    # Reduce footer top margin
    c = c.replace("margin-top: 30px;", "margin-top: 20px;")
    
    with open(file, "w") as f:
        f.write(c)
