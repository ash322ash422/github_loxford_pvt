from langchain.tools import tool

def dataframe_tool_factory(df):

    @tool
    def dataframe_python(code: str) -> str:
        """
        Execute Python code against the dataframe df.
        """

        local_vars = {"df": df}

        try:
            result = eval(code, {}, local_vars)
            return str(result)

        except Exception:
            try:
                exec(code, {}, local_vars)

                if "result" in local_vars:
                    return str(local_vars["result"])

                return "Code executed."

            except Exception as e:
                return f"Error: {e}"

    return dataframe_python