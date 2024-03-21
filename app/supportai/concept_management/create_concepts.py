class BaseConceptCreator():
    def __init__(self, conn, llm, embedding_service):
        self.conn = conn
        self.llm = llm
        self.embedding_service = embedding_service

    def _install_query(self, query_name):
        with open(f"app/gsql/supportai/concept_curation/concept_creation/{query_name}.gsql", "r") as f:
            query = f.read()
        res = self.conn.gsql("USE GRAPH "+self.conn.graphname+"\n"+query+"\n INSTALL QUERY "+query_name)
        return res


    def _check_query_install(self, query_name):
        endpoints = self.conn.getEndpoints(dynamic=True) # installed queries in database
        installed_queries = [q.split("/")[-1] for q in endpoints]

        if query_name not in installed_queries:
            return self._install_query(query_name)
        else:
            return True

    def create_concepts(self):
        raise NotImplementedError
    
class RelationshipConceptCreator(BaseConceptCreator):
    def __init__(self, conn, llm, embedding_service):
        super().__init__(conn, llm, embedding_service)
        self._check_query_install("Build_Relationship_Concepts")
    
    def create_concepts(self, minimum_cooccurrence=5):
        res = self.conn.runInstalledQuery("Build_Relationship_Concepts", {"occurence_min": minimum_cooccurrence})
        return res
    
class EntityConceptCreator(BaseConceptCreator):
    def __init__(self, conn, llm, embedding_service):
        super().__init__(conn, llm, embedding_service)
        self._check_query_install("Build_Entity_Concepts")
    
    def create_concepts(self):
        res = self.conn.runInstalledQuery("Build_Entity_Concepts")
        return res
    
class CommunityConceptCreator(BaseConceptCreator):
    def __init__(self, conn, llm, embedding_service):
        super().__init__(conn, llm, embedding_service)
        self._check_query_install("Build_Community_Concepts")
    
    def create_concepts(self, min_community_size=10, max_community_size=100):
        res = self.conn.runInstalledQuery("Build_Community_Concepts", {"v_type_set": ["Entity", "Relationship"],
                                                                       "e_type_set": ["IS_HEAD_OF", "HAS_TAIL"],
                                                                        "min_community_size": min_community_size,
                                                                        "max_community_size": max_community_size
                                                                        })
        return res