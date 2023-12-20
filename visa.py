"""
Нагрузка плагина SPP

1/2 документ плагина
"""
import datetime
import itertools
import logging
import os
import re
import time

import dateutil.parser
from selenium.webdriver.chrome.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.common import NoSuchElementException

from src.spp.types import SPP_document


class VISA:
    """
    Класс парсера плагина SPP

    :warning Все необходимое для работы парсера должно находится внутри этого класса

    :_content_document: Это список объектов документа. При старте класса этот список должен обнулиться,
                        а затем по мере обработки источника - заполняться.


    """

    SOURCE_NAME = 'visa'
    _content_document: list[SPP_document]

    HOST = 'https://usa.visa.com'

    def __init__(self, webdriver: WebDriver, *args, **kwargs):
        """
        Конструктор класса парсера

        По умолчанию внего ничего не передается, но если требуется (например: driver селениума), то нужно будет
        заполнить конфигурацию
        """
        # Обнуление списка
        self._content_document = []

        self.driver = webdriver

        # Логер должен подключаться так. Вся настройка лежит на платформе
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.debug(f"Parser class init completed")
        self.logger.info(f"Set source: {self.SOURCE_NAME}")
        ...

    def content(self) -> list[SPP_document]:
        """
        Главный метод парсера. Его будет вызывать платформа. Он вызывает метод _parse и возвращает список документов
        :return:
        :rtype:
        """
        self.logger.debug("Parse process start")
        self._parse()
        self.logger.debug("Parse process finished")
        return self._content_document

    def _parse(self):
        """
        Метод, занимающийся парсингом. Он добавляет в _content_document документы, которые получилось обработать
        :return:
        :rtype:
        """
        # HOST - это главная ссылка на источник, по которому будет "бегать" парсер
        self.logger.debug(F"Parser enter to {self.HOST}")

        # ========================================
        # Тут должен находится блок кода, отвечающий за парсинг конкретного источника
        # -
        self.driver.set_page_load_timeout(40)

        blog_link = 'https://usa.visa.com/visa-everywhere/blog.html'


        self._parsing_visa_press_release()
        self._parsing_visa_archive()



        # Логирование найденного документа
        # self.logger.info(self._find_document_text_for_logger(document))

        # ---
        # ========================================
        ...

    def _parsing_visa_press_release(self):
        press_release_link = 'https://usa.visa.com/about-visa/newsroom/press-releases-listing.html#2a'
        self.logger.debug(f'Start parse press-releases from url: {press_release_link}')

        self._initial_access_source(press_release_link, 4)

        tabs = self.driver.find_elements(By.CLASS_NAME, 'tab-pane')
        print(len(tabs))

        links = []

        for tab in tabs:
            articles = tab.find_elements(By.TAG_NAME, "a")
            dates = tab.find_elements(By.TAG_NAME, "p")

            for a, d in zip(articles, dates):
                print(d.text, a.text, a.get_attribute('href'))

            for article in articles:
                link = article.get_attribute('href')
                if link:
                    links.append(link)

        for link in links[:30]:
            self._parse_press_release_page(link)

    def _parse_press_release_page(self, url: str):
        self.logger.debug(f'Start parse press-release from url: {url}')
        self._initial_access_source(url, 3)

        try:
            title = self.driver.find_element(By.XPATH, '//*[@id="response1"]/div[1]/h1').text
            date = self.driver.find_element(By.XPATH, '//*[@id="response1"]/div[1]/p').text
            pub_date = dateutil.parser.parse(date)
            text = self.driver.find_element(By.CLASS_NAME, 'press-release-body').text

            document = SPP_document(None, title, None, text, url, None, None, pub_date, datetime.datetime.now())
            self.logger.info(self._find_document_text_for_logger(document))
            self._content_document.append(document)
        except Exception as e:
            self.logger.error(e)


    def _parsing_visa_archive(self):
        archive_link = 'https://usa.visa.com/partner-with-us/visa-consulting-analytics/leverage-economic-and-business-insights/archives.html'

        self.logger.debug(f'Start parse press-releases from url: {archive_link}')
        self._initial_access_source(archive_link, 5)

        links = []

        tabs = self.driver.find_elements(By.CLASS_NAME, 'vs-accordion-content')
        print(len(tabs))
        for tab in tabs:
            sections = tab.find_elements(By.CLASS_NAME, 'section')
            print(len(sections))

            for section in sections:
                article = section.find_element(By.TAG_NAME, 'a')
                try:
                    date = section.find_element(By.TAG_NAME, 'span')
                    pub_date = dateutil.parser.parse(date.get_attribute('innerText'))
                except Exception as e:
                    self.logger.error(e)
                    continue
                link = article.get_attribute('href')


                # !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                # Вот это нужно поменять, если мы захотим скачивать файлы тоже.
                if link and link.endswith('.html'):
                    links.append((link, pub_date))
        print(len(links))
        print(links)
        for link, pub_date in links[:30]:
            self._parse_archive_page(link, pub_date)

    def _parse_archive_page(self, url: str, pub_date: datetime.datetime):
        self.logger.debug(f'Start parse archive from url: {url}')
        self._initial_access_source(url, 3)

        try:
            title = self.driver.find_element(By.XPATH, '//*[@id="skipTo"]/div[1]/div/div[1]/div[2]/div/h1').text
            text = self.driver.find_element(By.CLASS_NAME, 'vs-page-section').text

            document = SPP_document(None, title, None, text, url, None, None, pub_date, datetime.datetime.now())
            self.logger.info(self._find_document_text_for_logger(document))
            self._content_document.append(document)
        except Exception as e:
            self.logger.error(e)




    def _initial_access_source(self, url: str, delay: int = 2):
        self.driver.get(url)
        self.logger.debug('Entered on web page '+url)
        time.sleep(delay)
        self._agree_cookie_pass()

    def _agree_cookie_pass(self):
        """
        Метод прожимает кнопку agree на модальном окне
        """
        cookie_agree_xpath = '//*[@id="onetrust-accept-btn-handler"]'

        try:
            cookie_button = self.driver.find_element(By.XPATH, cookie_agree_xpath)
            if WebDriverWait(self.driver, 5).until(ec.element_to_be_clickable(cookie_button)):
                cookie_button.click()
                self.logger.debug(F"Parser pass cookie modal on page: {self.driver.current_url}")
        except NoSuchElementException as e:
            self.logger.debug(f'modal agree not found on page: {self.driver.current_url}')

    @staticmethod
    def _find_document_text_for_logger(doc: SPP_document):
        """
        Единый для всех парсеров метод, который подготовит на основе SPP_document строку для логера
        :param doc: Документ, полученный парсером во время своей работы
        :type doc:
        :return: Строка для логера на основе документа
        :rtype:
        """
        return f"Find document | name: {doc.title} | link to web: {doc.web_link} | publication date: {doc.pub_date}"
