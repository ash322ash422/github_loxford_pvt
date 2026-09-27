# multi_server.py

import httpx
import ast
import operator
from mcp.server.fastmcp import FastMCP

# Initialize the server
mcp = FastMCP("Classroom Multi-Tool Server")

# --- TOOL 1: PRECISE CALCULATOR ---
# Supported operators for a safe sandbox calculation (avoids using unsafe eval())
ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg
}

def _safe_eval(node):
    if isinstance(node, ast.Num):
        return node.n
    elif isinstance(node, ast.BinOp):
        return ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    elif isinstance(node, ast.UnaryOp):
        return ALLOWED_OPERATORS[type(node.op)](_safe_eval(node.operand))
    raise TypeError(f"Unsupported math operation: {node}")

@mcp.tool()
def calculate_expression(expression: str) -> str:
    """Evaluates basic mathematical expressions precisely to prevent 
       LLM calculation errors.
    
    Args:
        expression: A math string containing numbers 
                    and operators +, -, *, /, ** (e.g., '2 * (3 + 4) ** 2')
    """
    try:
        # Clean white spaces and parse string expression safely into an AST tree
        tree = ast.parse(expression.replace(" ", ""), mode='eval')
        result = _safe_eval(tree.body)
        return f"Calculation Successful! Result: {result}"
    except Exception as e:
        return f"Math Error: Could not compute expression. {str(e)}"


# --- TOOL 2: LIVE WEATHER ---
@mcp.tool()
async def get_live_weather(latitude: float, longitude: float) -> str:
    """Fetch current weather for a location using latitude and longitude.

    Args:
        latitude: Decimal latitude, e.g. 40.7128.
        longitude: Decimal longitude, e.g. -74.0060.
    """
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={latitude}"
        f"&longitude={longitude}"
        "&current=temperature_2m,wind_speed_10m"
    )

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, timeout=10.0)
            response.raise_for_status()

            data = response.json()
            current = data.get("current", {})

            temp = current.get("temperature_2m")
            wind = current.get("wind_speed_10m")

            return (
                f"Live Weather Data: "
                f"Current Temperature: {temp}°C. "
                f"Wind Speed: {wind} km/h."
            )

        except httpx.HTTPError as e:
            return f"Weather API Error: {str(e)}"

        except Exception as e:
            return f"Unexpected Error: {str(e)}"

if __name__ == "__main__":
    mcp.run()
