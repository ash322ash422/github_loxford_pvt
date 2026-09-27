# langchain_agent_calculator_weather.py
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool

import math
import requests

# TOOL 1 : Calculator
@tool
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    Examples:
    25*4
    100/5
    sqrt(16)
    sin(0.5)
    """
    print("...Running calculator tool")

    try:
        result = eval( expression,{"__builtins__": None}, vars(math),)
        return str(result)

    except Exception as e:
        return f"Calculation error: {e}"


# TOOL 2 : Weather
@tool
def get_weather(city: str) -> str:
    """
    Get current weather information for a city.
    """

    print("...Running weather tool")

    try:
        geo_url = (
            f"https://geocoding-api.open-meteo.com/"
            f"v1/search?name={city}"
        )

        geo_response = requests.get( geo_url, timeout=10 )

        geo_data = geo_response.json()

        if "results" not in geo_data:
            return "City not found"

        latitude = geo_data["results"][0]["latitude"]
        longitude = geo_data["results"][0]["longitude"]

        weather_url = (
            "https://api.open-meteo.com/v1/forecast"
            f"?latitude={latitude}"
            f"&longitude={longitude}"
            "&current_weather=true"
        )

        weather_response = requests.get(weather_url, timeout=10 )

        weather_data = weather_response.json()

        current = weather_data.get("current_weather")

        if current is None:
            return "Weather data unavailable"

        temperature = current["temperature"]
        windspeed   = current["windspeed"]

        return (
            f"Temperature: {temperature}°C, "
            f"Wind Speed: {windspeed} km/h"
        )

    except Exception as e:
        return f"Weather error: {e}"


# CREATE AGENT FUNCTION
def build_agent(api_key):

    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=api_key,
    )

    tools = [ calculator,  get_weather, ]

    agent = create_agent(
        model=llm,
        tools=tools,
        system_prompt="""
        You are a helpful assistant with access to tools..
        
        CRITICAL: Do NOT use markdown, bolding (**), italics (*), or LaTeX formatting like \\( \\) or \\[ \\].
        Provide responses in raw, plain text only. Example: Write '1 + 2 * 4 = 9' instead of structural equations.

        Use the calculator tool whenever mathematical
        calculations are required.

        Use the get_weather tool whenever weather
        information is requested.
        """
    )

    return agent
