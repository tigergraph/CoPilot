#include <iostream>
#include "ExprFunctions.hpp"

int
main(int argc, char* argv[]) {
    std::cout << "Running copilot code." << std::endl;
    std::string milvus_host = "localhost";
    int64_t milvus_port = 19530;
    const std::string collection_name = "tg_support_documents";
    const std::string field_id_name = "pk";
    const std::string field_vertex_id_name = "vertex_id";
    const std::string field_vector_name = "document_vector";
    std::string metric_type = "L2";
    int64_t top_k = 10;
    std::vector<float> q_vector = {-0.0030031754032486375, 0.0006635236344847458};
    std::cout << "Searching in milvus." << std::endl;

    auto search_results = searchInMilvus(milvus_host, milvus_port, collection_name, field_vector_name, field_vertex_id_name, q_vector, metric_type, top_k);
    for (const auto& result : search_results) {
        std::cout << "Vector ID: " << result.first << ", Vertex ID: " << result.second << std::endl;
    }

    return 0;
}