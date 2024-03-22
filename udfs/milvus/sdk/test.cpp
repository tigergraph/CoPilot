#include <iostream>
#include "ExprFunctions.hpp" // Make sure this path is correct

void
CheckStatus(std::string&& prefix, const milvus::Status& status) {
    if (!status.IsOk()) {
        std::cout << prefix << " " << status.Message() << std::endl;
        exit(1);
    }
}

int main() {
    printf("Populating collection - this would normally happen outside of the UDF...\n");

    // setup
    auto client = milvus::MilvusClient::Create();

    milvus::ConnectParam connect_param{"localhost", 19530};
    auto status = client->Connect(connect_param);
    CheckStatus("Failed to connect milvus server:", status);
    std::cout << "Connect to milvus server." << std::endl;

    const std::string collection_name = "TEST";
    status = client->DropCollection(collection_name);

    const std::string field_id_name = "pk";
    const std::string field_vertex_id_name = "vertex_id";
    const std::string field_vector_name = "document_vector";
    const uint32_t dimension = 4;
    milvus::CollectionSchema collection_schema(collection_name);
    collection_schema.AddField({field_id_name, milvus::DataType::INT64, "vector id", true, false});
    collection_schema.AddField(milvus::FieldSchema(field_vertex_id_name, milvus::DataType::VARCHAR, "TigerGraph vertex ID")
                                   .WithMaxLength(64));
    collection_schema.AddField(milvus::FieldSchema(field_vector_name, milvus::DataType::FLOAT_VECTOR, "Document Vector")
                                   .WithDimension(dimension));

    status = client->CreateCollection(collection_schema);
    CheckStatus("Failed to create collection:", status);
    std::cout << "Successfully create collection." << std::endl;

    milvus::IndexDesc index_desc(field_vector_name, "", milvus::IndexType::FLAT, milvus::MetricType::L2, 0);
    status = client->CreateIndex(collection_name, index_desc);
    CheckStatus("Failed to create index:", status);
    std::cout << "Successfully create index." << std::endl;

    // create a partition
    std::string partition_name = "TG_PartitionOne";
    status = client->CreatePartition(collection_name, partition_name);
    CheckStatus("Failed to create partition:", status);
    std::cout << "Successfully create partition." << std::endl;

    // tell server prepare to load collection
    status = client->LoadCollection(collection_name);
    CheckStatus("Failed to load collection:", status);

    // insert some rows
    const int64_t row_count = 1000;
    std::vector<int64_t> insert_ids;
    std::vector<std::string> insert_vertex_ids;
    std::vector<std::vector<float>> insert_vectors;
    std::default_random_engine ran(time(nullptr));
    std::uniform_int_distribution<int> int_gen(1, 100);
    std::uniform_real_distribution<float> float_gen(0.0, 1.0);
    for (auto i = 0; i < row_count; ++i) {
        insert_ids.push_back(i);
        insert_vertex_ids.push_back(std::to_string(int_gen(ran)));
        std::vector<float> vector(dimension);

        for (auto i = 0; i < dimension; ++i) {
            vector[i] = float_gen(ran);
        }
        insert_vectors.emplace_back(vector);
    }

    std::vector<milvus::FieldDataPtr> fields_data{
        std::make_shared<milvus::Int64FieldData>(field_id_name, insert_ids),
        std::make_shared<milvus::VarCharFieldData>(field_vertex_id_name, insert_vertex_ids),
        std::make_shared<milvus::FloatVecFieldData>(field_vector_name, insert_vectors)};
    milvus::DmlResults dml_results;
    status = client->Insert(collection_name, partition_name, fields_data, dml_results);
    CheckStatus("Failed to insert:", status);
    std::cout << "Successfully insert " << dml_results.IdArray().IntIDArray().size() << " rows." << std::endl;

    // copilot code
    std::cout << "Running copilot code." << std::endl;
    std::string milvus_host = "localhost";
    int64_t milvus_port = 19530;
    std::string collection_name_one = collection_name;
    std::string vector_field_name = field_vector_name;
    std::string vertex_id_field_name = field_vertex_id_name;
    std::string metric_type = "L2";

    std::uniform_int_distribution<int64_t> int64_gen(0, row_count - 1);
    int64_t q_number = int64_gen(ran);
    std::vector<float> q_vector = insert_vectors[q_number];
    int64_t top_k = 10;
    std::cout << "Searching in milvus." << std::endl;
    auto search_results = searchInMilvus(milvus_host, milvus_port, collection_name_one, vector_field_name, vertex_id_field_name, q_vector, metric_type, top_k);    // Output search results
    for (const auto& result : search_results) {
        std::cout << "Vector ID: " << result.first << ", Vertex ID: " << result.second << std::endl;
    }
}