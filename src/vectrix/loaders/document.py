
from unstructured.partition.auto import partition
from unstructured.cleaners.core import clean
from unstructured.chunking.basic import chunk_elements
class Document:
    """
    This class will import documents, process them and load them into the Vector Database.
    """

    def __init__(self):
