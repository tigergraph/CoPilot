#include "ExprUtil.hpp"
#include <string>
#include <unordered_set>

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
class GlobalStringSet
{
public:
   static size_t count(const std::string& k)
   {
     return string_set.count(k);
   }

   static void insert(const std::string& k)
   {
     string_set.insert(k);
   }

   static size_t erase(const std::string& k)
   {
     return string_set.erase(k);
   }

   static void clear()
   {
     string_set.clear();
   }

private:
   inline static std::unordered_set<std::string> string_set;
};
inline ListAccum<std::string> string_split(std::string str, std::string delimiter) {
     ListAccum<std::string> newList;
     size_t pos = 0;
     std::string token;

     while ((pos = str.find(delimiter)) != std::string::npos) {
       token = str.substr(0, pos);
       newList += token;
       str.erase(0, pos + delimiter.length());
     }
     newList += str;
     return newList;
}
inline ListAccum<std::string> searchInMilvus(
   const std::string milvus_host, const int64_t milvus_port, const std::string& collection_name,
   const std::string& vector_field_name, const std::string& vertex_id_field_name, const std::string& query_vector_str,
   const std::string& metric_type, const int64_t top_k) {
   
   MilvusUtil milvus_util(milvus_host, milvus_port);
   
   // Convert query vector string to std::vector<float>
   std::vector<float> query_vector = stringToFloatVector(query_vector_str);

   std::cout << "Beginning the search on: " << collection_name << std::endl;
   return milvus_util.search(collection_name, vector_field_name, vertex_id_field_name, query_vector, metric_type, top_k);
}