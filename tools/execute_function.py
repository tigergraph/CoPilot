from langchain.tools import BaseTool
from langchain.tools.base import ToolException
from pyTigerGraph import TigerGraphConnection

class ExecuteFunction(BaseTool):
    name = "ExecuteFunction"
    description = "Execute a pyTigerGraph function, always use the output of GenerateFunction as input to this tool."
    conn: "TigerGraphConnection" = None
    handle_tool_error: bool =True

    def __init__(self, conn):
        super().__init__()
        self.conn = conn

    def _run(self, function: str) -> str:
        try:
            loc = {}
            exec("res = conn."+function, {"conn": self.conn}, loc)
            return loc["res"]
        except:
            raise ToolException("The function {} did not execute directly. Please rephrase your question and try again".format(function))

    async def _arun(self) -> str:
        """Use the tool asynchronously."""
        raise NotImplementedError("custom_search does not support async")

    def _handle_error(error:ToolException) -> str:
        return  "The following errors occurred during tool execution:" + error.args[0]+ "Please ask for human input if they asked their question correctly."