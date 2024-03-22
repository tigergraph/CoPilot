// Licensed to the LF AI & Data foundation under one
// or more contributor license agreements. See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership. The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License. You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#pragma once

#include <set>
#include <string>
#include <unordered_map>

#include "../Status.h"
#include "Constants.h"
#include "FieldData.h"
#include "MetricType.h"

namespace milvus {

/**
 * @brief Arguments for MilvusClient::Search().
 */
class SearchArguments {
 public:
    /**
     * @brief Get name of the target collection
     */
    const std::string&
    CollectionName() const;

    /**
     * @brief Set name of this collection, cannot be empty
     */
    Status
    SetCollectionName(std::string collection_name);

    /**
     * @brief Get partition names
     */
    const std::set<std::string>&
    PartitionNames() const;

    /**
     * @brief Specify partition name to control search scope, the name cannot be empty
     */
    Status
    AddPartitionName(std::string partition_name);

    /**
     * @brief Get output field names
     */
    const std::set<std::string>&
    OutputFields() const;

    /**
     * @brief Specify output field names to return field data, the name cannot be empty
     */
    Status
    AddOutputField(std::string field_name);

    /**
     * @brief Get filter expression
     */
    const std::string&
    Expression() const;

    /**
     * @brief Set filter expression
     */
    Status
    SetExpression(std::string expression);

    /**
     * @brief Get target vectors
     */
    FieldDataPtr
    TargetVectors() const;

    /**
     * @brief Add a binary vector to search
     */
    Status
    AddTargetVector(std::string field_name, const std::string& vector);

    /**
     * @brief Add a binary vector to search with uint8_t vectors
     */
    Status
    AddTargetVector(std::string field_name, const std::vector<uint8_t>& vector);

    /**
     * @brief Add a binary vector to search
     */
    Status
    AddTargetVector(std::string field_name, std::string&& vector);

    /**
     * @brief Add a float vector to search
     */
    Status
    AddTargetVector(std::string field_name, const FloatVecFieldData::ElementT& vector);

    /**
     * @brief Add a float vector to search
     */
    Status
    AddTargetVector(std::string field_name, FloatVecFieldData::ElementT&& vector);

    /**
     * @brief Get travel timestamp.
     */
    uint64_t
    TravelTimestamp() const;

    /**
     * @brief Specify an absolute timestamp in a search to get results based on a data view at a specified point in
     * time. \n
     *
     * Default value is 0, server executes search on a full data view.
     */
    Status
    SetTravelTimestamp(uint64_t timestamp);

    /**
     * @brief Get guarantee timestamp.
     */
    uint64_t
    GuaranteeTimestamp() const;

    /**
     * @brief Instructs server to see insert/delete operations performed before a provided timestamp. \n
     * If no such timestamp is specified, the server will wait for the latest operation to finish and search. \n
     *
     * Note: The timestamp is not an absolute timestamp, it is a hybrid value combined by UTC time and internal flags.
     * \n We call it TSO, for more information please refer to: \n
     * https://github.com/milvus-io/milvus/blob/master/docs/design_docs/milvus_hybrid_ts_en.md.
     * You can get a TSO from insert/delete results. Use an operation's TSO to set this parameter,
     * the server will execute search after this operation is finished. \n
     *
     * Default value is 1, server executes search immediately.
     */
    Status
    SetGuaranteeTimestamp(uint64_t timestamp);

    /**
     * @brief Specify search limit, AKA topk
     */
    Status
    SetTopK(int64_t topk);

    /**
     * @brief Get Top K
     */
    int64_t
    TopK() const;

    /**
     * @brief Get nprobe
     */
    int64_t
    Nprobe() const;

    /**
     * @brief Set nprobe
     */
    Status
    SetNprobe(int64_t nlist);

    /**
     * @brief Specifies the decimal place of the returned results.
     */
    Status
    SetRoundDecimal(int round_decimal);

    /**
     * @brief Get the decimal place of the returned results
     */
    int
    RoundDecimal() const;

    /**
     * @brief Specifies the metric type
     */
    Status
    SetMetricType(::milvus::MetricType metric_type);

    /**
     * @brief Get the metric type
     */
    ::milvus::MetricType
    MetricType() const;

    /**
     * @brief Add extra param
     */
    Status
    AddExtraParam(std::string key, int64_t value);

    /**
     * @brief Get extra param
     */
    std::string
    ExtraParams() const;

    /**
     * @brief Validate for search arguments
     *
     */
    Status
    Validate() const;

    /**
     * @brief Get range radius
     * @return
     */
    float
    Radius() const;

    /**
     * @brief Get range filter
     * @return
     */
    float
    RangeFilter() const;

    /**
     * @brief Set range radius
     * @param from range radius from
     * @param to range radius to
     */
    Status
    SetRange(float from, float to);

    /**
     * @brief Get if do range search
     * @return
     */
    bool
    RangeSearch() const;

 private:
    std::string collection_name_;
    std::set<std::string> partition_names_;
    std::set<std::string> output_field_names_;
    std::string filter_expression_;

    BinaryVecFieldDataPtr binary_vectors_;
    FloatVecFieldDataPtr float_vectors_;

    std::set<std::string> output_fields_;
    std::unordered_map<std::string, int64_t> extra_params_;

    uint64_t travel_timestamp_{0};
    uint64_t guarantee_timestamp_{GuaranteeEventuallyTs()};

    int64_t topk_{1};
    int round_decimal_{-1};

    float radius_;
    float range_filter_;
    bool range_search_{false};
    ::milvus::MetricType metric_type_{::milvus::MetricType::L2};
};

}  // namespace milvus
