from psycopg_pool import AsyncConnectionPool
from langsmith import Client

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
        langgraph_node = ""
        loaded_json = ""
        allow_streaming = True

        
        async for event in graph.astream_events({"question": question}, version="v1", config=self.config):
            run_id = event['run_id']
            kind = event["event"]
            if kind == "on_chat_model_stream":
                if langgraph_node != event['metadata']['langgraph_triggers']:
                    langgraph_node = event['metadata']['langgraph_triggers']
                    yield  {
                        "run_id" : run_id,
                        "type" : "progress",
                        "status" : langgraph_node[0].split(':')[-1]}

                if event['metadata']['langgraph_node'] == "generate_response":
                    if event['data']['chunk'].content and 'partial_json' in event['data']['chunk'].content[0]:
                        loaded_json += event['data']['chunk'].content[0]['partial_json']
                        if ('{"answer": "' in loaded_json) and allow_streaming:
                            # Remove {"answer": " from the loaded JSON
                            chunk_length = len(event['data']['chunk'].content[0]['partial_json'])
                            chunk = loaded_json.replace('{"answer": "', '')[-chunk_length:]
                            if not '.", "' in loaded_json:
                                yield {
                                    "run_id" : run_id,
                                    "type" : "response",
                                    "chunk_content" : chunk}
                            else:
                                allow_streaming = False
                                # Split the chunk at the last double quote
                                last_quote_index = chunk.rfind('"')
                                if last_quote_index != -1:
                                    yield {
                                        "run_id" : run_id,
                                        "type" : "response",
                                        "chunk_content" : chunk[:last_quote_index]}
                                else:
                                    yield {
                                        "run_id" : run_id,
                                        "type" : "response",
                                        "chunk_content" : chunk.split(', "quotes":')[0]}
                                    break
                                    
            # Print the documents used to generate the answer, if any
            if kind == "on_chain_end":
                if event["name"] == "generate_response":
                    yield {
                        "run_id" : run_id,
                        "type" : "final_output",
                        "sources" : event['data']['output']['generation'][0]['args'],
                        "trace_url": self.client.read_run(run_id).url}