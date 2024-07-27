import logging
import cv2
import numpy as np
import pytesseract
from PIL import Image
from io import BytesIO
import base64
import time

USERNAME = "TODO"
PASSWORD = "TODO"

assert USERNAME != "TODO"
assert PASSWORD != "TODO"

logger = logging.getLogger()

def recognize_captcha(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    _, binary_image = cv2.threshold(gray, 0, 255, cv2.THRESH_OTSU)
    
    count_white = np.sum(binary_image > 0)
    count_black = np.sum(binary_image == 0)
    if count_black > count_white:
        binary_image = 255 - binary_image

    final_image = cv2.copyMakeBorder(binary_image, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=(255, 255, 255))
    predicted_text = pytesseract.image_to_string(final_image, config='-c tessedit_char_whitelist=0123456789')

    return predicted_text.strip()


from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.wait import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.firefox.service import Service

options = webdriver.FirefoxOptions()
options.binary_location = "/usr/bin/firefox"

driver = webdriver.Firefox(options=options, service=Service("./geckodriver") )
driver.get("https://my.medu.ir/login.html")

def wait_for_captcha(locator, pervious_captcha=None):
    #captchasrc
    def _predicate(driver):
        elem = driver.find_element(*locator)
        if 'data:image' in elem.get_property('src'):
            return elem if elem.get_property('src') != pervious_captcha else False
        else:
            return False

    return _predicate

def try_get_captcha(img_locator, reload_locator):
    pervious_captcha = None

    while True:
        captcha_elem = WebDriverWait(driver, 60, ignored_exceptions=Exception).until(
            wait_for_captcha(img_locator, pervious_captcha)
        )

        captcha_src = captcha_elem.get_property("src")
        encoded_image = captcha_src.replace("data:image/png;base64,", "")
        im = Image.open(BytesIO(base64.b64decode(encoded_image)))
        im.save("captcha.png")
        
        captcha_value = recognize_captcha(np.array(im)).strip()

        if len(captcha_value) == 5:
            return captcha_value
        
        pervious_captcha = captcha_src
        logging.warning("Could not read captcha")
        driver.find_element(*reload_locator).click()
        time.sleep(2)

def wait_for_notif(success_locator, error_locator):
    def _predicate(driver):
        try:
            success = driver.find_element(*success_locator)
            
            if success:
                return "success"
        
        except NoSuchElementException:
            try:
                error = driver.find_element(*error_locator)
                
                if error:
                    return "error"
            
            except NoSuchElementException:
                return False

        return False

    return _predicate



WebDriverWait(driver, 60).until(
    EC.presence_of_element_located((By.ID, "btnstudent"))
).click()

driver.find_element(By.ID, "NationalID").send_keys(USERNAME)

driver.find_element(By.ID, "password").send_keys(PASSWORD)


while True:
    captcha = try_get_captcha((By.ID, "captchasrc"), (By.CLASS_NAME, "reloadCaptch"))

    elem = driver.find_element(By.ID, "captchaResponse")
    elem.clear()
    elem.send_keys(captcha)

    driver.find_element(By.ID, "loginSubmit").click()

    result = WebDriverWait(driver, 60).until(
        wait_for_notif((By.CLASS_NAME, "notifyjs-bootstrap-success"), 
                       (By.CLASS_NAME, "notifyjs-foo-error")
                       ))

    if result == "success":
        break

    logger.error("Incorrect captcha, trying again")
    driver.find_element(By.CLASS_NAME, "reloadCaptch").click()
    time.sleep(2)


elem = WebDriverWait(driver, 500).until(
    EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div[1]/main/div/div/div/div[1]/div/div/div/div/div[1]/div/div/div/div[5]/div/div"))
)

WebDriverWait(driver, 500).until(
    EC.element_to_be_clickable(elem)
)

from selenium.webdriver.common.action_chains import ActionChains

ActionChains(driver).move_to_element(elem).click().perform()
driver.switch_to.window(driver.window_handles[-1])
