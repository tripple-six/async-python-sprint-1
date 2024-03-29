import datetime
from typing import Optional

from pydantic import BaseModel, validator


class HourForecast(BaseModel):
    hour: int
    temp: int
    condition: str


class DayForecast(BaseModel):
    date: datetime.datetime
    hours: list[HourForecast]
    avg_temp: Optional[int]
    count_hour_clear: Optional[float]

    CLEAR_CONDITIONS: set[str] = {"clear", "partly-cloudy", "cloudy", "overcast"}
    WORK_HOURS_RANGE: range = range(9, 20)

    @validator("date", pre=True)
    def day_str_to_date(cls, v) -> datetime:
        return datetime.datetime.strptime(v, "%Y-%m-%d")

    def calculate_avg_temp(self) -> None:
        work_hours: list[HourForecast] = [
            x for x in self.hours if x.hour in self.WORK_HOURS_RANGE
        ]
        self.avg_temp = (
            sum(x.temp for x in work_hours) // len(work_hours) if work_hours else 0
        )

    def calculate_avg_hour_clear_days(self) -> None:
        result: list[str] = [
            x.condition
            for x in self.hours
            if x.hour in self.WORK_HOURS_RANGE and x.condition in self.CLEAR_CONDITIONS
        ]
        self.count_hour_clear = len(result) if result else 0

    class Config:
        arbitrary_types_allowed: bool = True


class CityForecast(BaseModel):
    name: str
    forecasts: list[DayForecast]
    avg_temp: Optional[float]
    avg_hour_clear: Optional[int]

    def calculate_avg_temp(self) -> None:
        result = []
        for forecast in self.forecasts:
            forecast.calculate_avg_temp()
            if forecast.avg_temp is not None:
                result.append(forecast.avg_temp)
        self.avg_temp = round(sum(result) / len(result), 1)

    def calculate_avg_hour_clear(self) -> None:
        result = []
        for forecast in self.forecasts:
            forecast.calculate_avg_hour_clear_days()
            if forecast.count_hour_clear is not None:
                result.append(forecast.count_hour_clear)
        self.avg_hour_clear = round(sum(result) / len(result), 1)

    def calculate(self) -> None:
        self.calculate_avg_hour_clear()
        self.calculate_avg_temp()

    def clear_blank_forecast(self) -> None:
        self.forecasts = list(
            filter(
                lambda item: item.hours,
                self.forecasts,
            )
        )


class RatingCity(BaseModel):
    city: CityForecast
    rating: int


class RatingCityList(BaseModel):
    cities: list[RatingCity]


class CityForecastList(BaseModel):
    cities: list[CityForecast]

    def aggregate_rating_cities(self) -> RatingCityList:
        sorted_cities_by_avg_temp_and_avg_hour: list[CityForecast] = sorted(
            self.cities,
            key=lambda city: (city.avg_temp, city.avg_hour_clear),
            reverse=True,
        )

        rating_cities: list[RatingCity] = [
            RatingCity(city=city, rating=index + 1)
            for index, city in enumerate(sorted_cities_by_avg_temp_and_avg_hour)
        ]
        result: RatingCityList = RatingCityList(cities=rating_cities)
        return result
