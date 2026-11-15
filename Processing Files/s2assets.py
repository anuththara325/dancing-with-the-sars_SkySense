import sys, json, subprocess
date, d1 = sys.argv[1], sys.argv[2]
body = json.dumps({"collections":["sentinel-2-l2a"],"bbox":[80.45,5.9,80.75,6.1],"datetime":f"{date}T00:00:00Z/{d1}T00:00:00Z","limit":5})
out = subprocess.run(["curl","-s","-X","POST","https://earth-search.aws.element84.com/v1/search","-H","Content-Type: application/json","-d",body],capture_output=True,text=True).stdout
f = json.loads(out)["features"][0]
for k in ("visual","red","green","blue","scl","cloud","thumbnail"):
    a = f["assets"].get(k)
    if not a: print(k, "none"); continue
    code = subprocess.run(["curl","-sI","-o","/dev/null","-w","%{http_code}",a["href"]],capture_output=True,text=True).stdout
    print(k, code, a["href"])
