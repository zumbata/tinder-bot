from anticaptchaofficial.funcaptchaproxyon import funcaptchaProxyon

solver = funcaptchaProxyon()
solver.set_verbose(1)
solver.set_key("f101c33c0462c2ce8cb50436d9a09e6d")
solver.set_website_url("") #enter before starting
solver.set_website_key("") #enter before starting
solver.set_proxy_address("217.29.63.159")
solver.set_proxy_port(16494)
solver.set_proxy_login("Ng2Jzn")
solver.set_proxy_password("6cQ8oj")
solver.set_user_agent("Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36")

token = solver.solve_and_return_solution()
if token != 0:
    print(f"result token: {token}")
else:
    print(f"task finished with error {solver.error_code}")
