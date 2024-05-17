#include <iostream>
#include <vector>
#include <utility>
#include <string>
#include <random>
#include <curl/curl.h>
#include <json/json.h>

class tg_MilvusUtil {
public:
    tg_MilvusUtil(const std::string& host, int port) {
        this->host = host;
        this->port = port;
        curl_global_init(CURL_GLOBAL_ALL);
    }

    ~tg_MilvusUtil() {
        curl_global_cleanup();
    }

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

    ListAccum<std::string> search(const std::string& collection_name, const std::string& vector_field_name,
                        const std::string& vertex_id_field_name, const std::vector<float>& query_vector, const std::string& metric_type, int top_k) const {
        ListAccum<std::string> vertexIdList;

        Json::Value search_body;
        search_body["collectionName"] = collection_name;
        
        // Convert query_vector to Json::Value format
        for (const auto& val : query_vector) {
            search_body["vector"].append(val);
        }

        search_body["outputFields"] = Json::arrayValue;
        search_body["outputFields"].append("pk");
        search_body["outputFields"].append(vertex_id_field_name);
        search_body["limit"] = top_k;

        // You may need to adjust 'search_body' to match the exact format expected by your Milvus server version

        CURL* curl = curl_easy_init();
        if (curl) {
            CURLcode res;
            std::string readBuffer;            
            std::string url;
            
            if (host.substr(0, 4) == "http" && host.find(":") != std::string::npos && host.find(std::to_string(port)) != std::string::npos) {
                url = host + "/v1/vector/search";
            } else if (host.substr(0, 4) == "http") {
                url = host + ":" + std::to_string(port) + "/v1/vector/search";
            } else {
                url = "http://" + host + ":" + std::to_string(port) + "/v1/vector/search";
            }

            Json::StreamWriterBuilder writerBuilder;
            std::string requestBody = Json::writeString(writerBuilder, search_body);

            curl_easy_setopt(curl, CURLOPT_URL, url.c_str());
            curl_easy_setopt(curl, CURLOPT_POST, 1L);
            curl_easy_setopt(curl, CURLOPT_POSTFIELDS, requestBody.c_str());
            curl_easy_setopt(curl, CURLOPT_WRITEFUNCTION, WriteCallback);
            curl_easy_setopt(curl, CURLOPT_WRITEDATA, &readBuffer);

            struct curl_slist *headers = NULL;
            headers = curl_slist_append(headers, "Content-Type: application/json");
            curl_easy_setopt(curl, CURLOPT_HTTPHEADER, headers);

            res = curl_easy_perform(curl);
            if (res != CURLE_OK) {
                std::cerr << "curl_easy_perform() failed: " << curl_easy_strerror(res) << std::endl;
            } else {
                Json::CharReaderBuilder readerBuilder;
                Json::Value json_response;
                std::unique_ptr<Json::CharReader> const reader(readerBuilder.newCharReader());
                std::string parseErrors;

                bool parsingSuccessful = reader->parse(readBuffer.c_str(), readBuffer.c_str() + readBuffer.size(), &json_response, &parseErrors);
                
                if (parsingSuccessful) {
                    std::cout << "JSON successfully parsed" << std::endl;
                } else {
                    // If parsing was unsuccessful, print the errors encountered
                    std::cerr << "Failed to parse JSON: " << parseErrors << std::endl;
                }

                if (parsingSuccessful) {
                    for (const auto& item : json_response["data"]) {
                        std::string pk = item["pk"].asString();
                        std::string vertex_id_str = item[vertex_id_field_name].asString();
                        std::cout << "Vector ID: " << pk << "\tVertex ID: " << vertex_id_str << std::endl;
                        vertexIdList += vertex_id_str;
                    }
                }
            }

            curl_easy_cleanup(curl);
            curl_slist_free_all(headers);
        }

        return vertexIdList;
    }

private:
    std::string host;
    int port;

    static size_t WriteCallback(void *contents, size_t size, size_t nmemb, std::string *userp) {
        userp->append((char*)contents, size * nmemb);
        return size * nmemb;
    }
};