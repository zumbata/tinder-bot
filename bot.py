import time, paramiko, openpyxl, sys, requests, json, os, shutil, selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver import ChromeOptions
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.command import Command
from enum import Enum
from mega import Mega
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
            if tries == 6:
                print("[FiveSim API] > No SMS received, exitting...")
                exit(0)
            print("[FiveSim API] > There is no SMS, retrying...")
            time.sleep(10)

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
            if tries == 6:
                print("[SmsPva API] > No SMS received, exitting...")
                exit(0)
            print("[SmsPva API] > There is no SMS, retrying...")
            time.sleep(10)


def waitForItem(driver, selector_type, selector_value, timeout=120):
    try:
        element = WebDriverWait(driver, timeout).until(EC.presence_of_element_located((selector_type, selector_value)))
    except selenium.common.exceptions.TimeoutException:
        print(" > Timeout error: Element couldn't be located.")
        return None
    return element

def setAccountId(args):
    global globals
    try:
        accId = int(args[1])
    except:
        exit(0)
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

def downloadFiles(megaLogin, images):
    cwd = globals['WorkingDir']
    folder = cwd + "accounts/" + str(globals['AccountId']) + "/"
    files = megaLogin.get_files()
    for image in images:
        img_name = files[image]['a']['n']
        img_path = os.path.normpath(folder+img_name)
        if not os.path.exists(img_path):
            img_file = megaLogin.find(img_name)
            print(f" > Downloading {img_name}")
            megaLogin.download(img_file, folder)
        else:
            print(f" > Skipping {img_name}")
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
    # chrome_options.add_argument("--no-sandbox")
    # chrome_options.add_argument("--disable-gpu")
    # chrome_options.add_argument('--disable-dev-shm-usage')
    # chrome_options.add_argument("--headless")
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
        driver.execute_cdp_cmd("Page.setGeolocationOverride", globals['DriverLocation'])
    except:
        print(globals['ChromeDriverLocation'])
        driver.execute(Command.SET_LOCATION, globals['ChromeDriverLocation'])
    # print(" > Headless Chrome Initialized. Updating window size...")
    # driver.set_window_size(1920, 1080)
    # print(" > Headless Chrome is ready to rock!!!")
    return driver

def findTinderButton(driver):
    selector = "[aria-label='Log in with phone number']"
    btn = waitForItem(driver, By.CSS_SELECTOR, selector, timeout=7)
    if btn == None:
        print(" > Tinder Login Button wasn't found. Exitting....")        
        exit(0)
    return btn

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

def uploadImages(driver):
    images = globals['Images'][1:]
    for image in images:
        print(" > Uploading " + image)
        btn = waitForItem(driver, By.XPATH, '//*[@id="content"]/div/div[1]/div/main/div[1]/div/div/div/div/div[2]/span/button', timeout=10)
        btn.click()
        input_field = waitForItem(driver, By.CSS_SELECTOR, 'input[type="file"]')
        input_field.send_keys(image)
        time.sleep(1.5)
        chooseBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/button[2]")
        chooseBtn.click()
        time.sleep(2)

def getNumber(driver):
    phoneNum, actSrc, country = BuyAnyActivation()
    changeCountryBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/div[2]/div/div[1]", timeout=3)
    changeCountryBtn.click()
    changeCountryInput = waitForItem(driver, By.NAME, "searchQuery", timeout=1)
    changeCountryInput.send_keys(country)
    time.sleep(1)
    selectCountry = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/div[2]/div[2]/div[1]", timeout=1)
    selectCountry.click()
    phoneInput = waitForItem(driver, By.NAME, "phone_number", timeout=1)
    if actSrc == ActivationService.FiveSim:
        phoneNum = fixNumber(phoneNum, country)
    phoneInput.send_keys(phoneNum)
    nextBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/button", timeout=3)
    nextBtn.click()
    print(f" > Sending verification code to phone number '{phoneNum}' from {country}.")
    time.sleep(5)
    code = None
    if actSrc == ActivationService.FiveSim:
        code = FiveSimGetCode()
    else:
        code = SmspvaGetCode()
    index = 1
    for c in str(code):
        codeInput = waitForItem(driver, By.XPATH, f"/html/body/div[2]/div/div/div[2]/div[3]/input[{index}]", timeout=1)
        codeInput.send_keys(c)
        index += 1
    continueBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/button", timeout=1)
    continueBtn.click()

