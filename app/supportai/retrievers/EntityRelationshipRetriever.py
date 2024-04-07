from app.supportai.retrievers import BaseRetriever
from app.supportai.extractors import LLMEntityRelationshipExtractor
from app.metrics.tg_proxy import TigerGraphConnectionProxy

class EntityRelationshipRetriever(BaseRetriever):
    def __init__(self, embedding_service, embedding_store, llm_service, connection: TigerGraphConnectionProxy):
        super().__init__(embedding_service, embedding_store, llm_service, connection)
        self._check_query_install("Entity_Relationship_Retrieval")
        self.extractor = LLMEntityRelationshipExtractor(llm_service)

    def search(self, question, top_k=1):
        nodes_rels = self.extractor.document_er_extraction(question)
        res = self.conn.runInstalledQuery("Entity_Relationship_Retrieval",
                                          {"entities": [x["id"] for x in nodes_rels["nodes"]],
                                           "relationships": [x["type"] for x in nodes_rels["rels"]],
                                           "top_k": top_k})

        return res
        
    def retrieve_answer(self, question, top_k=1):
        retrieved = self.search(question, top_k)
        return self._generate_response(question, retrieved)