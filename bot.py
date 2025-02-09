import time, openpyxl, sys, requests, json, os, shutil, selenium, re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.command import Command
from anticaptchaofficial.funcaptchaproxyless import funcaptchaProxyless
from enum import Enum
from mega import Mega
import threading
from pyvirtualdisplay import Display

globals = {}
globals['AccountId'] = None
globals['AccountInfo'] = []
globals['AccountCoordinates'] = []
globals['DriverLocation'] = {}
globals['ChromeDriverLocation'] = {}
globals['MegaInstance'] = Mega()
globals['WorkingDir'] = os.getcwd() + "/"
globals['OrderId'] = None
globals['ActivationService'] = None
globals['Images'] = []

display = None
driver = None

ANTICAPTCHA = {}
ANTICAPTCHA['Key'] = 'f101c33c0462c2ce8cb50436d9a09e6d'

FIVESIMAPI = {}
FIVESIMAPI['Key'] = "eyJhbGciOiJSUzUxMiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2MTYyNjUwMDksImlhdCI6MTU4NDcyOTAwOSwicmF5IjoiZDE3YzIyN2U3YmQzYTk3Y2NkODkzYWI5ZjQwODNjMGMiLCJzdWIiOjMwODU3OH0.JtyzeAzHp6xdHo2hyTGGjWDtfW-dinSlhlLf5Cvw0OcENTGZFgMiNO_CzqWZDZadJgY_uOvgpyJsa42ce_-16tHkoY3v1IeYZwaUwGTdE9UlOE94qwV9G5af3ADVMEcRgeP_Zs26vfGrKaIweMGDNub_dsD6N23anJuJzk-QFjyvnUpIdbDNOQIMWsb-q3aqtOOmYVyjre4NxDjXEYQT13Cep6ZqTcYl_NDXJjd0cpBub-EzOxcOmcbhXAq23zOf8MyaEqoe7cH2xe6QtbdUGjih1VFqed2cAKHitwou1nYaJCuDDuWPe34kgkyOoOC0MxSadzQBalJqi_wpGcKs0A"
FIVESIMAPI['BuyActivation'] = "https://5sim.net/v1/user/buy/activation/%s/%s/%s"
FIVESIMAPI['CheckOrder'] = "https://5sim.net/v1/user/check/%s"

SMSPVAAPI = {}
SMSPVAAPI['Key'] = 'Kd85cDsKwkkat6YNYGSznilXH2G6qm'
SMSPVAAPI['Url'] = 'http://smspva.com/priemnik.php'

class RequestType(int):
    CheckOrder = 0
    BuyActivation = 1

class ActivationService(int):
    FiveSim = 0
    SmsPva = 1

class Columns(int):
    COORDINATES = 0
    TINDER_EMAIL = 1
    SMSPVA_EMAIL = 2
    SMSPVA_PASSWORD = 3
    MEGA_EMAIL = 4
    MEGA_PASSWORD = 5
    NAME = 6
    BIRTHDATE = 7
    TINDER_BIO = 8

def CaptchaSolver(url, publicKey):
    solver = funcaptchaProxyless()
    solver.set_verbose(1)
    solver.set_key(ANTICAPTCHA['Key'])
    solver.set_website_url(url)
    solver.set_website_key(publicKey)

    token = solver.solve_and_return_solution()
    if token != 0:
        print(" > Result token: "+token)
        return token
    else:
        print(" > Task finished with error "+solver.error_code)
        custom_exit()

def GetPublicKey():
    reCheck = r"([0-9a-zA-Z]{8}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{4}-[0-9a-zA-Z]{12})"
    matches = re.findall(reCheck, driver.page_source)
    if matches:
        pk = matches[0]
        print(f" > Found public key: {pk}")
        return pk
    else:
        print(" > Couldn't find public key.")
        custom_exit()

def safe_json(data):
    if data is None:
        return True
    elif isinstance(data, (bool, int, float)):
        return True
    elif isinstance(data, (tuple, list)):
        return all(safe_json(x) for x in data)
    elif isinstance(data, dict):
        return all(isinstance(k, str) and safe_json(v) for k, v in data.items())
    return False

