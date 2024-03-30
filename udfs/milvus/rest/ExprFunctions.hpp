#include <iostream>
#include "ExprUtil.hpp"

std::vector<float> stringToFloatVector(const std::string& str, char delimiter = ',') {
   std::vector<float> result;
   std::stringstream ss(str);
   std::string item;

   while (std::getline(ss, item, delimiter)) {
     try {
       result.push_back(std::stof(item));
     } catch (const std::invalid_argument& ia) {
       std::cerr << "Invalid argument: " << ia.what() << '\n';
     } catch (const std::out_of_range& oor) {
       std::cerr << "Out of Range error: " << oor.what() << '\n';
     }
   }

   return result;
}
inline ListAccum<std::string> searchInMilvus(
   const std::string milvus_host, int milvus_port, const std::string& collection_name,
   const std::string& vector_field_name, const std::string& vertex_id_field_name, const std::string& query_vector_str,
   const std::string& metric_type, int top_k) {
   
   MilvusUtil milvus_util(milvus_host, milvus_port);
   
   // Convert query vector string to std::vector<float>
   std::vector<float> query_vector = stringToFloatVector(query_vector_str);

   std::cout << "Beginning the search on: " << collection_name << std::endl;
   return milvus_util.search(collection_name, vector_field_name, vertex_id_field_name, query_vector, metric_type, top_k);
};