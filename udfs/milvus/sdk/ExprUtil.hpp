#include <iostream>
#include <vector>
#include <utility>
#include <string>
#include "milvus/include/MilvusClient.h"
#include "milvus/include/types/ConnectParam.h"
#include "milvus/include/types/SearchResults.h"

class MilvusUtil {
public:
    MilvusUtil(const std::string& host, const int64_t port) {
        auto client = milvus::MilvusClient::Create();
        milvus::ConnectParam connect_param{host, static_cast<uint16_t>(port)};
        auto status = client->Connect(connect_param);
        CheckStatus("Failed to connect to Milvus server:", status);
        this->client = std::move(client);
    }

    ~MilvusUtil() {
        if (client) {
            client->Disconnect();
        }
    }

    std::vector<std::pair<std::string, std::string>> search(const std::string& collection_name, const std::string& vector_field_name,
                        const std::string& vertex_id_field_name, const std::vector<float>& query_vector, const std::string& metric_type, const int64_t top_k) const {
        std::vector<std::pair<std::string, std::string>> results_list;

        milvus::SearchArguments args;
        args.SetCollectionName(collection_name);
        args.SetTopK(top_k);
        args.AddTargetVector(vector_field_name, query_vector);
        args.SetMetricType(StringToMetricType(metric_type));
        args.AddOutputField(vertex_id_field_name);

        milvus::SearchResults results;

        std::cout << "Loading collection before search " << std::endl;
        auto status = client->LoadCollection(collection_name);

        std::cout << "Searching!" << std::endl;
        status = client->Search(args, results);
        CheckStatus("Search failed:", status);

        for (const auto& result : results.Results()) {
            auto ids = result.Ids().IntIDArray();
            auto vertex_id_field = result.OutputField(vertex_id_field_name);
            auto& distances = result.Scores();

            auto vertex_id_field_ptr = std::dynamic_pointer_cast<milvus::VarCharFieldData>(vertex_id_field);
            auto& vertex_id_data = vertex_id_field_ptr->Data();

            std::cout << "Iterate over the results and extract vector_id and vertex_id" << std::endl;

            for (size_t i = 0; i < ids.size(); ++i) {
                std::string vector_id_str = std::to_string(ids[i]);
                std::string vertex_id_str = vertex_id_data[i]; 
                std::cout << "Vector ID: " << vector_id_str << "\tDistance: " << distances[i]
                        << "\tVertex ID: " << vertex_id_str << std::endl;
                
                results_list.emplace_back(vector_id_str, vertex_id_str);
            }
        }

        std::cout << "Returning results list " << std::endl;
        return results_list;
    }

private:
    std::shared_ptr<milvus::MilvusClient> client;

    static void CheckStatus(const std::string& prefix, const milvus::Status& status) {
        if (!status.IsOk()) {
            std::cerr << prefix << " Error: " << status.Message() << std::endl;
            exit(EXIT_FAILURE);
        }
    }

    static ::milvus::MetricType StringToMetricType(const std::string& metric_type_str) {
        if (metric_type_str == "L2") {
            return ::milvus::MetricType::L2;
        } else if (metric_type_str == "IP") {
            return ::milvus::MetricType::IP;
        }
        return ::milvus::MetricType::INVALID;
    }
};