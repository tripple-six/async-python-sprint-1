from multiprocessing.queues import Queue
import multiprocessing as mp
import pytest

from models import CityForecast, DayForecast, HourForecast
from tasks import DataCalculationTask, DataFetchingTask
from utils import YandexWeatherAPI


@pytest.fixture
def data_fetching_task(monkeypatch) -> DataFetchingTask:
    def mock_get_forecasting(self, city: str):
        return {
            "forecasts": [
                {
                    "date": "2022-01-01",
                    "hours": [
                        {"hour": 9, "temp": 10, "condition": "clear"},
                        {"hour": 10, "temp": 11, "condition": "cloudy"},
                        {"hour": 11, "temp": 12, "condition": "clear"},
                    ],
                }
            ]
        }

    monkeypatch.setattr(YandexWeatherAPI, "get_forecasting", mock_get_forecasting)
    weather_api = YandexWeatherAPI()
    return DataFetchingTask(weather_api)


@pytest.fixture
def city_forecast() -> CityForecast:
    return CityForecast(
        name="Moscow",
        forecasts=[
            DayForecast(
                date="2022-01-01",
                hours=[
                    HourForecast(hour=9, temp=10, condition="clear"),
                    HourForecast(hour=19, temp=20, condition="clear"),
                ],
            )
        ],
    )


@pytest.fixture
def queue() -> Queue:
    ctx = mp.get_context("spawn")
    return Queue(ctx=ctx)


def test_data_fetching_task(data_fetching_task) -> None:
    city = "Moscow"
    result = data_fetching_task(city)
    assert result == [
        DayForecast(
            date="2022-01-01",
            hours=[
                HourForecast(hour=9, temp=10, condition="clear"),
                HourForecast(hour=10, temp=11, condition="cloudy"),
                HourForecast(hour=11, temp=12, condition="clear"),
            ],
        )
    ]
    assert isinstance(result, list)
    assert all(isinstance(item, DayForecast) for item in result)
    assert result[0].date is not None


def test_data_calculation_task(city_forecast, queue):
    queue.put(city_forecast)
    pipe_sender, pipe_receiver = mp.Pipe()
    task = DataCalculationTask(queue, pipe_sender)
    task.start()
    received_data = pipe_receiver.recv()
    task.join()
    assert received_data.avg_temp == 15
    assert received_data.avg_hour_clear == 2
