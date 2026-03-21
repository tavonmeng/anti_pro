import os, glob

for file in glob.glob("cursor_sh/src/views/*.vue"):
    with open(file, "r") as f:
        c = f.read()

    # further reduce el-form-item margin, use important to override el-plus defaults
    c = c.replace("margin-bottom: 18px;", "margin-bottom: 10px !important;")
    
    # ensure button margin-top is zero (was margin-top: 10px;)
    c = c.replace("margin-top: 10px;", "margin-top: 2px;")
    
    with open(file, "w") as f:
        f.write(c)