def FiveSimApi(req: RequestType, *args):
    global globals
    headers = {"Authorization": f"Bearer {FIVESIMAPI['Key']}"}
    url = ""
    if req == RequestType.CheckOrder:
        url = FIVESIMAPI['CheckOrder'] % args[0]
    elif req == RequestType.BuyActivation:
        url = FIVESIMAPI['BuyActivation'] % (args[0], args[1], args[2])
    r = requests.get(url, headers=headers)
    try:
        data = json.loads(r.text)
    except:
        return False
    return data

def FiveSimBuyNumber():
        receivedPhone = False
        while receivedPhone == False:
            data = FiveSimApi(RequestType.BuyActivation, "usa", "any", "tinder")
            if data == False:
                print(" > There were no free phones, retrying...")
            else:
                globals['OrderId'] = data['id']
                receivedPhone = True

def FiveSimBuyActivation():
    FiveSimBuyNumber()
    response = FiveSimApi(RequestType.CheckOrder, globals['OrderId'])
    phone = GetFiveSimPhone(response)
    return phone

def GetFiveSimOrderId(response):
    return response['id']

def GetFiveSimCountry(response):
    return response['country']

def GetFiveSimCode(response):
    return response['sms'][0]['code']

def GetFiveSimPhone(response):
    return response['phone']

def FiveSimGetCode():
    hasSMS = False
    tries = 0
    while hasSMS == False:
        data = FiveSimApi(RequestType.CheckOrder, globals['OrderId'])
        if 'sms' in data and data['sms']:
            hasSMS = True
            sms = data['sms'][0]['code']
            print(f"[FiveSim API] > SMS Found: {sms}")
            return sms
        else:
            tries += 1
            if tries == 10:
                print("[FiveSim API] > No SMS received, exitting...")
                custom_exit()
            print("[FiveSim API] > There is no SMS, retrying...")
            time.sleep(15)

def BuyAnyActivation():
    country = ""
    requests_made = 1
    first_api = True
    phone = None
    while not phone:
        if first_api:
            country = "United States"
            data = FiveSimApi(RequestType.BuyActivation, "usa", "any", "tinder")
            if data == False:
                print(f"[5sim #{requests_made}] > There were no free phones, retrying...")
            else:
                globals['OrderId'] = data['id']
                phone = True
                return data['phone'], ActivationService.FiveSim, country
        else:
            country = "United Kingdom"
            data = SmspvaApi(RequestType.BuyActivation, 'uk', 'opt9')
            if data['response'] == '1':
                globals['OrderId'] = data['id']
                phone = True
                return data['number'], ActivationService.SmsPva, country
            elif data['response'] == '2':
                print(f"[SmsPva #{requests_made}] > There were no free phones, retrying...")
            
        if(requests_made % 100 == 0):
            first_api = not first_api
            curr_api = "FiveSim" if first_api else "SmsPva"
            print(f" > Switched to " + curr_api + " API")
        requests_made += 1

def SmspvaApi(req: RequestType, *args):
    params = {'apikey': SMSPVAAPI['Key']}
    if req == RequestType.BuyActivation:
        params.update([('metod', 'get_number'), ('country', (args[0]).lower()), ('service', args[1])])
    elif req == RequestType.CheckOrder:
        params.update([('metod', 'get_sms'), ('country', (args[0]).lower()), ('service', args[1]), ('id', args[2])])
    r = requests.get(SMSPVAAPI['Url'], params = params)
    data = json.loads(r.text)
    return data

def SmspvaBuyNumber():  
    hasPhone = False
    while hasPhone == False:
        data = SmspvaApi(RequestType.BuyActivation, 'uk', 'opt9')
        if data['response'] == '1':
            hasPhone = True
            globals['OrderId'] = data['id']
            return data['number'], data['id']
        elif data['response'] == '2':
            print(" > There were no free phones, retrying...")
            time.sleep(30)


def SmspvaGetCode():
    hasSMS = False
    tries = 0
    while hasSMS == False:
        data = SmspvaApi(RequestType.CheckOrder, 'uk', 'opt9', globals['OrderId'])
        if data['response'] == '1':
            hasSMS = True
            sms = data['sms']
            print(f"[SmsPva API] > SMS Found: {sms}")
            return sms
        elif data['response'] == '2':
            tries += 1
            if tries == 10:
                print("[SmsPva API] > No SMS received, exitting...")
                custom_exit()
            print("[SmsPva API] > There is no SMS, retrying...")
            time.sleep(15)