def completeRegistration(driver):
    time.sleep(1)
    if "Your Account Has Been Banned" in driver.find_element_by_tag_name('body').text:
        print(" > Account got banned.")
        exit(0)
    emailInput = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/div[2]/input", timeout=15)
    if emailInput:
        emailInput.send_keys(globals['AccountInfo'][Columns.TINDER_EMAIL])
    else:
        print(" > Email field couldn't be found! Maybe account already exists?")
        exit(0)
    print(" > Entering email, date of birth, name, photo and gender.")
    month, day, year = fixBirthDate(globals['AccountInfo'][Columns.BIRTHDATE])
    continueBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/div[2]/button", timeout=1)
    continueBtn.click()
    gotItBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/button", timeout=4)
    gotItBtn.click()
    womanBtn = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/form/div[2]/div[2]/div/div/div[1]/button[2]", timeout=1)
    womanBtn.click()
    nameInput = waitForItem(driver, By.ID, "name", timeout=1)
    nameInput.send_keys(globals['AccountInfo'][Columns.NAME])
    monthInput = waitForItem(driver, By.NAME, "month", timeout=1)
    dayInput = waitForItem(driver, By.NAME, "day", timeout=1)
    yearInput = waitForItem(driver, By.NAME, "year", timeout=1)
    monthInput.send_keys(month)
    dayInput.send_keys(day)
    yearInput.send_keys(year)
    photoInput = waitForItem(driver, By.CSS_SELECTOR, 'input[type="file"]', timeout=10)
    photoInput.send_keys(globals['Images'][0])
    time.sleep(1)
    chooseBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/div[1]/button[2]", timeout=5)
    chooseBtn.click()
    time.sleep(3)
    continueBtnNew = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/form/div[5]/button", timeout=1)
    continueBtnNew.click()
    time.sleep(9)
    driver.get("https://tinder.com/app/profile/edit")
    time.sleep(2)
    coordBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div/div/div[3]/button[1]", timeout=3)
    if coordBtn:
        coordBtn.click()
    time.sleep(0.1)
    notBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div/div/div[3]/button[2]", timeout=3)
    if notBtn:
        notBtn.click()
    cookieBtn = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[2]/div/div/div[1]/div/button", timeout=2)
    if cookieBtn:
        cookieBtn.click()
    time.sleep(0.5)
    randomPopUpBtn = waitForItem(driver, By.XPATH, "/html/body/div[2]/div/div/div[2]/button", timeout=4)
    if randomPopUpBtn:
        randomPopUpBtn.click()
    time.sleep(1)
    driver.get("https://tinder.com/app/profile/edit")
    time.sleep(3)
    bioTextArea = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div/div[2]/div[2]/div/textarea", timeout=10)
    bioTextArea.send_keys(globals['AccountInfo'][Columns.TINDER_BIO])
    uploadImages(driver)
    time.sleep(3)
    saveBtn = waitForItem(driver, By.XPATH, "/html/body/div[1]/div/div[1]/div/main/div[1]/div/div/div/div/div[1]/a", timeout=3)
    saveBtn.click()
    time.sleep(1)
    print(" > Everything done, captain!")

def openTinder(driver):
    driver.execute_script("window.open('about:blank', 'tinderTab');")
    driver.switch_to.window("tinderTab")
    driver.get("https://tinder.com")
    time.sleep(4)
    btn = findTinderButton(driver)
    btn.click()
    getNumber(driver)
    completeRegistration(driver)

def adjustCoords():
    global globals
    coords = globals['AccountInfo'][Columns.COORDINATES]
    coords = coords.split(' ')
    coords = [ x[:-2] for x in coords ]
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
    m = globals['MegaInstance'].login(email, password)
    files = m.get_files()
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
        exit(0)
    images = m.get_files_in_node(folder)
    createFolder()
    downloadFiles(m, images)

def main(args):
    fixFolders()
    setAccountId(args)
    readExcel()
    adjustCoords()
    downloadMegaImages()
    fillImages(globals['AccountId'])
    display = createDisplay()
    driver = createDriver()
    openTinder(driver)
    time.sleep(5)
    driver.quit()
    display.stop()
    print(" > JOB DONE. GOODBYE, WORLD!")

main(sys.argv)