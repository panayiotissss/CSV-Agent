import os
import pandas as pd
from dotenv import load_dotenv
from anthropic import Anthropic
from app.tools import aggregate , filter_rows
from app.schema import Finding
import time
import logging
import os


os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/agent.log"),   # writes to the file
        logging.StreamHandler(),            # writes to the terminal
    ],
)
logger = logging.getLogger(__name__)


#Load env variables
load_dotenv()

 #Auto-reads ANTHROPIC_API_KEY
client=Anthropic()

#Load data
df = pd.read_csv("data/sample.csv")


#How we go from text to function calling
#Dictionary lookup from text to function.
DISPATCH = {
    "aggregate": aggregate,
    "filter_rows": filter_rows,
}


#System prompt and schema feeding
schema_text = ", ".join(f"{c} ({df[c].dtype})" for c in df.columns)

SYSTEM_PROMPT = f"""You are a data analyst agent for a sales CSV.
Columns available: {schema_text}.
Answer questions by calling tools to compute real numbers. Never invent a number — if you need a figure, compute it with a tool.
Always ask yourself if you are hallucinating an number or a column. If you cant compute that number or you face any problem respond with
"I dont know" and the reason why. Always conclude by calling the final_answer tool with your structured result. Never answer in plain text — the final_answer tool is the only way to respond to the user.
"""


#TOOLS

#Aggregate tool
aggregate_tool = {
    "name": "aggregate",
    "description": "Group rows by a column and compute an aggregate (sum, mean, count, min, max) over a numeric column. Use for totals, averages, counts, min or max grouped by a category.",
    "input_schema": {
        "type": "object",
        "properties": {
            "group_by": {"type": "string", "description": "Column to group by, e.g. 'region'"},
            "metric":   {"type": "string", "description": "Numeric column to aggregate, e.g. 'revenue'"},
            "agg_fn":   {"type": "string", "enum": ["sum","mean","count","min","max"], "description": "Which aggregation to apply"},
        },
        "required": ["group_by", "metric", "agg_fn"],
    },
}

filter_tool = {
    "name": "filter_rows",
    "description": "Filters rows by and returns a result by using operators like (==, !=, <,>,<=,>=) over columns in the dataframe. Use to narrow the data to rows matching a condition, often before aggregating. .",
    "input_schema": {
        "type": "object",
        "properties": {
            "column": {"type": "string", "description": "Column to filter by, e.g. 'region'"},
            "value":   {"type": ["string", "number"], "description": "Which value to filter on?"},
            "operator":   {"type": "string" , "enum": ["==","!=","<",">","<=",">="], "description": "Which opperator to apply"},
        },
        "required": ["column", "operator", "value"],
    },
}

final_answer = {
    "name": "final_answer",
    "description": "Provide the final structured answer once you have called all necessary tools and have enough information. This concludes the task.",
    "input_schema": {
        "type": "object",
        "properties": {
            "answer": {"type": "string", "description": "The natural-language answer to the user's question"},
            "key_numbers": {"type": "object", "description": "Named key figures, e.g. {'north_avg_revenue': 11833.33}"},
            "tools_used": {"type": "array", "items": {"type": "string"}, "description": "Tool names used, e.g. ['filter_rows','aggregate']"},
            "confidence": {"type": "string", "enum": ["high","medium","low"], "description": "Confidence in the result"},
        },
        "required": ["answer", "key_numbers", "tools_used", "confidence"],
    },
}




def call_with_retry(messages, max_retries=3):
    for attempt in range(max_retries):
        try:
            return client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1000,
                system=SYSTEM_PROMPT,
                tools=[aggregate_tool, filter_tool, final_answer],
                messages=messages,
            )
        except Exception as e:
            if attempt == max_retries - 1:   # last attempt failed
                raise                         # give up, re-raise
            wait = 2 ** attempt               # backoff: 1s, 2s, 4s
            time.sleep(wait)


#RUN AGENT
def run_agent(question:str)-> Finding:
    messages = [{"role": "user", "content": question}]
    max_iterations = 10
    for iteration in range(max_iterations):

        response = call_with_retry(messages)
 
        if response.stop_reason != "tool_use":
            for block in response.content:
                if block.type == "text":
                    logger.info("Final answer (text fallback): %s", block.text)
                    return Finding(answer=block.text, key_numbers={}, tools_used=[], confidence="low")

        else:
            logger.info(">>> Claude wants a tool")
            messages.append({"role": "assistant", "content": response.content})
            for block in response.content:
                if block.type == "text":
                    logger.info("Thinking: %s", block.text)
                if block.type == "tool_use":
                    if block.name == 'final_answer':
                        return Finding(**block.input)
                    logger.info("Tool call: %s", block.name)
                    logger.info("Args: %s", block.input)
                    fn = DISPATCH[block.name]
                    result = fn(df, **block.input)
                    if isinstance(result, dict) and "error" in result:
                        logger.warning("Tool %s returned an error: %s", block.name, result)
                    logger.info("Result: %s", result)
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": str(result),
                        }],
                    })
            logger.info("Looping back")
    logger.warning("Hit max iterations (%s) without a final answer", max_iterations)
    return Finding(
        answer="Could not complete the request within the step limit.",
        key_numbers={},
        tools_used=[],
        confidence="low",
    )