def waitForItem(driver, selector_type, selector_value, timeout=20, debug=True):
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((selector_type, selector_value)))
    except selenium.common.exceptions.TimeoutException:
        if debug:
            print(f" > Timeout error: Element couldn't be located. ({selector_value})")
        return None
    return element

def setAccountId(args):
    global globals
    try:
        accId = int(args[1])
    except:
        custom_exit()
    globals['AccountId'] = accId
    print(f" > Updated Account Id [{accId}]")
    
def readExcel():
    global globals
    wb = openpyxl.load_workbook('inputs.xlsx')
    ws = wb.worksheets[0]
    row = ws[globals['AccountId']+1]
    for cell in row:
        globals['AccountInfo'].append(cell.value)

def fillImages(accountId = 1):
    global globals
    cwd = globals['WorkingDir']
    folder = cwd + "accounts/" + str(accountId) + "/"
    images_temp = []
    for filename in os.listdir(os.path.normpath(folder)):
        path = os.path.normpath(folder+filename)
        images_temp.append(path)
    globals['Images'] = images_temp

def createFolder():
    cwd = globals['WorkingDir']
    folder = cwd + "accounts/" + str(globals['AccountId']) + "/"
    fold_path = os.path.normpath(folder)
    if not os.path.exists(fold_path):
        os.makedirs(fold_path)

def AsyncDownloadImage(megaLogin, folder, img_file):
    image_downloaded = False
    img_name = img_file[1]['a']['n']
    while not image_downloaded:
        try:
            print(f" > Downloading {img_name}")
            megaLogin.download(img_file, folder)
            image_downloaded = True
        except Exception as e:
            print(f" > Error downloading {img_name} [{str(e)}]")

def downloadFiles(megaLogin, images):
    cwd = globals['WorkingDir']
    folder = cwd + "accounts/" + str(globals['AccountId']) + "/"
    files = megaLogin.get_files()
    img_files = []
    for image in images:
        img_name = files[image]['a']['n']
        img_path = os.path.normpath(folder+img_name)
        if not os.path.exists(img_path):
            img_file = megaLogin.find(img_name)
            img_files.append(img_file)
        else:
            print(f" > Skipping {img_name}")
    threads = []
    for img_file in img_files:
            thread = threading.Thread(target=AsyncDownloadImage, args=(megaLogin, folder, img_file))
            threads.append(thread)
    for thread in threads:
            thread.start()
    for thread in threads:
            thread.join()
    print(f" > Downloading finished for account id [{globals['AccountId']}]")

def fixFolders():
    cwd = globals['WorkingDir']
    folder = cwd + "accounts"
    fold_path = os.path.normpath(folder)
    if not os.path.exists(fold_path):
      os.makedirs(fold_path)

def createDisplay():
    display = Display(visible=0, size=(1920, 1080))
    display.start()
    return display

