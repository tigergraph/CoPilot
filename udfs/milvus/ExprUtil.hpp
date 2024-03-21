#include <iostream>
#include <vector>
#include <utility>
#include <string>
#include "milvus/include/MilvusClient.h"
#include "milvus/include/types/ConnectParam.h"
#include "milvus/include/types/SearchResults.h"
#include "milvus/include/types/FieldData.h"

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
        auto status = client->Search(args, results);
        CheckStatus("Search failed:", status);

        for (const auto& result : results.Results()) {
            auto ids = result.Ids().StrIDArray();

            // Iterate over the results and extract vector_id and vertex_id
            for (size_t i = 0; i < ids.size(); ++i) {
                std::string vector_id = ids[i];
                std::string vertex_id = "";
                results_list.emplace_back(vector_id, vertex_id);
            }
        }

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