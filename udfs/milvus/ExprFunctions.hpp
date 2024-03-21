#include "ExprUtil.hpp"

inline std::vector<std::pair<std::string, std::string>> searchInMilvus(const std::string& collection_name, const std::string& vector_field_name,
                            const std::string& vertex_id_field_name, const std::vector<float>& query_vector, const std::string& metric_type, const int64_t top_k) {
    const std::string milvus_host = "localhost";
    const int64_t milvus_port = 19530;

    MilvusUtil milvus_util(milvus_host, milvus_port);
    return milvus_util.search(collection_name, vector_field_name, vertex_id_field_name, query_vector, metric_type, top_k);
}