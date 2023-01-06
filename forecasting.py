from concurrent.futures.thread import ThreadPoolExecutor
import multiprocessing as mp
from multiprocessing.queues import Queue
from models import CityForecast
from utils import YandexWeatherAPI, CITIES
from tasks import (
    DataFetchingTask,
    DataCalculationTask,
    DataAggregationTask,
    DataAnalyzingTask,
)


def forecast_weather() -> None:
    """
    Analysis of weather conditions by city
    """

    yw_api = YandexWeatherAPI()
    data_fetching_task = DataFetchingTask(yw_api)
    ctx = mp.get_context("spawn")
    q = Queue(ctx=ctx)
    pipe_calc_agg_receiver, pipe_calc_agg_sender = mp.Pipe(duplex=False)
    pipe_agg_analyze_receiver, pipe_agg_analyze_sender = mp.Pipe(duplex=False)

    calc_task = DataCalculationTask(q, pipe_calc_agg_sender)
    calc_task.start()

    agg_task = DataAggregationTask(pipe_calc_agg_receiver, pipe_agg_analyze_sender)
    agg_task.start()

    analyze_task = DataAnalyzingTask(pipe_agg_analyze_receiver)
    analyze_task.start()

    with ThreadPoolExecutor() as executor:
        for result, city in zip(executor.map(data_fetching_task, CITIES), CITIES):
            city_forecast: CityForecast = CityForecast(name=city, forecasts=result)
            q.put(city_forecast)

    calc_task.join()
    agg_task.join()
    analyze_task.join()


if __name__ == "__main__":
    forecast_weather()
