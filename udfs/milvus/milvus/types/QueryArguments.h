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

#include <cstdint>
#include <set>
#include <string>

#include "../Status.h"

namespace milvus {

/**
 * @brief Arguments for MilvusClient::Query().
 */
class QueryArguments {
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
     * @brief Specify partition name to control query scope, the name cannot be empty
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
     * @brief Set filter expression, the expression cannot be empty
     */
    Status
    SetExpression(std::string expression);

    /**
     * @brief Get travel timestamp.
     */
    uint64_t
    TravelTimestamp() const;
    /**
     * @brief  @brief Specify an absolute timestamp in a query to get results based on a data view at a specified point
     * in time. \n Default value is 0, server executes query on a full data view.
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
     * If no such timestamp is specified, the server will wait for the latest operation to finish and query. \n
     *
     * Note: The timestamp is not an absolute timestamp, it is a hybrid value combined by UTC time and internal flags.
     * \n We call it TSO, for more information please refer to: \n
     * https://github.com/milvus-io/milvus/blob/master/docs/design_docs/milvus_hybrid_ts_en.md.
     * You can get a TSO from insert/delete results. Use an operation's TSO to set this parameter, \n the server will
     * execute query after this operation is finished. \n
     *
     * Default value is 1, server executes search immediately.
     */
    Status
    SetGuaranteeTimestamp(uint64_t timestamp);

 private:
    std::string collection_name_;
    std::set<std::string> partition_names_;
    std::set<std::string> output_field_names_;
    std::string filter_expression_;

    std::set<std::string> output_fields_;

    uint64_t travel_timestamp_{0};
    uint64_t guarantee_timestamp_{0};
};

}  // namespace milvus
