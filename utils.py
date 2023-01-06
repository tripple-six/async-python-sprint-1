import logging
import sys
import json
from abc import ABC, abstractmethod

if sys.version_info[0] == 3:
    from urllib.request import urlopen
else:
    from urllib import urlopen

logger = logging.getLogger()

CITIES = {
    "MOSCOW": "https://code.s3.yandex.net/async-module/moscow-response.json",
    "PARIS": "https://code.s3.yandex.net/async-module/paris-response.json",
    "LONDON": "https://code.s3.yandex.net/async-module/london-response.json",
    "BERLIN": "https://code.s3.yandex.net/async-module/berlin-response.json",
    "BEIJING": "https://code.s3.yandex.net/async-module/beijing-response.json",
    "KAZAN": "https://code.s3.yandex.net/async-module/kazan-response.json",
    "SPETERSBURG": "https://code.s3.yandex.net/async-module/spetersburg-response.json",
    "VOLGOGRAD": "https://code.s3.yandex.net/async-module/volgograd-response.json",
    "NOVOSIBIRSK": "https://code.s3.yandex.net/async-module/novosibirsk-response.json",
    "KALININGRAD": "https://code.s3.yandex.net/async-module/kaliningrad-response.json",
    "ABUDHABI": "https://code.s3.yandex.net/async-module/abudhabi-response.json",
    "WARSZAWA": "https://code.s3.yandex.net/async-module/warszawa-response.json",
    "BUCHAREST": "https://code.s3.yandex.net/async-module/bucharest-response.json",
    "ROMA": "https://code.s3.yandex.net/async-module/roma-response.json",
    "CAIRO": "https://code.s3.yandex.net/async-module/cairo-response.json",
}
TRANSLATE_CITIES = {
    "MOSCOW": "Москва",
    "PARIS": "Париж",
    "LONDON": "Лондон",
    "BERLIN": "Берлин",
    "BEIJING": "Пекин",
    "KAZAN": "Казань",
    "SPETERSBURG": "Санкт-Петербург",
    "VOLGOGRAD": "Волгоград",
    "NOVOSIBIRSK": "Новосибирск",
    "KALININGRAD": "Калининград",
    "ABUDHABI": "Абу-Даби",
    "WARSZAWA": "Варшава",
    "BUCHAREST": "Бухарест",
    "ROMA": "Рим",
    "CAIRO": "Каир",
}
ERR_MESSAGE_TEMPLATE = "Something wrong. Please connect with administrator."

logging.basicConfig(
    filename="project.log",
    format="%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(funcName)s- %(message)s",
    level="INFO",
)
logger = logging.getLogger()


def get_conditions() -> dict:
    conditions = {}
    with open("examples/conditions.txt", "r", encoding="UTF-8") as file:
        for line in file:
            if line.startswith("#"):
                continue
            name, value = line.strip().split(" — ")
            conditions[name] = value
    return conditions


class WeatherApi(ABC):
    @abstractmethod
    def get_forecasting(self, city: str) -> dict:
        raise NotImplementedError


class YandexWeatherAPI(WeatherApi):
    """
    Base class for requests
    """

    @staticmethod
    def _do_req(url, method="GET"):
        """Base request method"""

        try:
            with urlopen(url) as req:
                resp = req.read().decode("utf-8")
                resp = json.loads(resp)
            if req.status != 200:
                raise Exception(
                    "Error during execute request. {}: {}".format(
                        resp.status, resp.reason
                    )
                )
            return resp
        except Exception as ex:
            logger.error(ex)
            raise Exception(ERR_MESSAGE_TEMPLATE)

    @staticmethod
    def _get_url_by_city_name(city_name):
        city_url = CITIES.get(city_name.upper(), None)
        if not city_url or city_url is None:
            raise Exception("Please check that city {} exists".format(city_name))
        return city_url

    def get_forecasting(self, city_name):
        """
        :param city_name: key as str
        :return: response data as json
        """
        logging.debug(f"Request the weather forecast in the city: {city_name}")
        city_url = self._get_url_by_city_name(city_name)
        return self._do_req(city_url)
