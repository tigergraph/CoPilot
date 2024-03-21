#include <iostream>
#include "ExprFunctions.hpp" // Make sure this path is correct

int main() {
    std::string collection_name = "YourCollectionName";
    std::string vector_field_name = "YourVectorFieldName";
    std::string vertex_id_field_name = "YourVertexIdFieldName";
    std::vector<float> query_vector = {/* your query vector elements */};
    std::string metric_type = "L2"; // Or "IP" based on your vector field configuration
    int64_t top_k = 10; // Number of nearest vectors to find
    auto search_results = searchInMilvus(collection_name, vector_field_name, vertex_id_field_name, query_vector, metric_type, top_k);    // Output search results
    for (const auto& result : search_results) {
        std::cout << "Vector ID: " << result.first << ", Vertex ID: " << result.second << std::endl;
    }    
    return 0;
}