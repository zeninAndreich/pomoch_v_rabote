from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import requests
import time

# Конфигурация авторизации
BASE_URL = "https://44.fabrtech.ru"
OPERATOR_LOGIN = "operator"
OPERATOR_PASSWORD = "QQqSoo$l!"

# Инициализация драйвера
driver = webdriver.Chrome()
driver.maximize_window()
wait = WebDriverWait(driver, 15)


def login():
    """Точный процесс авторизации с учетом структуры HTML"""
    print("Запускаю процесс авторизации...")
    driver.get(BASE_URL)

    try:
        # 1. Нажимаем кнопку "Войти" на главной странице
        print("Нахожу и нажимаю кнопку 'Войти'...")
        wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//button[contains(., 'Войти')]")
        )).click()

        # 2. Ждем появления окна авторизации
        print("Ожидаю появление окна авторизации...")
        wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "ul.nav-tabs.login-tabs")
        ))

        # 3. Находим и нажимаем вкладку "по логину"
        print("Ищу вкладку 'по логину'...")
        login_tab = wait.until(EC.element_to_be_clickable(
            (By.XPATH, "//ul[@class='nav nav-tabs login-tabs']//a[contains(., 'по логину')]")
        ))
        login_tab.click()
        print("Вкладка 'по логину' найдена и нажата")

        # 4. Вводим логин и пароль
        print("Ввожу учетные данные...")
        username_field = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "input[name='login[username]']")
        ))
        username_field.clear()
        username_field.send_keys(OPERATOR_LOGIN)

        password_field = wait.until(EC.visibility_of_element_located(
            (By.CSS_SELECTOR, "input[name='login[password]']")
        ))
        password_field.clear()
        password_field.send_keys(OPERATOR_PASSWORD)

        # 5. Находим и нажимаем кнопку "Войти" (точный локатор из HTML)
        print("Нажимаю кнопку входа...")
        submit_btn = wait.until(EC.element_to_be_clickable(
            (By.CSS_SELECTOR, "button.login-password-btn")
        ))

        # Дополнительное ожидание и прокрутка к кнопке
        time.sleep(1)  # Даем время для завершения анимаций
        driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", submit_btn)
        submit_btn.click()
        print("Кнопка 'Войти' нажата")

        # 6. Проверяем успешность авторизации
        #print("Проверяю успешность входа...")
        #wait.until(lambda d: "dashboard" in d.current_url.lower() or
                             #d.find_elements(By.XPATH, "//*[contains(., 'Добро пожаловать')]"))
        #print("Авторизация успешно выполнена!")

    except Exception as e:
        print(f"Ошибка при авторизации: {str(e)}")
        driver.save_screenshot("auth_error.png")
        raise


def collect_links():
    """Сбор всех ссылок на странице"""
    print("\nНачинаю сбор ссылок...")
    all_urls = set()

    # Основной сбор ссылок
    links = wait.until(EC.presence_of_all_elements_located((By.TAG_NAME, "a")))
    for link in links:
        url = link.get_attribute("href")
        if url and url.startswith(('http', '/')):
            all_urls.add(url if url.startswith('http') else f"{BASE_URL}{url}")

    # Проверка выпадающих меню
    print("Проверяю выпадающие меню...")
    dropdowns = driver.find_elements(By.CSS_SELECTOR,
                                     "[data-toggle='dropdown'], .dropdown-toggle, .has-dropdown"
                                     )

    for dropdown in dropdowns:
        try:
            ActionChains(driver).move_to_element(dropdown).pause(1).perform()
            for link in dropdown.find_elements(By.TAG_NAME, "a"):
                url = link.get_attribute("href")
                if url and url.startswith(('http', '/')):
                    all_urls.add(url if url.startswith('http') else f"{BASE_URL}{url}")
        except:
            continue

    print(f"Всего собрано ссылок: {len(all_urls)}")
    return all_urls


def check_links(urls):
    """Проверка работоспособности ссылок с улучшенной обработкой"""
    print("\nНачинаю проверку ссылок...")
    broken_links = []

    # Подготовка заголовков как в браузере
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
    }

    # Перенос cookies из Selenium в requests
    cookies = {c['name']: c['value'] for c in driver.get_cookies()}

    with requests.Session() as session:
        session.headers.update(headers)
        session.cookies.update(cookies)

        for i, url in enumerate(urls, 1):
            try:
                if not url or any(url.startswith(p) for p in ("javascript:", "#", "mailto:", "tel:")):
                    continue

                if not url.startswith(('http://', 'https://')):
                    url = f"{BASE_URL}{'/' if not url.startswith('/') else ''}{url}"

                # Увеличиваем таймаут и используем GET вместо HEAD
                response = session.get(
                    url,
                    timeout=20,
                    allow_redirects=True,
                    stream=True  # Не загружаем тело ответа полностью
                )
                response.close()  # Закрываем соединение

                if response.status_code >= 400:
                    # Двойная проверка для подозрительных статусов
                    if response.status_code in (403, 500, 502, 503):
                        time.sleep(1)  # Пауза между запросами
                        second_response = session.get(url, timeout=20, allow_redirects=True)
                        second_response.close()

                        if 200 <= second_response.status_code < 400:
                            print(f"[{i}/{len(urls)}] ✅ {url} - OK (при повторной проверке)")
                            continue

                    broken_links.append(f"{url} (Статус: {response.status_code})")
                    print(f"[{i}/{len(urls)}] ❌ {url} - ошибка {response.status_code}")
                else:
                    print(f"[{i}/{len(urls)}] ✅ {url} - OK")

            except requests.exceptions.Timeout:
                broken_links.append(f"{url} (Ошибка: Timeout)")
                print(f"[{i}/{len(urls)}] ⏳ {url} - таймаут")
            except Exception as e:
                broken_links.append(f"{url} (Ошибка: {str(e)})")
                print(f"[{i}/{len(urls)}] ⚠️ {url} - исключение: {str(e)}")

            # Пауза между запросами для снижения нагрузки
            time.sleep(0.5)

    return broken_links


def main():
    try:
        # Авторизация
        login()

        # Сбор ссылок
        all_urls = collect_links()

        # Проверка ссылок
        broken_links = check_links(all_urls)

        # Сохранение результатов
        with open("broken_links.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(broken_links))

        print("\nИтоговый отчет:")
        print(f"Всего проверено ссылок: {len(all_urls)}")
        print(f"Найдено проблемных ссылок: {len(broken_links)}")

        if broken_links:
            print("\nПервые 10 проблемных ссылок:")
            print("\n".join(broken_links[:10]))

    except Exception as e:
        print(f"\nПрограмма завершена с ошибкой: {str(e)}")
    finally:
        driver.quit()
        print("\nРабота браузера завершена")


if __name__ == "__main__":
    main()