from psycopg_pool import AsyncConnectionPool
from langsmith import Client
import logging


logger = logging.getLogger(__name__)

class StreamProcessor:
    """
    A class for processing streaming events from a langgraph.

    This class initializes a LangSmith Client and provides methods to process
    streaming events from a graph, handling various event types and yielding
    progress updates, streamed data, and final outputs.

    Attributes:
        client (Client): An instance of the LangSmith Client.

    Methods:
        process_stream(graph, question): Asynchronously processes the stream of events
        from the given graph for the provided question.
    """
    def __init__(self, config):
        self.client = Client()
        self.config = config

    async def process_stream(self, graph, question):
        """
        Asynchronously processes the stream of events from the given graph for the provided question.

        This method yields progress updates, streamed data, and final outputs as the graph processes
        the question. It handles various event types, including chat model streaming and chain end events.

        Args:
            graph: The langgraph object to process events from.
            question (str): The question to be processed by the graph.

        Yields:
            dict: A dictionary containing one of the following keys:
                - "progress": A string indicating the current step being processed.
                - "data": A string containing streamed chunks of the answer.
                - "final_output": The final generated answer.
            str: The URL of the completed run in LangSmith.

        Note:
            This method uses the LangSmith Client to retrieve the final run URL.
        """

        run_id = ""
        client  = Client()
        current_langgraph_node = []

        
        async for event in graph.astream_events({"question": question}, version="v1", config=self.config):
            run_id = event['run_id']
            kind = event["event"]
            if "langgraph_node" in event["metadata"]:
                if event["metadata"]["langgraph_node"] not in current_langgraph_node:
                    current_langgraph_node.append(event["metadata"]["langgraph_node"])
                    yield {
                        "type":"progress",
                        "model_provider": "",
                        "model_name": "",
                        "run_id" : event["run_id"],
                        "graph_node" : event["metadata"]["langgraph_node"],
                        "data": f"Processing {event['metadata']['langgraph_node']}..."
                        }

            if kind == "on_chat_model_stream":
                if  event["metadata"]["langgraph_node"] == "response":
                    run_id  = event["run_id"]
                    yield {
                        "type":"stream",
                        "model_provider": event["metadata"]["ls_provider"],
                        "model_name": event["metadata"]["ls_model_name"],
                        "run_id" : event["run_id"],
                        "graph_node" : event["metadata"]["langgraph_node"],
                        "data": event["data"]["chunk"].content
                    }

            if kind == "on_chain_end":
                if event["name"] == "cite_sources":
                    data = []
                    for source in event["data"]["output"]['cited_sources']:
                        data.append(
                            {
                                "source": source.source,
                                "url": source.url
                             }
                        )

                    run_url = ""

                    try :
                        run_url = client.read_run(event["run_id"]).url

                    except Exception as e:
                        logger.error(e)

                    finally:
                        yield {
                            "type":"final_output",
                            "model_provider": "",
                            "model_name": "",
                            "run_id" : event["run_id"],
                            "graph_node" : event["metadata"]["langgraph_node"],
                            "data": data,
                            "trace_url": run_url
                            }