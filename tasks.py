import multiprocessing as mp
import queue
import threading
import json
from typing import Optional
from multiprocessing.connection import Connection

from utils import WeatherApi, TRANSLATE_CITIES, logger

from models import (
    CityForecast,
    DayForecast,
    CityForecastList,
    RatingCityList,
)
from prettytable import PrettyTable


class DataFetchingTask:
    def __init__(self, weather_api: WeatherApi) -> None:
        self.weather_api: WeatherApi = weather_api
        self.task_name = "DataFetching"

    def __call__(self, city: str = None) -> Optional[list[DayForecast]]:
        logger.info(f"{self.task_name}: started for {city}")
        result = self.weather_api.get_forecasting(city)
        forecasts_nested = result.get("forecasts", [])
        day_forecasts = [
            DayForecast.parse_obj(forecast) for forecast in forecasts_nested
        ]
        logger.info(f"{self.task_name}: Finished for {city}")
        return day_forecasts or None


class DataCalculationTask(mp.Process):
    def __init__(self, _queue: queue, pipe_sender: Connection) -> None:
        super().__init__()
        self._queue: queue = _queue
        self._pipe_sender: Connection = pipe_sender
        self.task_name = "DataCalculation"
        self._timeout_queue = 5

    def run(self) -> None:
        logger.info(f"{self.task_name}: Started")
        while True:
            try:
                item: CityForecast = self._queue.get(timeout=self._timeout_queue)
            except queue.Empty:
                self._pipe_sender.send(None)
                break
            item.calculate()
            item.clear_blank_forecast()
            self._pipe_sender.send(item)
            logger.info(f"{self.task_name}: done for {item.name}")
        logger.info(f"{self.task_name}: Finished")


class DataAggregationTask(mp.Process):
    """Aggregation calculated data"""

    def __init__(self, pipe_receiver: Connection, pipe_sender: Connection) -> None:
        super().__init__()
        self._receiver = pipe_receiver
        self._sender = pipe_sender
        self._items = []
        self.task_name = "DataAggregation"

    def run(self) -> None:
        """
        Aggregating the city rating
        """
        logger.info(f"{self.task_name}: Started")
        while True:
            item = self._receiver.recv()
            if item is None:
                self._receiver.close()
                break
            self._items.append(item)

        city_forecast_list = CityForecastList(cities=self._items)
        rating_city_list = city_forecast_list.aggregate_rating_cities()
        self._sender.send(rating_city_list)
        logger.info(f"{self.task_name}: Finished")


class DataAnalyzingTask(threading.Thread):
    """Analyzing and saving result"""

    def __init__(self, _receiver: Connection, is_save: bool = True) -> None:
        super().__init__()
        self._receiver = _receiver
        self.is_save = is_save
        self.task_name = "DataAnalyzing"
        self.text = "Самый благоприятный город - {city}"

    def run(self) -> None:
        logger.info(f"{self.task_name}: Started")

        data = self._receiver.recv()
        city = data.cities[0].city.name
        logger.info(f"{self.task_name}: Best city: {city}")

        if self.is_save:
            self.write_json(data)

        print(self.text.format(city=TRANSLATE_CITIES[city]))
        table = self.create_table(data)
        print(table)
        logger.info("Program finished.")

    @staticmethod
    def create_table(data: RatingCityList) -> PrettyTable:
        table: PrettyTable = PrettyTable()
        dates = []
        for city_rating in data.cities:
            for forecast in city_rating.city.forecasts:
                dates.append(forecast.date.strftime("%d-%m"))
            break
        table.field_names = ["Город/день", "", *dates, "Среднее", "Рейтинг"]
        temp_text = "Температура, среднее"
        hour_text = "Без осадков, часов"
        for city_rating in data.cities:
            date_temp = []
            clear_hour = []
            for forecast in city_rating.city.forecasts:
                date_temp.append(forecast.avg_temp)
                clear_hour.append(forecast.count_hour_clear)
            table.add_row(
                [
                    TRANSLATE_CITIES[city_rating.city.name],
                    temp_text,
                    *date_temp,
                    city_rating.city.avg_temp,
                    city_rating.rating,
                ]
            )
            table.add_row(
                [
                    "",
                    hour_text,
                    *clear_hour,
                    city_rating.city.avg_hour_clear,
                    "",
                ]
            )
        return table

    @staticmethod
    def write_json(data: RatingCityList) -> None:
        exclude_keys = {
            "cities": {"__all__": {"city": {"forecasts": {"__all__": {"hours"}}}}}
        }
        logger.info("Write to json")
        with open("report.json", "w", encoding="utf-8") as file:
            json.dump(
                data.dict(exclude=exclude_keys),
                file,
                indent=1,
                sort_keys=True,
                ensure_ascii=False,
                default=str,
            )
        logger.info("Finished writing to json")