def createDriver():
    capa = DesiredCapabilities.CHROME
    capa["pageLoadStrategy"] = "none"
    chrome_options = ChromeOptions()
    # chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument("--headless")
    # chrome_options.add_argument('--proxy-server=132.145.89.166:3128')
    chrome_options.add_argument("window-size=1920,1080")
    chrome_options.add_experimental_option('prefs', {
    'geolocation': True
    })
    chrome_options.add_experimental_option("excludeSwitches", ['enable-automation'])
    chrome_options.add_experimental_option("useAutomationExtension", False)
    driver = webdriver.Chrome(desired_capabilities=capa, options=chrome_options)
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        """
    })
    try:
        driver.execute(Command.SET_LOCATION, globals['ChromeDriverLocation'])
    except:
        driver.execute_cdp_cmd("Page.setGeolocationOverride", globals['DriverLocation'])
    # print(" > Headless Chrome Initialized. Updating window size...")
    # driver.set_window_size(1920, 1080)
    # print(" > Headless Chrome is ready to rock!!!")
    return driver

def clickTinderButton(driver):
    try:
        driver.execute_script("document.querySelector(\"button[aria-label='Log in with phone number']\").click()")
    except Exception as e:
        print(" > Can't find Log in button.")
        print(str(e))
        custom_exit()
    #### OLD #### 

    #selector = "[aria-label='Log in with phone number']"
    #btn = waitForItem(driver, By.CSS_SELECTOR, selector)
    #if not btn:
    #     print(" > Tinder Login Button wasn't found. Exitting....")
    #     custom_exit()
    # print(btn)
    # driver.execute_script("arguments[0].click();", btn)

def fixNumber(phoneNum, country):
    phoneNum = phoneNum[1:]
    r = requests.get(f"https://restcountries.eu/rest/v2/name/{country}")
    jsonCountries = json.loads(r.text)
    index = 0
    foundCC = False
    while foundCC == False:
        if jsonCountries[index]['callingCodes'][0] == '':
            index += 1
            continue
        for callingCode in jsonCountries[index]['callingCodes']:
            if phoneNum.startswith(callingCode):
                foundCC = True
                callingCodeLen = len(callingCode)
                phoneNum = phoneNum[callingCodeLen:]
                break
    return phoneNum

def fixBirthDate(date):
    dates = date.split('/')
    month = dates[0]
    day = dates[1]
    year = dates[2]
    return month, day, year

def searchNoThxBtn(driver):
    # noThxBtn = waitForItem(driver, By.XPATH, "//a[contains(text(),'No Thanks')]", timeout=2, debug=False)
    noThxBtn = waitForItem(driver, By.XPATH, '/html/body/div[2]/div/div/div[2]/button[2]', timeout=2, debug=False)
    if noThxBtn:
        print(" > Found 'No Thanks' button, clicking...")
        noThxBtn.click()     
          
def uploadImages(driver):
    images = globals['Images'][1:]
    for image in images:
        print(" > Uploading " + image)
        searchNoThxBtn(driver)
        btn = waitForItem(driver, By.XPATH, '/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div/div[2]/span/button')
        driver.save_screenshot('234.png')
        btn.click()
        input_field = waitForItem(driver, By.CSS_SELECTOR, 'input[type="file"]')
        input_field.send_keys(image)
        searchNoThxBtn(driver)
        chooseBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/div[1]/button[2]")
        chooseBtn.click()
        time.sleep(2)

def getNumber(driver):
    phoneNum, actSrc, country = BuyAnyActivation()
    changeCountryBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/div[2]/div/div[1]")
    changeCountryBtn.click()
    changeCountryInput = waitForItem(driver, By.NAME, "searchQuery")
    changeCountryInput.send_keys(country)
    time.sleep(1)
    selectCountry = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/div[2]/div[2]/div/div[1]")
    selectCountry.click()
    phoneInput = waitForItem(driver, By.NAME, "phone_number")
    if actSrc == ActivationService.FiveSim:
        phoneNum = fixNumber(phoneNum, country)
    phoneInput.send_keys(phoneNum)
    nextBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/button")
    nextBtn.click()
    print(f" > Sending verification code to phone number '{phoneNum}' from {country}.")
    time.sleep(10)
    code = None
    if actSrc == ActivationService.FiveSim:
        code = FiveSimGetCode()
    else:
        code = SmspvaGetCode()
    index = 1
    for c in str(code):
        codeInput = waitForItem(driver, By.XPATH, f"/html/body/div[2]/div/div/div[1]/div[3]/input[{index}]")
        codeInput.send_keys(c)
        index += 1
    continueBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/button")
    continueBtn.click()

def CheckBan(step):
    reason = "email" if step == "email" else "phone"
    if driver.current_url == "https://tinder.com/app/banned" or "Your Account Has Been Banned" in driver.find_element_by_tag_name('body').text:
        print(f" > Account got banned because of bad {reason}.")
        custom_exit()

def CheckCaptcha():
    return driver.current_url == "https://tinder.com/app/verify/onboarding"

def completeRegistration(driver):
    time.sleep(1)
    CheckBan("phone")
    driver.save_screenshot("567.png")
    emailInput = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/div[2]/input", timeout=15)
    if emailInput:
        emailInput.send_keys(globals['AccountInfo'][Columns.TINDER_EMAIL])
    else:
        print(" > Email field couldn't be found! Maybe account already exists?")
        custom_exit()
    print(" > Entering email, date of birth, name, photo and gender.")
    month, day, year = fixBirthDate(globals['AccountInfo'][Columns.BIRTHDATE])
    continueBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/div[2]/button")
    continueBtn.click()
    time.sleep(2)
    CheckBan("email")
    cookieBtn = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[2]/div/div/div[1]/button")
    if cookieBtn:
        cookieBtn.click()
    gotItBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/button", timeout=4)
    if not gotItBtn:
        gotItBtn = waitForItem(driver, By.CSS_SELECTOR, r"#modal-manager > div > div > div.Ta\(s\).As\(fs\).P\(16px\)--s > button", timeout=3)
    driver.save_screenshot("321.png")
    try:
        gotItBtn.click()
    except:
          print(" > Account got banned. ")
          custom_exit()
    time.sleep(3)
    womanBtn = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/form/div[2]/div[2]/div/div/div[1]/button[2]")
    womanBtn.click()
    time.sleep(1)
    nameInput = waitForItem(driver, By.ID, "name")
    nameInput.send_keys(globals['AccountInfo'][Columns.NAME])
    monthInput = waitForItem(driver, By.NAME, "month")
    dayInput = waitForItem(driver, By.NAME, "day")
    yearInput = waitForItem(driver, By.NAME, "year")
    monthInput.send_keys(month)
    dayInput.send_keys(day)
    yearInput.send_keys(year)
    photoInput = waitForItem(driver, By.CSS_SELECTOR, 'input[type="file"]')
    photoInput.send_keys(globals['Images'][0])
    time.sleep(3)
    chooseBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[1]/div[1]/button[2]")
    chooseBtn.click()
    time.sleep(10)
    continueBtnNew = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/form/div[7]/button", timeout=3)
    if not continueBtnNew:
        continueBtnNew = waitForItem(driver, By.CSS_SELECTOR, 'button[type="submit"]', timeout=3)
    continueBtnNew.click()
    time.sleep(10)
    if CheckCaptcha():
        time.sleep(20)
        first_iframe = waitForItem(driver, By.CSS_SELECTOR, 'iframe[title="arkose-enforcement"]', timeout=20, debug=False)
        if first_iframe:
            time.sleep(10)
            driver.switch_to.frame(first_iframe)
            second_iframe = waitForItem(driver, By.CSS_SELECTOR, 'iframe[data-e2e="challenge-frame"]', timeout=10, debug=False)
            if second_iframe:
                time.sleep(5)
                driver.switch_to.frame(second_iframe)
                third_iframe = waitForItem(driver, By.ID, "fc-iframe-wrap", timeout=10, debug=False)
                if third_iframe:
                    captchaUrl = third_iframe.get_attribute("src")
                    verificationInput = waitForItem(driver, By.ID, "verification-token", timeout=5, debug=False)
                    funCaptchaInput = waitForItem(driver, By.ID, "FunCaptcha-Token", timeout=5, debug=False)
                    publicKey = GetPublicKey()
                    print(' > Started solving captcha.')
                    token = CaptchaSolver(captchaUrl, publicKey)
                    print(' > Captcha solved by someone. Now trying to validate it in the browser.')
                    driver.execute_script(f"arguments[0].setAttribute('value', '{token}');", verificationInput)
                    driver.execute_script(f"arguments[0].setAttribute('value', '{token}');", funCaptchaInput)
                    driver.switch_to.frame(third_iframe)
                    time.sleep(5)
                    try:
                        driver.execute_script('solveMeta();')
                        print(" > Captcha is JavaScript.")
                    except:
                        print(" > Captcha is not JavaScript.")
                        funCaptchaInput = waitForItem(driver, By.NAME, "fc-token", timeout=5, debug=False)
                        tokenSplit = token.split('|')
                        newToken = tokenSplit[0] + '|' + tokenSplit[1]
                        driver.execute_script(f"arguments[0].setAttribute('value', '{newToken}');", funCaptchaInput)
                        driver.execute_script("$('form').submit()")
                    print(' > Just continued the validation process...')
    else:
        time.sleep(5)
    time.sleep(10)
    driver.save_screenshot('123.png')
    print(" > Redirecting...")
    driver.get("https://tinder.com/app/profile/edit")
    time.sleep(5)
    coordBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div/div/div[3]/button[1]", timeout=1)
    if coordBtn:
        coordBtn.click()
    else:
        print(" > Captcha hasn't been solved properly. Exitting...")
        custom_exit()
    time.sleep(0.1)
    notBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div/div/div[3]/button[2]", timeout=1)
    if notBtn:
        notBtn.click()
    time.sleep(0.5)
    randomPopUpBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/button", timeout=1)
    if randomPopUpBtn:
        randomPopUpBtn.click()
    time.sleep(5)
    driver.get("https://tinder.com/app/profile/edit")
    time.sleep(3)
    bioTextArea = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div/div[2]/div[2]/div/textarea")
    bioTextArea.send_keys(globals['AccountInfo'][Columns.TINDER_BIO])
    uploadImages(driver)
    time.sleep(3)
    saveBtn = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div/div[1]/a")
    saveBtn.click()
    time.sleep(1)
    print(" > Everything done, captain! Redirecting to main page now.")
    backBtnNew = waitForItem(driver, By.CSS_SELECTOR, 'a[href="/app/recs"]', timeout=3)
    if backBtnNew:
        backBtnNew.click()
    else:
        print(" > Back button couldn't be located.")
          
def openTinder(driver):
    driver.execute_script("window.open('about:blank', 'tinderTab');")
    driver.switch_to.window("tinderTab")
    driver.get("https://tinder.com?lang=en-GB")
    time.sleep(6)
    clickTinderButton(driver)
    getNumber(driver)
    completeRegistration(driver)

def adjustCoords():
    global globals
    coords = globals['AccountInfo'][Columns.COORDINATES]
    coords = coords.split(' ')
    coord_one = coords[0][:-2] if coords[0][-1] == "N" else "-"+coords[0][:-2]
    coord_two = coords[1][:-2] if coords[1][-1] == "E" else "-"+coords[1][:-2]
    coords = [coord_one, coord_two]
          
    params = {
        "latitude": float(coords[0]),
        "longitude": float(coords[1]),
        "accuracy": 100
    }
    chrome_geolocation_format = {
        "location": {
            "latitude": float(coords[0]),
            "longitude": float(coords[1])
        }
    }

    globals['AccountCoordinates'] = coords
    globals['DriverLocation'] = params
    globals['ChromeDriverLocation'] = chrome_geolocation_format
    print(f" > Coordinates set to: {coords[0]}, {coords[1]}")

# def updateCoordinates(driver):
#     fake_lat = globals['AccountCoordinates'][0]
#     fake_long = globals['AccountCoordinates'][1]
#     driver.execute_script('window.navigator.geolocation.getCurrentPosition=function(success){var position = {"coords" : {"latitude": "' + f'{fake_lat}' + '","longitude": "' + f'{fake_long}' + '"}}; success(position);}')

def downloadMegaImages():
    email = globals['AccountInfo'][Columns.MEGA_EMAIL]
    password = globals['AccountInfo'][Columns.MEGA_PASSWORD]
    try:
        m = globals['MegaInstance'].login(email, password)
        files = m.get_files()
    except:
        print(" > Problems with MEGA. Try again after a minute.")
        custom_exit()
    folder = None
    images = []
    for file in files:
        foldName = files[file]['a']['n']
        if f"Account #{globals['AccountId']}" in foldName:
            print(f" > Found MEGA folder ({foldName})")
            folder = files[file]['h']
            break
    if folder == None:
        print(f" > No photos for account #{globals['AccountId']}")
        custom_exit()
    images = m.get_files_in_node(folder)
    createFolder()
    downloadFiles(m, images)

def custom_exit():
    global driver, display
    try:
        driver.quit()
    except:
        pass
    try:
        display.stop()
    except:
        pass
    exit(0)

def main(args):
    global display, driver
    fixFolders()
    setAccountId(args)
    readExcel()
    adjustCoords()
    downloadMegaImages()
    fillImages(globals['AccountId'])
    #display = createDisplay()
    driver = createDriver()
    openTinder(driver)
    time.sleep(180)
    driver.refresh()
    time.sleep(7)
    driver.save_screenshot(f"final_{args[1]}.png")
    driver.quit()
    #display.stop()
    print(" > JOB DONE. GOODBYE, WORLD!")

main(sys.argv)
